""" this can be run more than once if need be """
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "euclid.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def init_db():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()
    print("euclid.db ready at", DB_PATH)


if __name__ == "__main__":
    init_db()
