import { getEnv } from "./env";
import { BotDecision, TicketDraft } from "./types";

const systemPrompt = `
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
`;

export async function analyzeWithOpenRouter(
  currentDraft: TicketDraft,
  userMessage: string
): Promise<BotDecision | null> {
  const apiKey = getEnv("OPENROUTER_API_KEY");
  if (!apiKey) return null;

  const baseUrl = getEnv("OPENROUTER_BASE_URL") || "https://openrouter.ai/api/v1";
  const model = getEnv("OPENROUTER_MODEL") || "openrouter/free";

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://netlify.app",
      "X-Title": "Bot WhatsApp Service Desk IT"
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: "system", content: systemPrompt },
        {
          role: "user",
          content: JSON.stringify({
            borrador_actual: currentDraft,
            mensaje_usuario: userMessage
          })
        }
      ],
      temperature: 0.1,
      max_tokens: 900
    }),
    signal: AbortSignal.timeout(8000)
  });

  if (!response.ok) return null;
  const data = await response.json();
  const content = data?.choices?.[0]?.message?.content ?? "";
  const jsonText = content.slice(content.indexOf("{"), content.lastIndexOf("}") + 1);
  return JSON.parse(jsonText) as BotDecision;
}

