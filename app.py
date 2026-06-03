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

