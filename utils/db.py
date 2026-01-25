import sqlite3
import random

_connection = None


def get_db_connection(db_path="./datas/allen_data.db"):
    """Establish a connection to the SQLite database, reusing if already exists."""
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(db_path)
    return _connection


def get_event_by_rel(rel: str):
    """Fetch events from the database based on a given relation."""
    corresponding_rels = {
        "p": "precedes",
        "P": "precededby",
        "m": "meets",
        "M": "metby",
        "o": "overlaps",
        "O": "overlappedby",
        "s": "starts",
        "S": "startedby",
        "f": "finishes",
        "F": "finishedby",
        "d": "during",
        "D": "contains",
        "e": "equals",
    }
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM relations WHERE allen_type=?", (corresponding_rels[rel],)
    )
    results = cursor.fetchall()
    from_id, to_id, allen_type = random.choice(results)
    return {
        "from": from_id,
        "to": to_id,
    }


if __name__ == "__main__":
    get_event_by_rel("S")
