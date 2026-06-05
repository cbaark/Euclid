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

def row_owned_or_404(table, row_id):
    db = get_db()
    row = db.execute(
        'SELECT user_id FROM "%s" WHERE id = ?' % table, (row_id,)
    ).fetchone()
    if row is None:
        return False, (jsonify({"error": "Not found"}), 404)
    if row["user_id"] != current_user():
        return False, (jsonify({"error": "Not found"}), 404)
    return True, None


@app.route("/api/journal", methods=["GET"])
@login_required
def journal_list():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM journal_entries WHERE user_id = ? ORDER BY date DESC, id DESC",
        (current_user(),),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/journal", methods=["POST"])
@login_required
def journal_create():
    data = json_body()
    miss = missing_fields(data, ["title", "date", "content"])
    if miss:
        return jsonify({"error": "Missing fields: " + ", ".join(miss)}), 400

    entry_type = clean(data.get("entry_type", ""))
    related = clean(data.get("related_module", ""))
    if entry_type and entry_type not in ENTRY_TYPES:
        return jsonify({"error": "Invalid entry type"}), 400
    if related and related not in MODULES:
        return jsonify({"error": "Invalid related module"}), 400

    db = get_db()
    cur = db.execute(
        """INSERT INTO journal_entries
           (user_id, title, date, project_tag, entry_type, related_module, content)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            current_user(),
            clean(data["title"]),
            clean(data["date"]),
            clean(data.get("project_tag", "")),
            entry_type,
            related,
            data["content"],
        ),
    )
    db.commit()
    return jsonify({"id": cur.lastrowid}), 201


@app.route("/api/journal/<int:entry_id>", methods=["PATCH"])
@login_required
def journal_update(entry_id):
    ok, err = row_owned_or_404("journal_entries", entry_id)
    if not ok:
        return err
    data = json_body()
    miss = missing_fields(data, ["title", "date", "content"])
    if miss:
        return jsonify({"error": "Missing fields: " + ", ".join(miss)}), 400

    entry_type = clean(data.get("entry_type", ""))
    related = clean(data.get("related_module", ""))
    if entry_type and entry_type not in ENTRY_TYPES:
        return jsonify({"error": "Invalid entry type"}), 400
    if related and related not in MODULES:
        return jsonify({"error": "Invalid related module"}), 400

    db = get_db()
    db.execute(
        """UPDATE journal_entries
           SET title = ?, date = ?, project_tag = ?, entry_type = ?,
               related_module = ?, content = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ? AND user_id = ?""",
        (
            clean(data["title"]),
            clean(data["date"]),
            clean(data.get("project_tag", "")),
            entry_type,
            related,
            data["content"],
            entry_id,
            current_user(),
        ),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/journal/<int:entry_id>", methods=["DELETE"])
@login_required
def journal_delete(entry_id):
    ok, err = row_owned_or_404("journal_entries", entry_id)
    if not ok:
        return err
    db = get_db()
    db.execute(
        "DELETE FROM journal_entries WHERE id = ? AND user_id = ?",
        (entry_id, current_user()),
    )
    db.commit()
    return jsonify({"ok": True})

@app.route("/api/kanban", methods=["GET"])
@login_required
def kanban_list():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM kanban_issues WHERE user_id = ? ORDER BY id DESC",
        (current_user(),),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/kanban", methods=["POST"])
@login_required
def kanban_create():
    data = json_body()
    miss = missing_fields(data, ["title", "status"])
    if miss:
        return jsonify({"error": "Missing fields: " + ", ".join(miss)}), 400

    status = clean(data["status"])
    priority = clean(data.get("priority", ""))
    if status not in KANBAN_STATUS:
        return jsonify({"error": "Invalid status"}), 400
    if priority and priority not in KANBAN_PRIORITY:
        return jsonify({"error": "Invalid priority"}), 400

    reported = clean(data.get("reported_date", "")) or today_str()
    db = get_db()
    cur = db.execute(
        """INSERT INTO kanban_issues
           (user_id, title, description, status, priority, reported_date)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            current_user(),
            clean(data["title"]),
            data.get("description", ""),
            status,
            priority,
            reported,
        ),
    )
    db.commit()
    return jsonify({"id": cur.lastrowid}), 201


@app.route("/api/kanban/<int:issue_id>", methods=["PATCH"])
@login_required
def kanban_update(issue_id):
    ok, err = row_owned_or_404("kanban_issues", issue_id)
    if not ok:
        return err
    data = json_body()
    db = get_db()

    # drag and drop vs full update conditional
    if set(data.keys()) <= {"status"}:
        status = clean(data.get("status", ""))
        if status not in KANBAN_STATUS:
            return jsonify({"error": "Invalid status"}), 400
        db.execute(
            "UPDATE kanban_issues SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
            (status, issue_id, current_user()),
        )
        db.commit()
        return jsonify({"ok": True})

    miss = missing_fields(data, ["title", "status"])
    if miss:
        return jsonify({"error": "Missing fields: " + ", ".join(miss)}), 400
    status = clean(data["status"])
    priority = clean(data.get("priority", ""))
    if status not in KANBAN_STATUS:
        return jsonify({"error": "Invalid status"}), 400
    if priority and priority not in KANBAN_PRIORITY:
        return jsonify({"error": "Invalid priority"}), 400
    reported = clean(data.get("reported_date", "")) or today_str()
    db.execute(
        """UPDATE kanban_issues
           SET title = ?, description = ?, status = ?, priority = ?,
               reported_date = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ? AND user_id = ?""",
        (
            clean(data["title"]),
            data.get("description", ""),
            status,
            priority,
            reported,
            issue_id,
            current_user(),
        ),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/kanban/<int:issue_id>", methods=["DELETE"])
@login_required
def kanban_delete(issue_id):
    ok, err = row_owned_or_404("kanban_issues", issue_id)
    if not ok:
        return err
    db = get_db()
    db.execute(
        "DELETE FROM kanban_issues WHERE id = ? AND user_id = ?",
        (issue_id, current_user()),
    )
    db.commit()
    return jsonify({"ok": True})

def next_req_id(db, uid, req_type):
    prefix = "FR" if req_type.startswith("Functional") else "NFR"
    rows = db.execute(
        "SELECT req_id FROM requirements WHERE user_id = ? AND req_id LIKE ?",
        (uid, prefix + "-%"),
    ).fetchall()
    biggest = 0
    for r in rows:
        # exact match or else null
        tail = r["req_id"].split("-", 1)
        head = tail[0]
        if head != prefix:
            continue
        try:
            num = int(tail[1])
        except (IndexError, ValueError):
            continue
        biggest = max(biggest, num)
    return "%s-%03d" % (prefix, biggest + 1)


@app.route("/api/requirements", methods=["GET"])
@login_required
def requirements_list():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM requirements WHERE user_id = ? ORDER BY req_id",
        (current_user(),),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/requirements", methods=["POST"])
@login_required
def requirements_create():
    data = json_body()
    miss = missing_fields(data, ["type", "description"])
    if miss:
        return jsonify({"error": "Missing fields: " + ", ".join(miss)}), 400

    req_type = clean(data["type"])
    priority = clean(data.get("priority", ""))
    status = clean(data.get("status", "")) or "Not Started"
    module = clean(data.get("assigned_module", ""))
    if req_type not in REQ_TYPES:
        return jsonify({"error": "Invalid type"}), 400
    if priority and priority not in REQ_PRIORITY:
        return jsonify({"error": "Invalid priority"}), 400
    if status not in REQ_STATUS:
        return jsonify({"error": "Invalid status"}), 400
    if module and module not in MODULES:
        return jsonify({"error": "Invalid module"}), 400

    db = get_db()
    req_id = next_req_id(db, current_user(), req_type)
    cur = db.execute(
        """INSERT INTO requirements
           (user_id, req_id, type, description, priority, status,
            assigned_module, acceptance_criteria, source_stakeholder)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            current_user(),
            req_id,
            req_type,
            data["description"],
            priority,
            status,
            module,
            data.get("acceptance_criteria", ""),
            clean(data.get("source_stakeholder", "")),
        ),
    )
    db.commit()
    return jsonify({"id": cur.lastrowid, "req_id": req_id}), 201


@app.route("/api/requirements/<int:req_id>", methods=["PATCH"])
@login_required
def requirements_update(req_id):
    ok, err = row_owned_or_404("requirements", req_id)
    if not ok:
        return err
    data = json_body()
    miss = missing_fields(data, ["type", "description"])
    if miss:
        return jsonify({"error": "Missing fields: " + ", ".join(miss)}), 400

    req_type = clean(data["type"])
    priority = clean(data.get("priority", ""))
    status = clean(data.get("status", "")) or "Not Started"
    module = clean(data.get("assigned_module", ""))
    if req_type not in REQ_TYPES:
        return jsonify({"error": "Invalid type"}), 400
    if priority and priority not in REQ_PRIORITY:
        return jsonify({"error": "Invalid priority"}), 400
    if status not in REQ_STATUS:
        return jsonify({"error": "Invalid status"}), 400
    if module and module not in MODULES:
        return jsonify({"error": "Invalid module"}), 400

    db = get_db()
    db.execute(
        """UPDATE requirements
           SET type = ?, description = ?, priority = ?, status = ?,
               assigned_module = ?, acceptance_criteria = ?, source_stakeholder = ?,
               updated_at = CURRENT_TIMESTAMP
           WHERE id = ? AND user_id = ?""",
        (
            req_type,
            data["description"],
            priority,
            status,
            module,
            data.get("acceptance_criteria", ""),
            clean(data.get("source_stakeholder", "")),
            req_id,
            current_user(),
        ),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/requirements/<int:req_id>", methods=["DELETE"])
@login_required
def requirements_delete(req_id):
    ok, err = row_owned_or_404("requirements", req_id)
    if not ok:
        return err
    db = get_db()
    db.execute(
        "DELETE FROM requirements WHERE id = ? AND user_id = ?",
        (req_id, current_user()),
    )
    db.commit()
    return jsonify({"ok": True})

@app.route("/api/references", methods=["GET"])
@login_required
def references_list():
    db = get_db()
    rows = db.execute(
        'SELECT * FROM "references" WHERE user_id = ? ORDER BY id DESC',
        (current_user(),),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/references", methods=["POST"])
@login_required
def references_create():
    data = json_body()
    miss = missing_fields(data, ["title"])
    if miss:
        return jsonify({"error": "Missing fields: " + ", ".join(miss)}), 400

    url = clean(data.get("url", ""))
    ref_type = clean(data.get("ref_type", ""))
    module = clean(data.get("related_module", ""))
    if url and not valid_url(url):
        return jsonify({"error": "URL must start with http:// or https://"}), 400
    if ref_type and ref_type not in REF_TYPES:
        return jsonify({"error": "Invalid reference type"}), 400
    if module and module not in MODULES:
        return jsonify({"error": "Invalid related module"}), 400

    db = get_db()
    if url:
        dupe = db.execute(
            'SELECT 1 FROM "references" WHERE user_id = ? AND url = ?',
            (current_user(), url),
        ).fetchone()
        if dupe:
            return jsonify({"error": "You already saved that URL"}), 409

    cur = db.execute(
        """INSERT INTO "references"
           (user_id, title, url, ref_type, tags, notes, date_added, related_module)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            current_user(),
            clean(data["title"]),
            url,
            ref_type,
            clean(data.get("tags", "")),
            data.get("notes", ""),
            clean(data.get("date_added", "")) or today_str(),
            module,
        ),
    )
    db.commit()
    return jsonify({"id": cur.lastrowid}), 201


@app.route("/api/references/<int:ref_id>", methods=["PATCH"])
@login_required
def references_update(ref_id):
    ok, err = row_owned_or_404("references", ref_id)
    if not ok:
        return err
    data = json_body()
    miss = missing_fields(data, ["title"])
    if miss:
        return jsonify({"error": "Missing fields: " + ", ".join(miss)}), 400

    url = clean(data.get("url", ""))
    ref_type = clean(data.get("ref_type", ""))
    module = clean(data.get("related_module", ""))
    if url and not valid_url(url):
        return jsonify({"error": "URL must start with http:// or https://"}), 400
    if ref_type and ref_type not in REF_TYPES:
        return jsonify({"error": "Invalid reference type"}), 400
    if module and module not in MODULES:
        return jsonify({"error": "Invalid related module"}), 400

    db = get_db()
    if url:
        dupe = db.execute(
            'SELECT 1 FROM "references" WHERE user_id = ? AND url = ? AND id != ?',
            (current_user(), url, ref_id),
        ).fetchone()
        if dupe:
            return jsonify({"error": "You already saved that URL"}), 409

    db.execute(
        """UPDATE "references"
           SET title = ?, url = ?, ref_type = ?, tags = ?, notes = ?,
               date_added = ?, related_module = ?
           WHERE id = ? AND user_id = ?""",
        (
            clean(data["title"]),
            url,
            ref_type,
            clean(data.get("tags", "")),
            data.get("notes", ""),
            clean(data.get("date_added", "")) or today_str(),
            module,
            ref_id,
            current_user(),
        ),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/references/<int:ref_id>", methods=["DELETE"])
@login_required
def references_delete(ref_id):
    ok, err = row_owned_or_404("references", ref_id)
    if not ok:
        return err
    db = get_db()
    db.execute(
        'DELETE FROM "references" WHERE id = ? AND user_id = ?',
        (ref_id, current_user()),
    )
    db.commit()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=False, port=5000)
