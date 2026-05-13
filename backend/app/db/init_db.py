import os
import sqlite3
from typing import Optional


def _db_path() -> str:
    # 尽量给课程演示一个“即开即用”的默认路径
    return os.getenv(
        "RESUME_DB_PATH",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "resume.db",
        ),
    )


def init_db(db_path: Optional[str] = None) -> None:
    path = db_path or _db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS resume_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                extracted_text TEXT,
                sections_json TEXT,
                suggestions_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_resume_records_created_at
            ON resume_records(created_at)
            """
        )
        conn.commit()
    finally:
        conn.close()

