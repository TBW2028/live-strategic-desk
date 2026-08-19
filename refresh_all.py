import sqlite3
import json
import math
import urllib.request
import ssl
from datetime import datetime, timezone, timedelta
from math import radians, sin, cos, sqrt, atan2

DB = "earthquake_intel.db"

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def get_agency_id(conn, code):
    cur = conn.cursor()
    cur.execute("SELECT id FROM agencies WHERE code = ?", (code,))
    row = cur.fetchone()
    return row[0] if row else None

def fetch_json(url, headers=None):
    req = urllib.request.Request(
        url,
        headers=headers or {
            "User-Agent": "Mozilla/5.0 (compatible; BrinkWorld-EQ-Intel/1.0)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60, context=ssl_ctx()) as resp:
        return json.loads(resp.read().decode())

def ingest_usgs(conn):
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson"
    data = fetch_json(url)
    features = data.get("features", [])
    agency_id = get_agency_id(conn, "usgs")
    if not agency_id:
        return {"source": "usgs", "error": "agency missing"}
    inserted = skipped = 0
    for f in features:
        props = f.get("properties", {})
        coords = f.get("geometry", {}).get("coordinates", [None, None, None])
        external_id = props.get("code") or f.get("id")
        magnitude = props.get("mag")
        place = props.get("place")
        event_time_ms = props.get("time")
        depth = coords[2] if len(coords) > 2 else None
        lon = coords[0] if len(coords) > 0 else None
        lat = coords[1] if len(coords) > 1 else None
        source_url = props.get("url")
        event_time = (
            datetime.fromtimestamp(event_time_ms / 1000, tz=timezone.utc).isoformat()
            if event_time_ms else None
        )
        raw_data = json.dumps(f)
        try:
            conn.execute(
                """
                INSERT INTO events (
                    agency_id, external_id, magnitude, place,
                    latitude, longitude, depth_km, event_time,
                    raw_data, source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (agency_id, external_id, magnitude, place, lat, lon, depth, event_time, raw_data, source_url),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
    return {"source": "usgs", "received": len(features), "inserted": inserted, "skipped": skipped}

def parse_bmkg_time(tanggal, jam):
    try:
        months = {
            "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
            "Mei": "05", "Jun": "06", "Jul": "07", "Agu": "08",
            "Sep": "09", "Okt": "10", "Nov": "11", "Des": "12",
        }
        parts = tanggal.replace(",", "").split()
        if len(parts) >= 3:
            day = parts[0].zfill(2)
            mon = months.get(parts[1], "01")
            year = parts[2]
            time_part = jam.replace(" WIB", "").strip()
            return f"{year}-{mon}-{day}T{time_part}+07:00"
    except Exception:
        pass
    return f"{tanggal} {jam}"

def ingest_bmkg(conn):
    url = "https://data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json"
    data = fetch_json(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    gempa_list = data.get("Infogempa", {}).get("gempa", [])
    if isinstance(gempa_list, dict):
        gempa_list = [gempa_list]
    agency_id = get_agency_id(conn, "bmkg")
    if not agency_id:
        return {"source": "bmkg", "error": "agency missing"}
    inserted = skipped = 0
    for g in gempa_list:
        try:
            magnitude = float(g.get("Magnitude", 0))
        except (TypeError, ValueError):
            magnitude = None
        place = g.get("Wilayah", "")
        depth_str = str(g.get("Kedalaman", "0")).replace(" km", "").strip()
        try:
            depth = float(depth_str)
        except (TypeError, ValueError):
            depth = None
        lat = lon = None
        coords = g.get("Coordinates", "")
        if coords and "," in coords:
            try:
                lat_s, lon_s = coords.split(",")
                lat = float(lat_s.strip())
                lon = float(lon_s.strip())
            except ValueError:
                pass
        if lat is None:
            lintang = g.get("Lintang", "")
            bujur = g.get("Bujur", "")
            try:
                if "LS" in lintang:
                    lat = -float(lintang.replace("LS", "").strip())
                elif "LU" in lintang:
                    lat = float(lintang.replace("LU", "").strip())
                if "BT" in bujur:
                    lon = float(bujur.replace("BT", "").strip())
                elif "BB" in bujur:
                    lon = -float(bujur.replace("BB", "").strip())
            except ValueError:
                pass
        event_time = parse_bmkg_time(g.get("Tanggal", ""), g.get("Jam", ""))
        external_id = g.get("DateTime") or f"{g.get('Tanggal')}_{g.get('Jam')}_{magnitude}"
        raw_data = json.dumps(g, ensure_ascii=False)
        try:
            conn.execute(
                """
                INSERT INTO events (
                    agency_id, external_id, magnitude, place,
                    latitude, longitude, depth_km, event_time,
                    raw_data, source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (agency_id, external_id, magnitude, place, lat, lon, depth, event_time, raw_data, "https://www.bmkg.go.id"),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
    return {"source": "bmkg", "received": len(gempa_list), "inserted": inserted, "skipped": skipped}

def haversine_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return 9999
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

def parse_time(t):
    if not t:
        return None
    t = str(t).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(t)
    except Exception:
        try:
            return datetime.strptime(str(t)[:19], "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return None

def detect_sequences(conn):
    c = conn.cursor()
    c.execute("""
        SELECT id, magnitude, place, latitude, longitude, event_time
        FROM events WHERE magnitude >= 6.5
        ORDER BY event_time DESC
    """)
    mainshocks = c.fetchall()
    c.execute("""
        SELECT id, magnitude, place, latitude, longitude, event_time
        FROM events ORDER BY event_time
    """)
    all_events = c.fetchall()
    created = 0
    for ms in mainshocks:
        ms_id, ms_mag, ms_place, ms_lat, ms_lon, ms_time = ms
        ms_dt = parse_time(ms_time)
        if not ms_dt:
            continue
        c.execute("SELECT id FROM sequences WHERE mainshock_event_id = ?", (ms_id,))
        existing = c.fetchone()
        if existing:
            seq_id = existing[0]
        else:
            c.execute(
                """
                INSERT INTO sequences (name, mainshock_event_id, start_time, status, region, notes)
                VALUES (?, ?, ?, 'active', ?, ?)
                """,
                (f"M{ms_mag} {ms_place}", ms_id, ms_time, ms_place or "Unknown", "Auto-detected"),
            )
            seq_id = c.lastrowid
            created += 1
            try:
                c.execute("INSERT INTO sequence_events (sequence_id, event_id) VALUES (?, ?)", (seq_id, ms_id))
            except sqlite3.IntegrityError:
                pass
        window_end = ms_dt + timedelta(days=14)
        for ev in all_events:
            ev_id, ev_mag, ev_place, ev_lat, ev_lon, ev_time = ev
            if ev_id == ms_id:
                continue
            ev_dt = parse_time(ev_time)
            if not ev_dt or ev_dt < ms_dt or ev_dt > window_end:
                continue
            if haversine_km(ms_lat, ms_lon, ev_lat, ev_lon) <= 250:
                try:
                    c.execute("INSERT INTO sequence_events (sequence_id, event_id) VALUES (?, ?)", (seq_id, ev_id))
                except sqlite3.IntegrityError:
                    pass
    return {"sequences_created": created, "mainshocks_seen": len(mainshocks)}

def days_since(mainshock_time, now=None):
    ms = parse_time(mainshock_time)
    if not ms:
        return None
    if now is None:
        now = datetime.now(timezone.utc)
    if ms.tzinfo is None:
        ms = ms.replace(tzinfo=timezone.utc)
    return max((now - ms).total_seconds() / 86400.0, 0.01)

def rj_style_probability(mainshock_mag, days_elapsed, mag_threshold, window_days):
    if mainshock_mag is None:
        return (0, 0)
    dm = mainshock_mag - mag_threshold
    productivity = 10 ** (0.85 * dm - 1.8)
    decay = (days_elapsed + 0.05) ** (-1.1)
    expected = productivity * decay * window_days
    p = 1.0 - math.exp(-max(expected, 0))
    p = max(0.0, min(p, 0.97))
    low = max(0, int(round((p * 0.75) * 100)))
    high = min(97, int(round((p * 1.15) * 100)))
    if high < low:
        high = low
    return (low, high)

def run_forecasts(conn):
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sequence_forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sequence_id INTEGER,
            calculated_at TEXT,
            days_since_mainshock REAL,
            p_m5_24h_low INTEGER,
            p_m5_24h_high INTEGER,
            p_m5_3d_low INTEGER,
            p_m5_3d_high INTEGER,
            p_m55_7d_low INTEGER,
            p_m55_7d_high INTEGER,
            p_m6_14d_low INTEGER,
            p_m6_14d_high INTEGER,
            notes TEXT,
            FOREIGN KEY (sequence_id) REFERENCES sequences(id)
        )
    """)
    c.execute("""
        SELECT s.id, s.name, s.start_time, e.magnitude
        FROM sequences s
        LEFT JOIN events e ON e.id = s.mainshock_event_id
        WHERE s.status = 'active'
    """)
    sequences = c.fetchall()
    now_iso = datetime.now(timezone.utc).isoformat()
    updated = 0
    for seq_id, name, start_time, ms_mag in sequences:
        days = days_since(start_time)
        if days is None:
            continue
        p5_24 = rj_style_probability(ms_mag, days, 5.0, 1)
        p5_3d = rj_style_probability(ms_mag, days, 5.0, 3)
        p55_7 = rj_style_probability(ms_mag, days, 5.5, 7)
        p6_14 = rj_style_probability(ms_mag, days, 6.0, 14)
        notes = f"Generic RJ/Omori-style bands for M{ms_mag}. Days since: {days:.2f}."
        c.execute(
            """
            INSERT INTO sequence_forecasts (
                sequence_id, calculated_at, days_since_mainshock,
                p_m5_24h_low, p_m5_24h_high,
                p_m5_3d_low, p_m5_3d_high,
                p_m55_7d_low, p_m55_7d_high,
                p_m6_14d_low, p_m6_14d_high,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                seq_id, now_iso, days,
                p5_24[0], p5_24[1], p5_3d[0], p5_3d[1],
                p55_7[0], p55_7[1], p6_14[0], p6_14[1], notes,
            ),
        )
        updated += 1
    return {"forecasts_updated": updated}

def run_refresh():
    conn = sqlite3.connect(DB)
    results = {"started_at": datetime.now(timezone.utc).isoformat(), "steps": []}
    try:
        usgs = ingest_usgs(conn)
        conn.commit()
        results["steps"].append(usgs)
        bmkg = ingest_bmkg(conn)
        conn.commit()
        results["steps"].append(bmkg)
        seq = detect_sequences(conn)
        conn.commit()
        results["steps"].append(seq)
        fc = run_forecasts(conn)
        conn.commit()
        results["steps"].append(fc)
        try:
            from ingest_multi import run_multi_ingest
            multi = run_multi_ingest(DB)
            results["steps"].append(multi)
        except Exception as e:
            results["steps"].append({"source": "multi_hazard", "error": str(e)})
        
        # Prune GDACS noise + old notices each cycle
        try:
            from datetime import timedelta
            conn2 = sqlite3.connect(DB)
            conn2.execute("""
                DELETE FROM hazard_events
                WHERE hazard_type = 'multi'
                  AND (
                    lower(title) LIKE '%forest fire%'
                    OR lower(title) LIKE '%wildfire%'
                    OR level = 'Green'
                  )
            """)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
            conn2.execute("DELETE FROM hazard_events WHERE event_time < ?", (cutoff,))
            conn2.commit()
            conn2.close()
            results["steps"].append({"source": "prune", "status": "ok"})
        except Exception as e:
            results["steps"].append({"source": "prune", "error": str(e)})

        results["status"] = "ok"
    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        conn.rollback()
    finally:
        conn.close()
    results["finished_at"] = datetime.now(timezone.utc).isoformat()
    return results

if __name__ == "__main__":
    print(json.dumps(run_refresh(), indent=2))
