import { getStore } from "@netlify/blobs";
import { getEnv } from "./env";
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
  const serviceDeskTicket = await createServiceDeskTicket(requesterPhone, draft);
  if (serviceDeskTicket) return serviceDeskTicket;

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

async function createServiceDeskTicket(requesterPhone: string, draft: TicketDraft) {
  const apiUrl = getEnv("SERVICE_DESK_API_URL").replace(/\/$/, "");
  const apiKey = getEnv("SERVICE_DESK_API_KEY");
  if (!apiUrl || !apiKey) return null;

  const response = await fetch(`${apiUrl}/integrations/service-desk-bot/tickets`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-service-bot-key": apiKey
    },
    body: JSON.stringify(toServiceDeskPayload(requesterPhone, draft))
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`No se pudo crear el ticket en Service Desk: ${response.status} ${errorText}`);
  }

  const ticket = await response.json();
  return {
    id: ticket.id,
    external_id: `SD-${ticket.id}`,
    requester_phone: requesterPhone,
    draft,
    status: ticket.status?.toLowerCase?.() ?? "open",
    created_at: ticket.createdAt,
    service_desk_ticket: ticket
  };
}

function toServiceDeskPayload(requesterPhone: string, draft: TicketDraft) {
  return {
    requesterName: draft.requester_name,
    requesterEmail: draft.requester_email,
    requesterPhone,
    title: draft.summary || "Ticket creado desde WhatsApp",
    description: buildDescription(draft),
    type: draft.ticket_type === "requerimiento" ? "SERVICE_REQUEST" : "INCIDENT",
    impact: mapImpact(draft),
    urgency: mapUrgency(draft),
    categoryName: draft.category || "General",
    service: draft.affected_service || draft.category,
    location: draft.location,
    source: "bot-whatsapp-service-desk"
  };
}

function buildDescription(draft: TicketDraft) {
  return [
    draft.description,
    draft.since_when ? `Desde cuándo: ${draft.since_when}` : null,
    draft.error_message ? `Mensaje de error: ${draft.error_message}` : null,
    draft.impact_scope ? `Impacto reportado: ${draft.impact_scope}` : null,
    draft.can_work ? `Continuidad operativa: ${draft.can_work}` : null,
    draft.urgency ? `Urgencia indicada: ${draft.urgency}` : null
  ]
    .filter(Boolean)
    .join("\n");
}

function mapImpact(draft: TicketDraft) {
  const impact = (draft.impact_scope ?? "").toLowerCase();
  if (impact.includes("empresa") || impact.includes("todos")) return "HIGH";
  if (impact.includes("varios") || impact.includes("equipo") || impact.includes("área") || impact.includes("area")) return "MEDIUM";
  return "LOW";
}

function mapUrgency(draft: TicketDraft) {
  const urgency = `${draft.urgency ?? ""} ${draft.priority ?? ""} ${draft.can_work ?? ""}`.toLowerCase();
  if (urgency.includes("critica") || urgency.includes("crítica") || urgency.includes("alta") || urgency.includes("no puedo")) return "HIGH";
  if (urgency.includes("media") || draft.ticket_type === "incidente") return "MEDIUM";
  return "LOW";
}

export async function listTickets() {
  const { blobs } = await store.list({ prefix: "tickets/" });
  const tickets = await Promise.all(
    blobs.map((blob) => store.get(blob.key, { type: "json" }))
  );
  return tickets.filter(Boolean).reverse();
}

