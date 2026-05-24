export type TicketDraft = {
  requester_name?: string | null;
  requester_email?: string | null;
  location?: string | null;
  ticket_type: "incidente" | "requerimiento" | "consulta" | "cambio" | "desconocido";
  category?: string | null;
  affected_service?: string | null;
  summary?: string | null;
  description?: string | null;
  since_when?: string | null;
  error_message?: string | null;
  impact_scope?: string | null;
  can_work?: string | null;
  urgency?: string | null;
  priority: "baja" | "media" | "alta" | "critica";
  confirmed: boolean;
};

export type BotDecision = {
  draft: TicketDraft;
  next_question: string | null;
  ready_to_create: boolean;
  user_wants_status?: boolean;
  confidence?: number;
};

export type IncomingMessage = {
  user_id: string;
  text: string;
  raw?: unknown;
};

export function emptyDraft(): TicketDraft {
  return {
    ticket_type: "desconocido",
    priority: "media",
    confirmed: false
  };
}

