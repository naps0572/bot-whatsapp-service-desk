from abc import ABC, abstractmethod
from typing import Any

import httpx

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


class ServiceDeskTicketAdapter(TicketAdapter):
    def __init__(self, api_url: str, api_key: str, fallback: TicketAdapter) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.fallback = fallback

    async def create_ticket(self, requester_phone: str, draft: TicketDraft) -> dict[str, Any]:
        if not self.api_url or not self.api_key:
            return await self.fallback.create_ticket(requester_phone, draft)

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.api_url}/integrations/service-desk-bot/tickets",
                headers={"x-service-bot-key": self.api_key},
                json=_to_service_desk_payload(requester_phone, draft),
            )
            response.raise_for_status()

        ticket = response.json()
        return {
            "id": ticket["id"],
            "external_id": f"SD-{ticket['id']}",
            "requester_phone": requester_phone,
            "draft": draft.model_dump(mode="json"),
            "status": str(ticket.get("status", "OPEN")).lower(),
            "created_at": ticket.get("createdAt"),
            "service_desk_ticket": ticket,
        }


def _to_service_desk_payload(requester_phone: str, draft: TicketDraft) -> dict[str, Any]:
    return {
        "requesterName": draft.requester_name,
        "requesterEmail": str(draft.requester_email) if draft.requester_email else None,
        "requesterPhone": requester_phone,
        "title": draft.summary or "Ticket creado desde WhatsApp",
        "description": _build_description(draft),
        "type": "SERVICE_REQUEST" if draft.ticket_type == "requerimiento" else "INCIDENT",
        "impact": _map_impact(draft),
        "urgency": _map_urgency(draft),
        "categoryName": draft.category or "General",
        "service": draft.affected_service or draft.category,
        "location": draft.location,
        "source": "bot-whatsapp-service-desk",
    }


def _build_description(draft: TicketDraft) -> str:
    details = [
        draft.description,
        f"Desde cuándo: {draft.since_when}" if draft.since_when else None,
        f"Mensaje de error: {draft.error_message}" if draft.error_message else None,
        f"Impacto reportado: {draft.impact_scope}" if draft.impact_scope else None,
        f"Continuidad operativa: {draft.can_work}" if draft.can_work else None,
        f"Urgencia indicada: {draft.urgency}" if draft.urgency else None,
    ]
    return "\n".join(item for item in details if item)


def _map_impact(draft: TicketDraft) -> str:
    impact = (draft.impact_scope or "").lower()
    if "empresa" in impact or "todos" in impact:
        return "HIGH"
    if "varios" in impact or "equipo" in impact or "área" in impact or "area" in impact:
        return "MEDIUM"
    return "LOW"


def _map_urgency(draft: TicketDraft) -> str:
    urgency = f"{draft.urgency or ''} {draft.priority or ''} {draft.can_work or ''}".lower()
    if "critica" in urgency or "crítica" in urgency or "alta" in urgency or "no puedo" in urgency:
        return "HIGH"
    if "media" in urgency or draft.ticket_type == "incidente":
        return "MEDIUM"
    return "LOW"

