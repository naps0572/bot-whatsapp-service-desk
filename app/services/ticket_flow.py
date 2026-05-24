import re

from pydantic import ValidationError

from app.models import BotDecision, TicketDraft
from app.services.openrouter import OpenRouterClient


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


class TicketFlow:
    def __init__(self, ai: OpenRouterClient) -> None:
        self.ai = ai

    async def process(self, current: TicketDraft, text: str) -> BotDecision:
        base = self._merge_with_rules(current, text)
        try:
            decision = await self.ai.analyze_message(base, text)
            draft = self._prefer_non_empty(base, decision.draft)
        except Exception:
            draft = base

        draft.priority = self._calculate_priority(draft)
        ready = self._has_minimum_fields(draft) and draft.confirmed
        next_question = None if ready else self._next_question(draft)
        return BotDecision(
            draft=draft,
            next_question=next_question,
            ready_to_create=ready,
            confidence=0.8,
        )

    def _merge_with_rules(self, draft: TicketDraft, text: str) -> TicketDraft:
        data = draft.model_dump()
        lowered = text.lower().strip()

        email = EMAIL_RE.search(text)
        if email:
            data["requester_email"] = email.group(0)

        if lowered in {"si", "sí", "confirmo", "crear", "ok", "dale", "correcto"}:
            data["confirmed"] = True

        if data["ticket_type"] == "desconocido":
            if any(word in lowered for word in ["no funciona", "error", "caido", "caído", "falla", "problema"]):
                data["ticket_type"] = "incidente"
            elif any(word in lowered for word in ["necesito", "solicito", "acceso", "instalar", "crear usuario"]):
                data["ticket_type"] = "requerimiento"

        categories = {
            "vpn": "Red/VPN",
            "correo": "Correo",
            "email": "Correo",
            "impresora": "Impresoras",
            "wifi": "Red/WiFi",
            "internet": "Red/Internet",
            "sap": "Aplicaciones/SAP",
            "office": "Software/Office",
            "teams": "Colaboracion/Teams",
            "contraseña": "Accesos",
            "password": "Accesos",
        }
        for keyword, category in categories.items():
            if keyword in lowered:
                data["category"] = category
                data["affected_service"] = data["affected_service"] or keyword.upper()
                break

        if not data["description"] and len(text) > 12:
            data["description"] = text
        if not data["summary"] and len(text) > 12:
            data["summary"] = text[:80]

        try:
            return TicketDraft.model_validate(data)
        except ValidationError:
            data["requester_email"] = draft.requester_email
            return TicketDraft.model_validate(data)

    def _prefer_non_empty(self, base: TicketDraft, ai_draft: TicketDraft) -> TicketDraft:
        merged = base.model_dump()
        for key, value in ai_draft.model_dump().items():
            if value not in (None, "", "desconocido"):
                merged[key] = value
        return TicketDraft.model_validate(merged)

    def _calculate_priority(self, draft: TicketDraft) -> str:
        impact = (draft.impact_scope or "").lower()
        urgency = (draft.urgency or "").lower()
        can_work = (draft.can_work or "").lower()
        if "empresa" in impact or "todos" in impact or "critica" in urgency or "crítica" in urgency:
            return "critica"
        if "varios" in impact or "no puedo" in can_work or "alta" in urgency:
            return "alta"
        if "media" in urgency or draft.ticket_type == "incidente":
            return "media"
        return "baja"

    def _has_minimum_fields(self, draft: TicketDraft) -> bool:
        return all(
            [
                draft.requester_email,
                draft.ticket_type != "desconocido",
                draft.summary,
                draft.description,
                draft.affected_service or draft.category,
                draft.impact_scope,
            ]
        )

    def _next_question(self, draft: TicketDraft) -> str:
        if not draft.requester_name:
            return "Para iniciar, dime tu nombre completo."
        if not draft.requester_email:
            return "Indícame tu correo corporativo."
        if draft.ticket_type == "desconocido":
            return "¿Esto es un incidente, un requerimiento, una consulta o un cambio?"
        if not draft.affected_service and not draft.category:
            return "¿Qué servicio o sistema está afectado? Por ejemplo VPN, correo, WiFi, SAP, impresora."
        if not draft.description:
            return "Cuéntame qué ocurre con el mayor detalle posible."
        if not draft.since_when and draft.ticket_type == "incidente":
            return "¿Desde cuándo ocurre el problema?"
        if not draft.impact_scope:
            return "¿Te afecta solo a ti, a varios usuarios o a toda el área?"
        return self._confirmation_text(draft)

    def _confirmation_text(self, draft: TicketDraft) -> str:
        return (
            "Confirma si creo el ticket con este resumen:\n"
            f"- Tipo: {draft.ticket_type}\n"
            f"- Servicio/categoría: {draft.affected_service or draft.category}\n"
            f"- Resumen: {draft.summary}\n"
            f"- Prioridad sugerida: {draft.priority}\n"
            "Responde 'sí' para crearlo o escribe la corrección."
        )

