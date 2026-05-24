import json
from typing import Any

import httpx

from app.config import Settings
from app.models import BotDecision, TicketDraft


SYSTEM_PROMPT = """
Eres un asistente experto en mesa de ayuda IT. Tu tarea es guiar al usuario por WhatsApp
para crear tickets completos y claros. No inventes datos. Si falta información, pregunta
solo una cosa por turno. Responde en JSON puro con esta estructura:
{
  "draft": {
    "requester_name": null,
    "requester_email": null,
    "location": null,
    "ticket_type": "incidente|requerimiento|consulta|cambio|desconocido",
    "category": null,
    "affected_service": null,
    "summary": null,
    "description": null,
    "since_when": null,
    "error_message": null,
    "impact_scope": null,
    "can_work": null,
    "urgency": null,
    "priority": "baja|media|alta|critica",
    "confirmed": false
  },
  "next_question": "pregunta corta en español o null",
  "ready_to_create": false,
  "user_wants_status": false,
  "confidence": 0.0
}
Prioriza capturar: nombre, correo, tipo, servicio afectado, resumen, descripción,
desde cuándo ocurre, impacto y confirmación final.
"""


class OpenRouterClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def analyze_message(
        self, current_draft: TicketDraft, user_message: str
    ) -> BotDecision:
        if not self.settings.openrouter_api_key:
            return BotDecision(draft=current_draft, confidence=0.0)

        payload = {
            "model": self.settings.openrouter_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "borrador_actual": current_draft.model_dump(mode="json"),
                            "mensaje_usuario": user_message,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0.1,
            "max_tokens": 900,
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=5.0)) as client:
            response = await client.post(
                f"{self.settings.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": self.settings.app_name,
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        parsed = self._parse_json(content)
        return BotDecision.model_validate(parsed)

    def _parse_json(self, content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.removeprefix("json").strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end >= start:
            cleaned = cleaned[start : end + 1]
        return json.loads(cleaned)
