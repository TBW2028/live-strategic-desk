import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta

DB = os.environ.get("INTEL_DB", "earthquake_intel.db")
THRESHOLDS_PATH = os.environ.get("THRESHOLDS_PATH", "thresholds.json")

def load_thresholds():
    if not os.path.exists(THRESHOLDS_PATH):
        return {"version": 1, "earthquake": {"watch_mag": 5.5, "alert_mag": 6.0, "escalate_mag": 7.0}}
    with open(THRESHOLDS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_time(t):
    if not t:
        return None
    t = str(t).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(t)
    except Exception:
        try:
            return datetime.strptime(str(t)[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception:
            return None

def classify_quake(mag, cfg):
    if mag is None:
        return None
    if mag >= cfg.get("escalate_mag", 7.0):
        return "escalate"
    if mag >= cfg.get("alert_mag", 6.0):
        return "alert"
    if mag >= cfg.get("watch_mag", 5.5):
        return "watch"
    return None

def evaluate_earthquakes(conn, cfg, hours=72):
    eq = cfg.get("earthquake", {})
    min_mag = eq.get("watch_mag", 5.5)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = conn.execute(
        "SELECT magnitude, place, depth_km, event_time FROM events WHERE magnitude >= ? ORDER BY event_time DESC LIMIT 200",
        (min_mag,),
    ).fetchall()
    hits = []
    for mag, place, depth, et in rows:
        dt = parse_time(et)
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt and dt < cutoff:
            continue
        level = classify_quake(mag, eq)
        if not level:
            continue
        hits.append({
            "hazard": "earthquake", "level": level,
            "title": f"M{mag} · {place}", "magnitude": mag, "place": place,
            "depth_km": depth, "event_time": et,
            "reason": f"M{mag} crossed {level} threshold", "source": "official_catalogue",
        })
    return hits

def evaluate_sequences(conn, cfg):
    eq = cfg.get("earthquake", {})
    hits = []
    try:
        rows = conn.execute("""
            SELECT s.name, e.magnitude, e.place, e.event_time,
                   (SELECT COUNT(*) FROM sequence_events se WHERE se.sequence_id = s.id)
            FROM sequences s
            LEFT JOIN events e ON e.id = s.mainshock_event_id
            WHERE s.status = 'active'
        """).fetchall()
    except sqlite3.OperationalError:
        return hits
    for name, mag, place, et, n in rows:
        if mag is None:
            continue
        level = "watch"
        if mag >= eq.get("escalate_mag", 7.0):
            level = "escalate"
        elif mag >= eq.get("alert_mag", 6.0):
            level = "alert"
        hits.append({
            "hazard": "earthquake_sequence", "level": level,
            "title": f"Active sequence · M{mag} {place or name}",
            "magnitude": mag, "place": place or name, "event_time": et,
            "linked_events": n, "reason": "Active sequence — aftershocks still relevant",
            "source": "sequence_model",
        })
    return hits

def classify_hazard_row(htype, level_text):
    lt = (level_text or "").lower()
    if htype == "volcano":
        if any(x in lt for x in ("warning", "red")):
            return "escalate"
        if any(x in lt for x in ("watch", "orange")):
            return "alert"
        if any(x in lt for x in ("advisory", "yellow")):
            return "watch"
        return "watch"
    if htype == "cyclone":
        if any(x in lt for x in ("hurricane", "typhoon", "major")):
            return "escalate"
        if any(x in lt for x in ("storm", "cyclone", "tropical")):
            return "alert"
        return "watch"
    if htype == "flood":
        if "red" in lt:
            return "escalate"
        if "orange" in lt or "warning" in lt:
            return "alert"
        return "watch"
    if htype == "health":
        if any(x in lt for x in ("emergency", "pandemic", "ebola", "marburg", "bundibugyo")):
            return "alert"
        return "watch"
    if "red" in lt:
        return "alert"
    if "orange" in lt:
        return "watch"
    return "watch"

def evaluate_hazard_events(conn, hours=168):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    try:
        rows = conn.execute("""
            SELECT hazard_type, title, place, level, summary, event_time, source, source_url
            FROM hazard_events ORDER BY event_time DESC LIMIT 150
        """).fetchall()
    except sqlite3.OperationalError:
        return []
    hits = []
    for htype, title, place, level, summary, et, source, source_url in rows:
        dt = parse_time(et)
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt and dt < cutoff:
            continue
        sev = classify_hazard_row(htype, f"{level} {title}")
        hits.append({
            "hazard": htype, "level": sev, "title": title, "place": place,
            "event_time": et, "notice_level": level,
            "summary": (summary or "")[:280],
            "reason": f"{htype} notice classified as {sev}",
            "source": source or "official", "source_url": source_url,
        })
    return hits

def run_thresholds(db_path=None):
    db = db_path or DB
    cfg = load_thresholds()
    result = {"evaluated_at": datetime.now(timezone.utc).isoformat(),
              "thresholds_version": cfg.get("version", 1), "alerts": []}
    if not os.path.exists(db):
        result["status"] = "no_database"
        return result
    conn = sqlite3.connect(db)
    try:
        all_hits = []
        all_hits.extend(evaluate_earthquakes(conn, cfg))
        all_hits.extend(evaluate_sequences(conn, cfg))
        all_hits.extend(evaluate_hazard_events(conn))
        rank = {"escalate": 0, "alert": 1, "watch": 2}
        def sort_key(h):
            dt = parse_time(h.get("event_time"))
            ts = dt.timestamp() if dt else 0
            return (rank.get(h["level"], 9), -ts)
        all_hits.sort(key=sort_key)
        result["alerts"] = all_hits
        by = {}
        for h in all_hits:
            by[h["hazard"]] = by.get(h["hazard"], 0) + 1
        result["counts"] = {
            "escalate": sum(1 for h in all_hits if h["level"] == "escalate"),
            "alert": sum(1 for h in all_hits if h["level"] == "alert"),
            "watch": sum(1 for h in all_hits if h["level"] == "watch"),
            "total": len(all_hits),
            "by_hazard": by,
        }
        result["status"] = "ok"
    finally:
        conn.close()
    return result

if __name__ == "__main__":
    print(json.dumps(run_thresholds(), indent=2, default=str))
