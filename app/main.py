from html import escape
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.adapters.itsm import LocalTicketAdapter, ServiceDeskTicketAdapter
from app.config import get_settings
from app.models import IncomingMessage
from app.services.openrouter import OpenRouterClient
from app.services.storage import Storage
from app.services.ticket_flow import TicketFlow
from app.services.whatsapp import WhatsAppSender

settings = get_settings()
storage = Storage(settings.database_path)
ai = OpenRouterClient(settings)
flow = TicketFlow(ai)
ticket_adapter = ServiceDeskTicketAdapter(
    settings.service_desk_api_url,
    settings.service_desk_api_key,
    LocalTicketAdapter(storage),
)
whatsapp = WhatsAppSender(settings)

app = FastAPI(title=settings.app_name)


@app.get("/")
async def root() -> dict[str, str]:
    return {"app": settings.app_name, "status": "ok"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "env": settings.app_env}


@app.get("/webhooks/whatsapp", response_class=PlainTextResponse)
async def verify_whatsapp_webhook(request: Request) -> str:
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode == "subscribe" and token == settings.whatsapp_verify_token and challenge:
        return challenge
    raise HTTPException(status_code=403, detail="Invalid verification token")


@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request) -> Any:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
        messages = _extract_meta_messages(payload)
        for message in messages:
            if not message.text:
                continue
            reply = await _handle_message(message)
            await whatsapp.send_text(message.user_id, reply)
        return {"status": "ok"}

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        message = _extract_twilio_message(dict(form))
        reply = await _handle_message(message) if message.text else ""
        return PlainTextResponse(_twiml(reply), media_type="application/xml")

    return {"status": "ignored"}


@app.post("/chat/test")
async def chat_test(message: IncomingMessage) -> dict[str, Any]:
    reply = await _handle_message(message)
    return {"reply": reply}


@app.get("/tickets")
async def list_tickets() -> list[dict[str, Any]]:
    return storage.list_tickets()


async def _handle_message(message: IncomingMessage) -> str:
    current = storage.get_draft(message.user_id)
    decision = await flow.process(current, message.text)

    if decision.ready_to_create:
        try:
            ticket = await ticket_adapter.create_ticket(message.user_id, decision.draft)
            storage.clear_draft(message.user_id)
            return (
                f"Ticket creado correctamente: {ticket['external_id']}\n"
                f"Prioridad: {decision.draft.priority}\n"
                "El equipo de Service Desk revisará tu caso."
            )
        except Exception:
            storage.save_draft(message.user_id, decision.draft)
            return (
                "Ya tengo la información del ticket, pero no pude registrarlo en Service Desk "
                "en este momento. Intenta responder 'sí' de nuevo en unos minutos."
            )

    storage.save_draft(message.user_id, decision.draft)
    return decision.next_question or "Necesito un poco más de información para crear el ticket."


def _extract_meta_messages(payload: dict[str, Any]) -> list[IncomingMessage]:
    incoming: list[IncomingMessage] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for item in value.get("messages", []):
                text = ""
                if item.get("type") == "text":
                    text = item.get("text", {}).get("body", "")
                elif item.get("type") in {"image", "document", "audio", "video"}:
                    text = f"El usuario envió un adjunto tipo {item.get('type')}."
                incoming.append(
                    IncomingMessage(
                        user_id=item.get("from", ""),
                        text=text,
                        raw=item,
                    )
                )
    return incoming


def _extract_twilio_message(form: dict[str, Any]) -> IncomingMessage:
    user_id = str(form.get("From", "")).replace("whatsapp:", "")
    return IncomingMessage(
        user_id=user_id,
        text=str(form.get("Body", "")),
        raw=form,
    )


def _twiml(text: str) -> str:
    return f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response><Message>{escape(text)}</Message></Response>"
