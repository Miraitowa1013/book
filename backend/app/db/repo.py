import json
import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Optional


def _db_path() -> str:
    return os.getenv(
        "RESUME_DB_PATH",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "resume.db",
        ),
    )


@dataclass
class ResumeRecord:
    id: int
    filename: str
    extracted_text: Optional[str]
    sections_json: Optional[str]
    suggestions_json: Optional[str]
    created_at: str
    updated_at: str


class ResumeRepo:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or _db_path()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_record(self, filename: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO resume_records(filename) VALUES (?)",
                (filename,),
            )
            conn.commit()
            return int(cur.lastrowid)

    def set_ocr_result(self, resume_id: int, extracted_text: str, sections: Any) -> None:
        sections_json = json.dumps(sections, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE resume_records
                SET extracted_text = ?, sections_json = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (extracted_text, sections_json, resume_id),
            )
            conn.commit()

    def set_suggestions(self, resume_id: int, suggestions: Any) -> None:
        suggestions_json = json.dumps(suggestions, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE resume_records
                SET suggestions_json = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (suggestions_json, resume_id),
            )
            conn.commit()

    def get_record(self, resume_id: int) -> Optional[ResumeRecord]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, filename, extracted_text, sections_json, suggestions_json, created_at, updated_at
                FROM resume_records
                WHERE id = ?
                """,
                (resume_id,),
            ).fetchone()

        if row is None:
            return None

        return ResumeRecord(
            id=int(row["id"]),
            filename=str(row["filename"]),
            extracted_text=row["extracted_text"],
            sections_json=row["sections_json"],
            suggestions_json=row["suggestions_json"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def get_sections(self, resume_id: int) -> Optional[Any]:
        record = self.get_record(resume_id)
        if record is None or not record.sections_json:
            return None
        return json.loads(record.sections_json)

    def get_extracted_text(self, resume_id: int) -> Optional[str]:
        record = self.get_record(resume_id)
        return None if record is None else record.extracted_text

    def get_suggestions(self, resume_id: int) -> Optional[Any]:
        record = self.get_record(resume_id)
        if record is None or not record.suggestions_json:
            return None
        return json.loads(record.suggestions_json)

