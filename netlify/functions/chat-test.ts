import type { Config } from "@netlify/functions";
import { clearDraft, createTicket, getDraft, saveDraft } from "./_shared/storage";
import { processMessage } from "./_shared/flow";

export default async (req: Request) => {
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405 });
  const body = await req.json();
  const userId = String(body.user_id ?? "test-user");
  const text = String(body.text ?? "");

  const current = await getDraft(userId);
  const decision = await processMessage(current, text);

  if (decision.ready_to_create) {
    const ticket = await createTicket(userId, decision.draft);
    await clearDraft(userId);
    return Response.json({
      reply: `Ticket creado correctamente: ${ticket.external_id}`,
      ticket
    });
  }

  await saveDraft(userId, decision.draft);
  return Response.json({ reply: decision.next_question, draft: decision.draft });
};

export const config: Config = {
  path: "/chat/test"
};

