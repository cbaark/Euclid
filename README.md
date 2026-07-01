# Euclid

An all-in-one, offline-capable Progressive Web App for solo and student developers to manage their software projects. A developer journal, bug kanban, requirements tracker, and reference list, all in one place.

## Prerequisites

- Python 3.12+
- A browser with service worker and IndexedDB support (Chrome 49+, Firefox 44+, Edge 79+, or Safari 16.4+) for offline functionality

## Setup

```bash
git clone <repo-url>
cd euclid
pip install -r requirements.txt
python init_db.py
```

`init_db.py` builds `euclid.db` from `schema.sql`. It's safe to run more than once, it won't wipe existing data.

### Optional: seed demo data

```bash
python seed_data.py
```

This creates a demo account with journal entries, kanban issues, requirements, and references already populated, so you can see the system in a used state rather than an empty one.

```
Username: developer
Password: Developer123
```

Safe to re-run, it wipes and rebuilds the `developer` account each time, so the demo data is always consistent.

## Running

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

## Project structure

```
euclid/
├── app.py                 # Flask app: page routes, API routes, auth, CSRF
├── schema.sql              # SQLite schema (5 tables)
├── init_db.py               # Builds euclid.db from schema.sql
├── seed_data.py             # Optional demo account + sample data
├── requirements.txt
├── manifest.json            # PWA manifest
├── service_worker.js        # Offline caching + install
└── static/
    ├── html/                 # dashboard.html, journal.html, kanban.html, etc.
    ├── css/                  # base.css + one stylesheet per page
    └── js/                   # offline.js, utils.js, and one module per page
```

## Tech stack

- **Backend:** Python 3.12, Flask 3.1.2, Werkzeug 3.1.5
- **Database:** SQLite3 (no external server required)
- **Frontend:** Vanilla HTML5, CSS3, JS, no frameworks, no build step
- **Offline:** Service worker (cache-first shell) + IndexedDB write queue, flushed on reconnect

## Notes

- The service worker requires either `localhost` or HTTPS to register, it will not activate over plain HTTP on a non-localhost address.
- No external APIs are used. Everything runs against the local SQLite database.
