import json
import sqlite3
from pathlib import Path
from typing import Any

from app.models import TicketDraft


class Storage:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    user_id TEXT PRIMARY KEY,
                    draft_json TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    external_id TEXT NOT NULL UNIQUE,
                    requester_phone TEXT NOT NULL,
                    draft_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'nuevo',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get_draft(self, user_id: str) -> TicketDraft:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT draft_json FROM conversations WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if not row:
            return TicketDraft()
        return TicketDraft.model_validate_json(row["draft_json"])

    def save_draft(self, user_id: str, draft: TicketDraft) -> None:
        payload = draft.model_dump_json()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (user_id, draft_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    draft_json = excluded.draft_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, payload),
            )

    def clear_draft(self, user_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))

    def create_ticket(self, requester_phone: str, draft: TicketDraft) -> dict[str, Any]:
        with self._connect() as connection:
            next_id = connection.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM tickets"
            ).fetchone()["next_id"]
            external_id = f"IT-{next_id:05d}"
            connection.execute(
                """
                INSERT INTO tickets (external_id, requester_phone, draft_json, status)
                VALUES (?, ?, ?, 'nuevo')
                """,
                (external_id, requester_phone, draft.model_dump_json()),
            )
            row = connection.execute(
                "SELECT * FROM tickets WHERE external_id = ?",
                (external_id,),
            ).fetchone()
        return dict(row)

    def list_tickets(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, external_id, requester_phone, draft_json, status, created_at FROM tickets ORDER BY id DESC"
            ).fetchall()
        tickets: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["draft"] = json.loads(item.pop("draft_json"))
            tickets.append(item)
        return tickets

