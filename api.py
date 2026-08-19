from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)
DB = "earthquake_intel.db"
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN", "brink-refresh-change-me")

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})

@app.route("/api/intel")
def intel():
    from build_intel import build
    return jsonify(build())

@app.route("/api/brief")
def brief():
    conn = get_conn()
    c = conn.cursor()
    seq = c.execute("""
        SELECT s.id, s.name, s.region, s.status, s.start_time,
               e.magnitude, e.place, e.latitude, e.longitude, e.depth_km, e.event_time
        FROM sequences s
        LEFT JOIN events e ON e.id = s.mainshock_event_id
        WHERE s.status = 'active'
        ORDER BY e.magnitude DESC
        LIMIT 1
    """).fetchone()
    if not seq:
        conn.close()
        return jsonify({"error": "No active sequence"}), 404
    seq_id = seq["id"]
    n_events = c.execute(
        "SELECT COUNT(*) AS n FROM sequence_events WHERE sequence_id = ?", (seq_id,)
    ).fetchone()["n"]
    f = c.execute("""
        SELECT * FROM sequence_forecasts
        WHERE sequence_id = ?
        ORDER BY calculated_at DESC LIMIT 1
    """, (seq_id,)).fetchone()
    recent = c.execute("""
        SELECT e.magnitude, e.place, e.event_time, e.depth_km
        FROM sequence_events se
        JOIN events e ON e.id = se.event_id
        WHERE se.sequence_id = ?
        ORDER BY e.event_time DESC
        LIMIT 8
    """, (seq_id,)).fetchall()
    conn.close()
    mag = seq["magnitude"] or 0
    return jsonify({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sequence": {
            "name": seq["name"],
            "mainshock_magnitude": seq["magnitude"],
            "mainshock_place": seq["place"],
            "mainshock_time": seq["event_time"],
            "depth_km": seq["depth_km"],
            "linked_events": n_events,
            "status": seq["status"],
        },
        "aftershock_outlook": dict(f) if f else None,
        "recent_events": [dict(r) for r in recent],
    })

@app.route("/api/sequences")
def sequences():
    conn = get_conn()
    rows = conn.execute("""
        SELECT s.id, s.name, s.status,
               e.magnitude as mainshock_mag, e.place as mainshock_place,
               (SELECT COUNT(*) FROM sequence_events se WHERE se.sequence_id = s.id) as event_count
        FROM sequences s
        LEFT JOIN events e ON e.id = s.mainshock_event_id
        WHERE s.status = 'active'
        ORDER BY e.magnitude DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/events/recent")
def recent_events():
    conn = get_conn()
    rows = conn.execute("""
        SELECT a.code as agency, e.magnitude, e.place, e.event_time, e.depth_km
        FROM events e
        JOIN agencies a ON a.id = e.agency_id
        ORDER BY e.event_time DESC
        LIMIT 30
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/refresh", methods=["GET", "POST"])
def refresh():
    token = request.args.get("token") or request.headers.get("X-Refresh-Token")
    expected = os.environ.get("REFRESH_TOKEN", "brink-refresh-change-me")
    if token != expected:
        return jsonify({"error": "unauthorized"}), 401
    try:
        from refresh_all import run_refresh
        full = run_refresh()
        # Slim response for cron-job.org size limits
        slim_steps = []
        for s in full.get("steps") or []:
            if not isinstance(s, dict):
                continue
            slim_steps.append({
                k: s.get(k)
                for k in ("source", "status", "inserted", "updated", "received", "skipped",
                          "error", "sequences_created", "forecasts_updated")
                if k in s
            })
        return jsonify({
            "status": full.get("status", "ok"),
            "started_at": full.get("started_at"),
            "finished_at": full.get("finished_at"),
            "steps": slim_steps,
            "error": full.get("error"),
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/alerts")
def alerts():
    from threshold_engine import run_thresholds
    return jsonify(run_thresholds())

if __name__ == "__main__":
    print("API running at http://127.0.0.1:5050")
    print("Routes: /health  /api/intel  /api/brief  /api/sequences  /api/events/recent")
    app.run(host="127.0.0.1", port=5050, debug=False)
