import type { Config, Context } from "@netlify/functions";
import { clearDraft, createTicket, getDraft, saveDraft } from "./_shared/storage";
import { processMessage } from "./_shared/flow";
import { IncomingMessage } from "./_shared/types";
import { getEnv } from "./_shared/env";

export default async (req: Request, _context: Context) => {
  if (req.method === "GET") return verifyMetaWebhook(req);
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405 });

  const contentType = req.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    const payload = await req.json();
    const messages = extractMetaMessages(payload);
    for (const message of messages) {
      const reply = await handleMessage(message);
      await sendMetaText(message.user_id, reply);
    }
    return Response.json({ status: "ok" });
  }

  const form = await req.formData();
  const message = extractTwilioMessage(form);
  const reply = message.text ? await handleMessage(message) : "";
  return new Response(twiml(reply), {
    headers: { "Content-Type": "application/xml" }
  });
};

export const config: Config = {
  path: "/webhooks/whatsapp"
};

async function handleMessage(message: IncomingMessage) {
  const current = await getDraft(message.user_id);
  const decision = await processMessage(current, message.text);

  if (decision.ready_to_create) {
    const ticket = await createTicket(message.user_id, decision.draft);
    await clearDraft(message.user_id);
    return `Ticket creado correctamente: ${ticket.external_id}\nPrioridad: ${decision.draft.priority}\nEl equipo de Service Desk revisará tu caso.`;
  }

  await saveDraft(message.user_id, decision.draft);
  return decision.next_question ?? "Necesito un poco más de información para crear el ticket.";
}

function verifyMetaWebhook(req: Request) {
  const url = new URL(req.url);
  const mode = url.searchParams.get("hub.mode");
  const token = url.searchParams.get("hub.verify_token");
  const challenge = url.searchParams.get("hub.challenge");
  if (mode === "subscribe" && token === getEnv("WHATSAPP_VERIFY_TOKEN") && challenge) {
    return new Response(challenge);
  }
  return new Response("Invalid verification token", { status: 403 });
}

function extractTwilioMessage(form: FormData): IncomingMessage {
  const from = String(form.get("From") ?? "").replace("whatsapp:", "");
  return {
    user_id: from,
    text: String(form.get("Body") ?? ""),
    raw: Object.fromEntries(form.entries())
  };
}

function extractMetaMessages(payload: any): IncomingMessage[] {
  const incoming: IncomingMessage[] = [];
  for (const entry of payload.entry ?? []) {
    for (const change of entry.changes ?? []) {
      for (const item of change.value?.messages ?? []) {
        incoming.push({
          user_id: item.from ?? "",
          text: item.type === "text" ? item.text?.body ?? "" : `El usuario envió un adjunto tipo ${item.type}.`,
          raw: item
        });
      }
    }
  }
  return incoming;
}

function twiml(text: string) {
  return `<?xml version="1.0" encoding="UTF-8"?><Response><Message>${escapeXml(text)}</Message></Response>`;
}

function escapeXml(text: string) {
  return text.replace(/[<>&'"]/g, (char) => {
    const map: Record<string, string> = {
      "<": "&lt;",
      ">": "&gt;",
      "&": "&amp;",
      "'": "&apos;",
      "\"": "&quot;"
    };
    return map[char];
  });
}

async function sendMetaText(to: string, text: string) {
  const token = getEnv("WHATSAPP_ACCESS_TOKEN");
  const phoneNumberId = getEnv("WHATSAPP_PHONE_NUMBER_ID");
  if (!token || !phoneNumberId) return;

  const version = getEnv("WHATSAPP_GRAPH_VERSION") || "v24.0";
  await fetch(`https://graph.facebook.com/${version}/${phoneNumberId}/messages`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      messaging_product: "whatsapp",
      to,
      type: "text",
      text: { body: text }
    })
  });
}

