import os
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/health")
def health():
    from datetime import datetime, timezone
    return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})

@app.route("/api/intel")
def intel():
    try:
        from build_intel import build
        return jsonify(build())
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/api/alerts")
def alerts():
    try:
        from threshold_engine import run_thresholds
        return jsonify(run_thresholds())
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/api/refresh", methods=["GET", "POST"])
def refresh():
    token = request.args.get("token") or request.headers.get("X-Refresh-Token")
    expected = os.environ.get("REFRESH_TOKEN", "brink-refresh-change-me")
    if token != expected:
        return jsonify({"error": "unauthorized"}), 401
    try:
        from refresh_all import run_refresh
        full = run_refresh()
        slim_steps = []
        for s in full.get("steps") or []:
            if not isinstance(s, dict):
                continue
            slim_steps.append({
                k: s.get(k)
                for k in (
                    "source", "status", "inserted", "updated", "received", "skipped",
                    "error", "sequences_created", "forecasts_updated"
                )
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

@app.route("/api/events/recent")
def events_recent():
    import sqlite3
    db = os.environ.get("INTEL_DB", "earthquake_intel.db")
    if not os.path.exists(db):
        return jsonify({"events": []})
    conn = sqlite3.connect(db)
    rows = conn.execute(
        """
        SELECT magnitude, place, depth_km, event_time, latitude, longitude
        FROM events
        ORDER BY event_time DESC
        LIMIT 30
        """
    ).fetchall()
    conn.close()
    events = [
        {
            "magnitude": r[0],
            "place": r[1],
            "depth_km": r[2],
            "event_time": r[3],
            "latitude": r[4],
            "longitude": r[5],
        }
        for r in rows
    ]
    return jsonify({"events": events})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
