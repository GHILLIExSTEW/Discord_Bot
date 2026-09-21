from typing import Any

from supabase import Client, create_client

from src.config import SUPABASE_URL, SUPABASE_KEY


class SupabaseService:
    def __init__(self) -> None:
        self.client: Client | None = None
        if SUPABASE_URL and SUPABASE_KEY:
            self.client = create_client(SUPABASE_URL, SUPABASE_KEY)

    def _ensure_client(self) -> Client:
        if self.client is None:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be configured.")
        return self.client

    def select(self, table: str, columns: str = "*", filters: dict[str, Any] | None = None):
        client = self._ensure_client()
        query = client.table(table).select(columns)
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        return query.execute()

    def insert(self, table: str, payload: dict[str, Any] | list[dict[str, Any]]):
        return self._ensure_client().table(table).insert(payload).execute()

    def upsert(self, table: str, payload: dict[str, Any] | list[dict[str, Any]], conflict_columns: list[str] | None = None):
        client = self._ensure_client()
        if conflict_columns:
            return client.table(table).upsert(
                payload,
                on_conflict=",".join(conflict_columns),
            ).execute()
        return client.table(table).upsert(payload).execute()

    def update(self, table: str, payload: dict[str, Any], match: dict[str, Any]):
        query = self._ensure_client().table(table).update(payload)
        for key, value in match.items():
            query = query.eq(key, value)
        return query.execute()

    def delete(self, table: str, match: dict[str, Any]):
        query = self._ensure_client().table(table).delete()
        for key, value in match.items():
            query = query.eq(key, value)
        return query.execute()


supabase_service = SupabaseService()
