from abc import ABC, abstractmethod
from typing import Any

from app.models import TicketDraft
from app.services.storage import Storage


class TicketAdapter(ABC):
    @abstractmethod
    async def create_ticket(self, requester_phone: str, draft: TicketDraft) -> dict[str, Any]:
        raise NotImplementedError


class LocalTicketAdapter(TicketAdapter):
    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    async def create_ticket(self, requester_phone: str, draft: TicketDraft) -> dict[str, Any]:
        return self.storage.create_ticket(requester_phone, draft)

