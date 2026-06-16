import os
import sqlite3

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "euclid.db")

USERNAME = "developer"
PASSWORD = "Developer123"


JOURNAL = [
    # title, date, project_tag, entry_type, related_module, content
    ("First day of coding", "2026-05-18", "setup", "Daily Log", "General",
     "Got the project skeleton up and running today. Set up the Flask app, the static folders and the SQLite database. Nothing fancy yet, just making sure the server boots and serves a page."),
    ("Database schema decisions", "2026-05-19", "database", "Decision Record", "General",
     "Decided to keep one users table and a separate table per module. Each module table points back to the user with a foreign key so every row is owned by someone. Went with parameterised queries everywhere to stay safe."),
    ("Auth flow working", "2026-05-21", "auth", "Daily Log", "Authentication",
     "Login and registration are done. Passwords are hashed and salted with Werkzeug before they ever touch the database. Sessions keep the user signed in. Tested that a logged out user gets bounced to the login page."),
    ("Kanban drag and drop", "2026-05-24", "frontend", "Problem Note", "Bug Tracker",
     "Spent a while on the drag and drop. The trick was to call preventDefault on dragover so the drop event actually fires. Dropping a card now patches the status on the server and rolls back if the request fails."),
    ("Sprint 1 retrospective", "2026-05-27", "retrospective", "Retrospective", "General",
     "Good week. The four modules are all talking to the same backend now. Next up is polishing the offline support and writing a proper test plan. One thing to watch is keeping the comments casual and readable."),
]

# title, description, status, priority, reported_date
KANBAN = [
    ("Syntax error on line 123", "Missing colon at the end of a function definition was crashing the whole module on import.",
     "Completed", "Critical", "2026-05-18"),
    ("Login redirect loops on slow network", "When the network is slow the dashboard sometimes redirects back to login before the session cookie is read.",
     "Urgent", "High", "2026-05-26"),
    ("Date field accepts empty value", "The journal date field can be submitted blank on older browsers. Needs a stronger client side check.",
     "To-Do", "Medium", "2026-05-25"),
    ("Long titles overflow the bug card", "A very long bug title pushes the priority badge off the edge of the card.",
     "To-Do", "Low", "2026-05-27"),
    ("Reference URL validation too strict", "URLs without a trailing slash were being rejected. Loosened the check so normal links pass.",
     "Completed", "Medium", "2026-05-20"),
]

# type, description, priority, status, assigned_module, acceptance_criteria, source_stakeholder
REQUIREMENTS = [
    ("Functional (FR)", "Make the program return a greeting to the user at some stage during the initialisation of the program.",
     "High", "Complete", "General", "On first load the user sees a clear welcome on the dashboard.", "Client"),
    ("Functional (FR)", "Users must be able to register with a username and password and log in again later.",
     "High", "Complete", "Authentication", "A new account can be created and used to sign back in.", "Client"),
    ("Functional (FR)", "The bug tracker must let a user move an issue between urgent, to-do and completed.",
     "Medium", "In Progress", "Bug Tracker", "Dragging a card to a new column saves the new status.", "Developer"),
    ("Functional (FR)", "Requirements must be auto numbered so the user does not have to track ids by hand.",
     "Medium", "Complete", "Requirements", "Each new requirement gets the next FR or NFR number.", "Developer"),
    ("Non-Functional (NFR)", "The application must work offline and sync changes once the connection is back.",
     "High", "In Progress", "General", "A change made offline shows up on the server after reconnecting.", "Client"),
    ("Non-Functional (NFR)", "All user input must be validated on both the client and the server before it is stored.",
     "High", "Complete", "General", "Bad input is rejected with a clear message and never hits the database.", "Teacher"),
    ("Non-Functional (NFR)", "Passwords must never be stored in plain text.",
     "High", "Complete", "Authentication", "The database only ever holds a salted hash of the password.", "Teacher"),
]

# title, url, ref_type, tags, notes, date_added, related_module
REFERENCES = [
    ("Flask Documentation", "https://flask.palletsprojects.com/", "Documentation", "flask, backend",
     "Main reference for routing, sessions and send_from_directory.", "2026-05-18", "General"),
    ("Werkzeug Security Helpers", "https://werkzeug.palletsprojects.com/en/stable/utils/", "Documentation", "auth, hashing",
     "Used for generate_password_hash and check_password_hash.", "2026-05-19", "Authentication"),
    ("MDN Drag and Drop API", "https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API", "Tutorial", "frontend, kanban",
     "Walks through the native drag and drop events for the bug board.", "2026-05-24", "Bug Tracker"),
    ("MDN Using Service Workers", "https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers", "Article", "pwa, offline",
     "Reference for caching the app shell and handling fetch events.", "2026-05-25", "General"),
    ("SQLite Query Language", "https://www.sqlite.org/lang.html", "Documentation", "database, sql",
     "Checked the syntax for UNION ALL when building the activity feed.", "2026-05-26", "General"),
    ("OWASP Top Ten", "https://owasp.org/www-project-top-ten/", "Article", "security",
     "Used to sanity check the app against common web vulnerabilities.", "2026-05-27", "Authentication"),
]


def seed():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # start clean so reruns are predictable. cascade clears the child rows
    cur.execute("DELETE FROM users WHERE username = ?", (USERNAME,))

    cur.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (USERNAME, generate_password_hash(PASSWORD)),
    )
    uid = cur.lastrowid

    cur.executemany(
        """INSERT INTO journal_entries
           (user_id, title, date, project_tag, entry_type, related_module, content)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [(uid,) + row for row in JOURNAL],
    )

    cur.executemany(
        """INSERT INTO kanban_issues
           (user_id, title, description, status, priority, reported_date)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [(uid,) + row for row in KANBAN],
    )

    # build req ids in order, counting FR and NFR separately
    fr = 0
    nfr = 0
    for (rtype, desc, prio, status, module, accept, source) in REQUIREMENTS:
        if rtype.startswith("Functional"):
            fr += 1
            rid = "FR-%03d" % fr
        else:
            nfr += 1
            rid = "NFR-%03d" % nfr
        cur.execute(
            """INSERT INTO requirements
               (user_id, req_id, type, description, priority, status,
                assigned_module, acceptance_criteria, source_stakeholder)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (uid, rid, rtype, desc, prio, status, module, accept, source),
        )

    cur.executemany(
        """INSERT INTO "references"
           (user_id, title, url, ref_type, tags, notes, date_added, related_module)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [(uid,) + row for row in REFERENCES],
    )

    conn.commit()
    conn.close()
    print("seeded account '%s' (password '%s')" % (USERNAME, PASSWORD))
    print("journal:", len(JOURNAL), "bugs:", len(KANBAN),
          "requirements:", len(REQUIREMENTS), "references:", len(REFERENCES))


if __name__ == "__main__":
    seed()
