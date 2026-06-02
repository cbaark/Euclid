PRAGMA foreign_keys = ON;

-- accounts. username + password only, nothing else
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- developer journal entries
CREATE TABLE IF NOT EXISTS journal_entries (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    title          TEXT NOT NULL,
    date           DATE NOT NULL,
    project_tag    TEXT,
    entry_type     TEXT,
    related_module TEXT,
    content        TEXT,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- bug kanban issues
CREATE TABLE IF NOT EXISTS kanban_issues (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT,
    status        TEXT NOT NULL,
    priority      TEXT,
    reported_date DATE,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- reference list. quoted name on purpose
CREATE TABLE IF NOT EXISTS "references" (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    title          TEXT NOT NULL,
    url            TEXT,
    ref_type       TEXT,
    tags           TEXT,
    notes          TEXT,
    date_added     DATE,
    related_module TEXT,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- requirements tracker
CREATE TABLE IF NOT EXISTS requirements (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id            INTEGER NOT NULL,
    req_id             TEXT NOT NULL,
    type               TEXT NOT NULL,
    description        TEXT,
    priority           TEXT,
    status             TEXT,
    assigned_module    TEXT,
    acceptance_criteria TEXT,
    source_stakeholder TEXT,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
