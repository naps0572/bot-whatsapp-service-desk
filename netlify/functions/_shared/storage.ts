import { getStore } from "@netlify/blobs";
import { TicketDraft, emptyDraft } from "./types";

const store = getStore({ name: "service-desk-bot", consistency: "strong" });

export async function getDraft(userId: string): Promise<TicketDraft> {
  const draft = await store.get(`conversations/${userId}`, { type: "json" });
  return (draft as TicketDraft | null) ?? emptyDraft();
}

export async function saveDraft(userId: string, draft: TicketDraft): Promise<void> {
  await store.setJSON(`conversations/${userId}`, draft);
}

export async function clearDraft(userId: string): Promise<void> {
  await store.delete(`conversations/${userId}`);
}

export async function createTicket(requesterPhone: string, draft: TicketDraft) {
  const counter = ((await store.get("counter", { type: "json" })) as { value: number } | null) ?? {
    value: 0
  };
  const next = counter.value + 1;
  await store.setJSON("counter", { value: next });

  const externalId = `IT-${String(next).padStart(5, "0")}`;
  const ticket = {
    external_id: externalId,
    requester_phone: requesterPhone,
    draft,
    status: "nuevo",
    created_at: new Date().toISOString()
  };
  await store.setJSON(`tickets/${externalId}`, ticket);
  return ticket;
}

export async function listTickets() {
  const { blobs } = await store.list({ prefix: "tickets/" });
  const tickets = await Promise.all(
    blobs.map((blob) => store.get(blob.key, { type: "json" }))
  );
  return tickets.filter(Boolean).reverse();
}

