from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


TicketType = Literal["incidente", "requerimiento", "consulta", "cambio", "desconocido"]
Priority = Literal["baja", "media", "alta", "critica"]


class TicketDraft(BaseModel):
    requester_name: str | None = None
    requester_email: EmailStr | None = None
    location: str | None = None
    ticket_type: TicketType = "desconocido"
    category: str | None = None
    affected_service: str | None = None
    summary: str | None = None
    description: str | None = None
    since_when: str | None = None
    error_message: str | None = None
    impact_scope: str | None = None
    can_work: str | None = None
    urgency: str | None = None
    priority: Priority = "media"
    confirmed: bool = False


class BotDecision(BaseModel):
    draft: TicketDraft = Field(default_factory=TicketDraft)
    next_question: str | None = None
    ready_to_create: bool = False
    user_wants_status: bool = False
    confidence: float = 0.0


class IncomingMessage(BaseModel):
    channel: Literal["whatsapp", "api"] = "whatsapp"
    user_id: str
    text: str
    raw: dict[str, Any] | None = None


class TicketRecord(BaseModel):
    id: int
    external_id: str
    requester_phone: str
    draft: TicketDraft
    status: str = "nuevo"

