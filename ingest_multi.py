import json
import re
import sqlite3
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

DB = "earthquake_intel.db"

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def fetch(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; BrinkWorld-GlobalWatch/1.0)",
            "Accept": "application/json, application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=45, context=ssl_ctx()) as resp:
        return resp.read()

def ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hazard_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hazard_type TEXT NOT NULL,
            external_id TEXT,
            title TEXT,
            place TEXT,
            level TEXT,
            summary TEXT,
            event_time TEXT,
            source TEXT,
            source_url TEXT,
            raw_data TEXT,
            retrieved_at TEXT,
            UNIQUE(hazard_type, external_id)
        )
    """)

def upsert(conn, hazard_type, external_id, title, place, level, summary, event_time, source, source_url, raw):
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute("""
            INSERT INTO hazard_events (
                hazard_type, external_id, title, place, level, summary,
                event_time, source, source_url, raw_data, retrieved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (hazard_type, external_id, title, place, level, summary, event_time, source, source_url, raw, now))
        return "inserted"
    except sqlite3.IntegrityError:
        conn.execute("""
            UPDATE hazard_events SET
                title=?, place=?, level=?, summary=?, event_time=?,
                source_url=?, raw_data=?, retrieved_at=?
            WHERE hazard_type=? AND external_id=?
        """, (title, place, level, summary, event_time, source_url, raw, now, hazard_type, external_id))
        return "updated"

def ingest_cyclones(conn):
    url = "https://www.nhc.noaa.gov/CurrentStorms.json"
    stats = {"source": "nhc", "inserted": 0, "updated": 0, "received": 0}
    try:
        data = json.loads(fetch(url).decode("utf-8", errors="replace"))
    except Exception as e:
        return {"source": "nhc", "error": str(e)}
    storms = data.get("activeStorms") or data.get("storms") or []
    if isinstance(storms, dict):
        storms = list(storms.values())
    stats["received"] = len(storms)
    for s in storms:
        if not isinstance(s, dict):
            continue
        name = s.get("name") or s.get("id") or "Storm"
        basin = s.get("basin") or s.get("basinID") or ""
        classification = s.get("classification") or s.get("typeClass") or ""
        intensity = s.get("intensity") or s.get("maxWind") or ""
        external_id = str(s.get("id") or s.get("binNumber") or name)
        summary = f"Classification: {classification}. Intensity: {intensity}."
        event_time = str(s.get("lastUpdate") or datetime.now(timezone.utc).isoformat())
        result = upsert(conn, "cyclone", external_id, str(name), basin or "Ocean basin",
                        str(classification or "Active"), summary, event_time, "NHC",
                        "https://www.nhc.noaa.gov/", json.dumps(s)[:5000])
        stats[result] = stats.get(result, 0) + 1
    return stats

def parse_rss_items(xml_bytes):
    root = ET.fromstring(xml_bytes)
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        guid = (item.findtext("guid") or link or title).strip()
        pub = (item.findtext("pubDate") or "").strip()
        event_time = None
        if pub:
            try:
                event_time = parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat()
            except Exception:
                event_time = pub
        items.append({
            "title": title, "link": link,
            "description": re.sub(r"<[^>]+>", " ", desc)[:500],
            "guid": guid,
            "event_time": event_time or datetime.now(timezone.utc).isoformat(),
        })
    return items

def ingest_gdacs(conn):
    url = "https://www.gdacs.org/xml/rss.xml"
    stats = {"source": "gdacs", "inserted": 0, "updated": 0, "received": 0}
    try:
        items = parse_rss_items(fetch(url))
    except Exception as e:
        return {"source": "gdacs", "error": str(e)}
    stats["received"] = len(items)
    for it in items:
        title = it["title"]
        low = title.lower()
        # Filter: drop forest fires; drop Green notices (noise)
        if "forest fire" in low or "wildfire" in low or "eventtype=wf" in (it.get("link") or "").lower():
            continue
        if low.startswith("green ") or " green " in low[:40]:
            continue
        if "earthquake" in low:
            htype = "earthquake_notice"
        elif "flood" in low:
            htype = "flood"
        elif any(x in low for x in ("cyclone", "hurricane", "typhoon", "tropical")):
            htype = "cyclone"
        elif "volcano" in low:
            htype = "volcano"
        elif "drought" in low:
            htype = "drought"
        else:
            htype = "multi"
        level = "Notice"
        for lab in ("Red", "Orange", "Green"):
            if lab.lower() in low:
                level = lab
                break
        result = upsert(conn, htype, it["guid"][:200], title[:300], None, level,
                        it["description"], it["event_time"], "GDACS",
                        it["link"] or "https://www.gdacs.org/", json.dumps(it)[:4000])
        stats[result] = stats.get(result, 0) + 1
    return stats

def ingest_who_don(conn):
    url = "https://www.who.int/rss-feeds/news-english.xml"
    stats = {"source": "who_don", "inserted": 0, "updated": 0, "received": 0}
    try:
        items = parse_rss_items(fetch(url))
    except Exception as e:
        return {"source": "who_don", "error": str(e)}
    stats["received"] = len(items)
    keys = ("outbreak", "disease", "ebola", "cholera", "marburg", "mpox", "fever",
            "virus", "epidemic", "pandemic", "health emergency", "bundibugyo")
    for it in items:
        title = it["title"]
        low = title.lower()
        if not any(k in low for k in keys):
            continue
        place = None
        if " – " in title:
            place = title.split(" – ")[-1].strip()[:120]
        elif " - " in title:
            place = title.split(" - ")[-1].strip()[:120]
        result = upsert(conn, "health", it["guid"][:200], title[:300], place, "Official notice",
                        it["description"], it["event_time"], "WHO",
                        it["link"] or "https://www.who.int/", json.dumps(it)[:4000])
        stats[result] = stats.get(result, 0) + 1
    return stats

def ingest_usgs_volcano(conn):
    url = "https://volcanoes.usgs.gov/hans-public/api/volcano/getElevatedVolcanoes"
    stats = {"source": "usgs_volcano", "inserted": 0, "updated": 0, "received": 0}
    try:
        data = json.loads(fetch(url).decode("utf-8", errors="replace"))
    except Exception as e:
        return {"source": "usgs_volcano", "error": str(e)}
    volcanoes = data if isinstance(data, list) else []
    stats["received"] = len(volcanoes)
    for v in volcanoes:
        if not isinstance(v, dict):
            continue
        name = v.get("volcano_name") or v.get("volcanoName") or "Volcano"
        alert = v.get("alert_level") or v.get("alertLevel") or ""
        color = v.get("color_code") or v.get("colorCode") or ""
        level = f"{alert} {color}".strip() or "Elevated"
        obs = v.get("obs_fullname") or v.get("obs_abbr") or "USGS"
        place = f"{name} · {obs}"
        external_id = str(v.get("vnum") or v.get("notice_identifier") or name)
        notice_url = v.get("notice_url") or "https://volcanoes.usgs.gov/"
        summary = f"{name}: {alert}/{color}. Observatory: {obs}. Type: {v.get('notice_type_cd', '')}."
        event_time = str(v.get("sent_utc") or datetime.now(timezone.utc).isoformat())
        result = upsert(conn, "volcano", external_id[:200], str(name)[:300], str(place)[:200],
                        level[:80], summary[:500], event_time, "USGS Volcano",
                        notice_url, json.dumps(v)[:5000])
        stats[result] = stats.get(result, 0) + 1
    return stats

def run_multi_ingest(db_path=None):
    db = db_path or DB
    conn = sqlite3.connect(db)
    ensure_table(conn)
    results = {"started_at": datetime.now(timezone.utc).isoformat(), "steps": []}
    try:
        for fn in (ingest_cyclones, ingest_gdacs, ingest_who_don, ingest_usgs_volcano):
            step = fn(conn)
            conn.commit()
            results["steps"].append(step)
        results["status"] = "ok"
    except Exception as e:
        conn.rollback()
        results["status"] = "error"
        results["error"] = str(e)
    finally:
        conn.close()
    results["finished_at"] = datetime.now(timezone.utc).isoformat()
    return results

if __name__ == "__main__":
    print(json.dumps(run_multi_ingest(), indent=2))
