from flask import Flask, request, redirect, render_template, g, url_for, jsonify, Response
import sqlite3
import os
import secrets
from functools import wraps

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "db", "queue.db")
_db_initialized = False

# --- Admin auth (optional via ADMIN_PASSWORD) ---
def _admin_protected():
    expected = os.getenv("ADMIN_PASSWORD")
    if not expected:
        return True
    auth = request.authorization
    return auth and auth.username == "admin" and auth.password == expected

def require_admin(f):
    @wraps(f)
    def _wrap(*a, **k):
        if not _admin_protected():
            return Response("Auth required", 401, {"WWW-Authenticate": 'Basic realm="Admin"'})
        return f(*a, **k)
    return _wrap

# --- DB / schema ---
def init_db():
    os.makedirs(os.path.join(BASE_DIR, "db"), exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        group_size INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'waiting',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS state (
        key TEXT PRIMARY KEY,
        value INTEGER NOT NULL
    );
    """)
    # add token column if missing
    cols = [c[1] for c in conn.execute("PRAGMA table_info(queue)").fetchall()]
    if "token" not in cols:
        conn.execute("ALTER TABLE queue ADD COLUMN token TEXT")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_queue_token ON queue(token)")
    # seed occupancy row
    conn.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('occupancy', 0)")
    # backfill tokens
    cur = conn.execute("SELECT id FROM queue WHERE token IS NULL OR token=''")
    for (gid,) in cur.fetchall():
        tok = secrets.token_urlsafe(8)
        while conn.execute("SELECT 1 FROM queue WHERE token=?", (tok,)).fetchone():
            tok = secrets.token_urlsafe(8)
        conn.execute("UPDATE queue SET token=? WHERE id=?", (tok, gid))
    conn.commit()
    conn.close()

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

# --- Occupancy helpers ---
def get_occupancy():
    db = get_db()
    row = db.execute("SELECT value FROM state WHERE key='occupancy'").fetchone()
    return int(row["value"]) if row else 0

def set_occupancy(value: int):
    db = get_db()
    db.execute("""
        INSERT INTO state(key, value) VALUES('occupancy', ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (int(value),))
    db.commit()

def change_occupancy(delta: int):
    set_occupancy(max(0, get_occupancy() + int(delta)))

# --- App lifecycle ---
@app.before_request
def ensure_db():
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

# --- Routes ---
@app.route("/")
def index():
    return redirect(url_for("join"))

@app.route("/join", methods=["GET", "POST"])
def join():
    if request.method == "POST":
        name = (request.form.get("name") or "Guest").strip()
        size = max(1, int(request.form["group_size"]))
        db = get_db()
        token = secrets.token_urlsafe(8)
        while db.execute("SELECT 1 FROM queue WHERE token=?", (token,)).fetchone():
            token = secrets.token_urlsafe(8)
        db.execute(
            "INSERT INTO queue (name, group_size, status, token) VALUES (?, ?, 'waiting', ?)",
            (name, size, token)
        )
        db.commit()
        return redirect(url_for("status_token", token=token))
    return render_template("join.html")

# Status page (tokenized link)
@app.route("/t/<token>")
def status_token(token):
    return render_template("status.html", token=token)

# Live status data for polling
@app.route("/t/<token>/data")
def status_token_data(token):
    db = get_db()
    me = db.execute("SELECT id, name, group_size, status, created_at FROM queue WHERE token=?", (token,)).fetchone()
    if not me:
        return jsonify({"ok": False, "not_found": True})
    if me["status"] != "waiting":
        return jsonify({"ok": True, "status": me["status"], "occupancy": get_occupancy(), "group_size": me["group_size"], "position": 0, "ahead": 0, "eta_minutes": 0})
    ahead = db.execute(
        "SELECT COUNT(*) AS c FROM queue WHERE status='waiting' AND created_at < ?",
        (me["created_at"],)
    ).fetchone()["c"]
    seconds_per_group = 60
    eta_minutes = (ahead * seconds_per_group) // 60
    return jsonify({
        "ok": True,
        "status": "waiting",
        "group_size": me["group_size"],
        "position": ahead + 1,
        "ahead": ahead,
        "eta_minutes": eta_minutes,
        "occupancy": get_occupancy()
    })

# ...existing code...

@app.route("/admin")
@require_admin
def admin():
    db = get_db()
    waiting = db.execute("SELECT id, name, group_size, created_at FROM queue WHERE status='waiting' ORDER BY created_at").fetchall()
    active = db.execute("SELECT id, name, group_size, created_at FROM queue WHERE status='active' ORDER BY created_at").fetchall()
    total_waiting_people = db.execute("SELECT COALESCE(SUM(group_size),0) AS total FROM queue WHERE status='waiting'").fetchone()["total"]
    return render_template("admin.html", waiting=waiting, active=active, occupancy=get_occupancy(), total_waiting_people=total_waiting_people)

@app.route("/admin/data")
@require_admin
def admin_data():
    db = get_db()
    waiting_rows = db.execute("SELECT id, name, group_size, created_at FROM queue WHERE status='waiting' ORDER BY created_at").fetchall()
    active_rows  = db.execute("SELECT id, name, group_size, created_at FROM queue WHERE status='active'  ORDER BY created_at").fetchall()
    total_waiting_people = db.execute("SELECT COALESCE(SUM(group_size),0) AS total FROM queue WHERE status='waiting'").fetchone()["total"]
    return jsonify({
        "occupancy": get_occupancy(),
        "waiting": [dict(r) for r in waiting_rows],
        "active":  [dict(r) for r in active_rows],
        "total_waiting_groups": len(waiting_rows),
        "total_waiting_people": total_waiting_people
    })

# Call a waiting group up (sets them 'active')
@app.route("/admin/call/<int:group_id>", methods=["POST"])
@require_admin
def call_group(group_id):
    db = get_db()
    # single active at a time (comment out next line to allow multiple)
    db.execute("UPDATE queue SET status='waiting' WHERE status='active'")
    db.execute("UPDATE queue SET status='active' WHERE id=? AND status='waiting'", (group_id,))
    db.commit()
    return ("", 204)

# Let a group in (from waiting or active) -> increments occupancy and marks done
@app.route("/admin/letin/<int:group_id>", methods=["POST"])
@require_admin
def let_in_group(group_id):
    db = get_db()
    row = db.execute("SELECT group_size FROM queue WHERE id=? AND status IN ('waiting','active')", (group_id,)).fetchone()
    if row:
        change_occupancy(row["group_size"])
        db.execute("UPDATE queue SET status='done' WHERE id=?", (group_id,))
        db.commit()
    return ("", 204)


@app.route("/admin/next/<int:group_id>", methods=["POST"])
@require_admin
def next_group(group_id):
    db = get_db()
    row = db.execute("SELECT group_size FROM queue WHERE id=? AND status='waiting'", (group_id,)).fetchone()
    if row:
        change_occupancy(row["group_size"])
        db.execute("UPDATE queue SET status='done' WHERE id=?", (group_id,))
        db.commit()
    return ("", 204)

@app.route("/admin/remove/<int:group_id>", methods=["POST"])
@require_admin
def remove_group(group_id):
    db = get_db()
    db.execute("UPDATE queue SET status='cancelled' WHERE id=? AND status='waiting'", (group_id,))
    db.commit()
    return ("", 204)

@app.route("/admin/occupancy", methods=["POST"])
@require_admin
def admin_occupancy():
    op = request.form.get("op") or request.form.get("action")
    if op == "inc":
        change_occupancy(int(request.form.get("delta", 1)))
    elif op == "dec":
        change_occupancy(-int(request.form.get("delta", 1)))
    elif op == "set":
        set_occupancy(int(request.form.get("value", 0)))
    return ("", 204)

@app.route("/admin/reset", methods=["POST"])
@require_admin
def reset_queue():
    db = get_db()
    db.execute("UPDATE queue SET status='cancelled' WHERE status='waiting'")
    db.commit()
    return ("", 204)

if __name__ == "__main__":
    app.run(debug=True)
