import os
import re
import secrets
import sqlite3
from datetime import date, timedelta
from functools import wraps
from urllib.parse import urlparse

from flask import (
    Flask,
    g,
    jsonify,
    redirect,
    request,
    send_from_directory,
    session,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "euclid.db")
HTML_DIR = os.path.join(BASE_DIR, "static", "html")

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = os.environ.get("EUCLID_SECRET", "dev-only-change-me-euclid")
app.permanent_session_lifetime = timedelta(days=14)

# ALLOWED VALUES.
ENTRY_TYPES = {"Daily Log", "Decision Record", "Retrospective", "Problem Note", "Research Note"}
MODULES = {"General", "Bug Tracker", "Requirements", "References", "Authentication"}
KANBAN_STATUS = {"Urgent", "To-Do", "Completed"}
KANBAN_PRIORITY = {"Critical", "High", "Medium", "Low"}
REQ_TYPES = {"Functional (FR)", "Non-Functional (NFR)"}
REQ_PRIORITY = {"High", "Medium", "Low"}
REQ_STATUS = {"Not Started", "In Progress", "Complete"}
REF_TYPES = {"Documentation", "Article", "Library", "Book", "Tutorial", "Video", "Other"}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def clean(value):
    return value.strip() if isinstance(value, str) else value


def missing_fields(data, fields):
    out = []
    for f in fields:
        v = data.get(f)
        if v is None or (isinstance(v, str) and v.strip() == ""):
            out.append(f)
    return out


def valid_password(pw):
    # min 8, at least one number, at least one uppercase
    if not isinstance(pw, str) or len(pw) < 8:
        return False
    return bool(re.search(r"\d", pw)) and bool(re.search(r"[A-Z]", pw))


def valid_url(url):
    try:
        parts = urlparse(url)
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and bool(parts.netloc)


def today_str():
    return date.today().isoformat()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            # api callers want json, page callers want a redirect
            if request.path.startswith("/api/"):
                return jsonify({"error": "Not authenticated"}), 401
            return redirect("/login")
        return fn(*args, **kwargs)

    return wrapper


def new_session(user_id, remember):
    session.clear()
    session["user_id"] = user_id
    session["csrf_token"] = secrets.token_hex(32)
    session.permanent = bool(remember)


@app.before_request
def csrf_protect():
    # only guard state changing api calls, login/register are exempt
    if request.path.startswith("/api/") and request.method in ("POST", "PATCH", "PUT", "DELETE"):
        sent = request.headers.get("X-CSRF-Token", "")
        if not sent or sent != session.get("csrf_token"):
            return jsonify({"error": "Bad or missing CSRF token"}), 403


def current_user():
    return session.get("user_id")


def json_body():
    return request.get_json(silent=True) or {}

def page(name):
    return send_from_directory(HTML_DIR, name)


@app.route("/")
def root():
    return redirect("/dashboard" if "user_id" in session else "/login")


@app.route("/login")
def login_page():
    return page("login.html")


@app.route("/register")
def register_page():
    return page("register.html")


@app.route("/dashboard")
@login_required
def dashboard_page():
    return page("dashboard.html")


@app.route("/journal")
@login_required
def journal_page():
    return page("journal.html")


@app.route("/kanban")
@login_required
def kanban_page():
    return page("kanban.html")


@app.route("/requirements")
@login_required
def requirements_page():
    return page("requirements.html")


@app.route("/references")
@login_required
def references_page():
    return page("references.html")

@app.route("/manifest.json")
def manifest():
    return send_from_directory(BASE_DIR, "manifest.json")


@app.route("/service_worker.js")
def service_worker():
    resp = send_from_directory(BASE_DIR, "service_worker.js")
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp

@app.route("/register", methods=["POST"])
def register():
    data = json_body()
    username = clean(data.get("username", ""))
    password = data.get("password", "")
    confirm = data.get("confirm_password", "")

    miss = missing_fields(data, ["username", "password", "confirm_password"])
    if miss:
        return jsonify({"error": "Missing fields: " + ", ".join(miss)}), 400
    if len(username) < 3 or len(username) > 40:
        return jsonify({"error": "Username must be 3 to 40 characters"}), 400
    if not valid_password(password):
        return jsonify({"error": "Password needs 8+ chars, a number and an uppercase letter"}), 400
    if password != confirm:
        return jsonify({"error": "Passwords do not match"}), 400

    db = get_db()
    exists = db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    if exists:
        return jsonify({"error": "That username is taken"}), 409

    cur = db.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, generate_password_hash(password)),
    )
    db.commit()
    new_session(cur.lastrowid, remember=False)
    return jsonify({"redirect": "/dashboard"})


@app.route("/login", methods=["POST"])
def login():
    data = json_body()
    username = clean(data.get("username", ""))
    password = data.get("password", "")
    remember = data.get("remember", False)

    miss = missing_fields(data, ["username", "password"])
    if miss:
        return jsonify({"error": "Missing fields: " + ", ".join(miss)}), 400

    db = get_db()
    user = db.execute(
        "SELECT id, password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid username or password"}), 401

    new_session(user["id"], remember)
    return jsonify({"redirect": "/dashboard"})


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/api/me")
@login_required
def whoami():
    db = get_db()
    row = db.execute("SELECT username FROM users WHERE id = ?", (current_user(),)).fetchone()
    return jsonify({"username": row["username"] if row else ""})


@app.route("/api/csrf")
@login_required
def get_csrf():
    # client grabs this once then sends it back on writes
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return jsonify({"csrf_token": session["csrf_token"]})

@app.route("/api/dashboard")
@login_required
def dashboard_stats():
    db = get_db()
    uid = current_user()

    journal_count = db.execute(
        "SELECT COUNT(*) c FROM journal_entries WHERE user_id = ?", (uid,)
    ).fetchone()["c"]
    urgent_bugs = db.execute(
        "SELECT COUNT(*) c FROM kanban_issues WHERE user_id = ? AND status = 'Urgent'", (uid,)
    ).fetchone()["c"]
    req_total = db.execute(
        "SELECT COUNT(*) c FROM requirements WHERE user_id = ?", (uid,)
    ).fetchone()["c"]
    req_done = db.execute(
        "SELECT COUNT(*) c FROM requirements WHERE user_id = ? AND status = 'Complete'", (uid,)
    ).fetchone()["c"]
    ref_count = db.execute(
        'SELECT COUNT(*) c FROM "references" WHERE user_id = ?', (uid,)
    ).fetchone()["c"]

    # recent activity part !!
    activity = db.execute(
        """
        SELECT kind, label, ts FROM (
            SELECT 'journal' AS kind, title AS label,
                   COALESCE(updated_at, created_at) AS ts
            FROM journal_entries WHERE user_id = :uid
            UNION ALL
            SELECT 'kanban', title, COALESCE(updated_at, created_at)
            FROM kanban_issues WHERE user_id = :uid
            UNION ALL
            SELECT 'reference', title, created_at
            FROM "references" WHERE user_id = :uid
            UNION ALL
            SELECT 'requirement', req_id || ' ' || COALESCE(description, ''),
                   COALESCE(updated_at, created_at)
            FROM requirements WHERE user_id = :uid
        )
        ORDER BY ts DESC
        LIMIT 5
        """,
        {"uid": uid},
    ).fetchall()

    return jsonify(
        {
            "journal_count": journal_count,
            "urgent_bugs": urgent_bugs,
            "requirements_done": req_done,
            "requirements_total": req_total,
            "reference_count": ref_count,
            "recent_activity": [dict(r) for r in activity],
        }
    )
