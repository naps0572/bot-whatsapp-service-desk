from typing import Any

import httpx

from app.config import Settings


class WhatsAppSender:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send_text(self, to: str, text: str) -> None:
        provider = self.settings.whatsapp_provider.lower()
        if provider == "meta":
            await self._send_meta(to, text)
            return
        if provider == "twilio":
            await self._send_twilio(to, text)
            return
        print(f"[WHATSAPP:console] To {to}: {text}")

    async def _send_meta(self, to: str, text: str) -> None:
        url = (
            f"https://graph.facebook.com/{self.settings.whatsapp_graph_version}/"
            f"{self.settings.whatsapp_phone_number_id}/messages"
        )
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {self.settings.whatsapp_access_token}"},
                json=payload,
            )
            response.raise_for_status()

    async def _send_twilio(self, to: str, text: str) -> None:
        url = (
            "https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.settings.twilio_account_sid}/Messages.json"
        )
        data = {
            "From": self.settings.twilio_from_whatsapp,
            "To": f"whatsapp:{to}" if not to.startswith("whatsapp:") else to,
            "Body": text,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                url,
                data=data,
                auth=(self.settings.twilio_account_sid, self.settings.twilio_auth_token),
            )
            response.raise_for_status()
