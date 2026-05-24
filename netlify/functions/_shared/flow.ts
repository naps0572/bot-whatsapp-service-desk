import { analyzeWithOpenRouter } from "./openrouter";
import { BotDecision, TicketDraft } from "./types";

const emailRe = /[\w.+-]+@[\w-]+\.[\w.-]+/;

export async function processMessage(current: TicketDraft, text: string): Promise<BotDecision> {
  const base = mergeWithRules(current, text);
  let draft = base;

  try {
    const aiDecision = await analyzeWithOpenRouter(base, text);
    if (aiDecision?.draft) draft = preferNonEmpty(base, aiDecision.draft);
  } catch {
    draft = base;
  }

  draft.priority = calculatePriority(draft);
  const ready = hasMinimumFields(draft) && draft.confirmed;

  return {
    draft,
    next_question: ready ? null : nextQuestion(draft),
    ready_to_create: ready,
    confidence: 0.8
  };
}

function mergeWithRules(draft: TicketDraft, text: string): TicketDraft {
  const data: TicketDraft = { ...draft };
  const lowered = text.toLowerCase().trim();
  const email = text.match(emailRe);
  if (email) data.requester_email = email[0];

  if (["si", "sí", "confirmo", "crear", "ok", "dale", "correcto"].includes(lowered)) {
    data.confirmed = true;
  }

  if (data.ticket_type === "desconocido") {
    if (["no funciona", "error", "caido", "caído", "falla", "problema"].some((word) => lowered.includes(word))) {
      data.ticket_type = "incidente";
    } else if (["necesito", "solicito", "acceso", "instalar", "crear usuario"].some((word) => lowered.includes(word))) {
      data.ticket_type = "requerimiento";
    }
  }

  const categories: Record<string, string> = {
    vpn: "Red/VPN",
    correo: "Correo",
    email: "Correo",
    impresora: "Impresoras",
    wifi: "Red/WiFi",
    internet: "Red/Internet",
    sap: "Aplicaciones/SAP",
    office: "Software/Office",
    teams: "Colaboracion/Teams",
    contraseña: "Accesos",
    password: "Accesos"
  };

  for (const [keyword, category] of Object.entries(categories)) {
    if (lowered.includes(keyword)) {
      data.category = category;
      data.affected_service ||= keyword.toUpperCase();
      break;
    }
  }

  if (!data.description && text.length > 12) data.description = text;
  if (!data.summary && text.length > 12) data.summary = text.slice(0, 80);
  return data;
}

function preferNonEmpty(base: TicketDraft, aiDraft: TicketDraft): TicketDraft {
  const merged = { ...base };
  for (const [key, value] of Object.entries(aiDraft)) {
    if (value !== null && value !== "" && value !== "desconocido") {
      (merged as any)[key] = value;
    }
  }
  return merged;
}

function calculatePriority(draft: TicketDraft) {
  const impact = (draft.impact_scope ?? "").toLowerCase();
  const urgency = (draft.urgency ?? "").toLowerCase();
  const canWork = (draft.can_work ?? "").toLowerCase();
  if (impact.includes("empresa") || impact.includes("todos") || urgency.includes("critica") || urgency.includes("crítica")) return "critica";
  if (impact.includes("varios") || canWork.includes("no puedo") || urgency.includes("alta")) return "alta";
  if (urgency.includes("media") || draft.ticket_type === "incidente") return "media";
  return "baja";
}

function hasMinimumFields(draft: TicketDraft) {
  return Boolean(
    draft.requester_email &&
      draft.ticket_type !== "desconocido" &&
      draft.summary &&
      draft.description &&
      (draft.affected_service || draft.category) &&
      draft.impact_scope
  );
}

function nextQuestion(draft: TicketDraft) {
  if (!draft.requester_name) return "Para iniciar, dime tu nombre completo.";
  if (!draft.requester_email) return "Indícame tu correo corporativo.";
  if (draft.ticket_type === "desconocido") return "¿Esto es un incidente, un requerimiento, una consulta o un cambio?";
  if (!draft.affected_service && !draft.category) return "¿Qué servicio o sistema está afectado? Por ejemplo VPN, correo, WiFi, SAP, impresora.";
  if (!draft.description) return "Cuéntame qué ocurre con el mayor detalle posible.";
  if (!draft.since_when && draft.ticket_type === "incidente") return "¿Desde cuándo ocurre el problema?";
  if (!draft.impact_scope) return "¿Te afecta solo a ti, a varios usuarios o a toda el área?";
  return `Confirma si creo el ticket con este resumen:\n- Tipo: ${draft.ticket_type}\n- Servicio/categoría: ${draft.affected_service || draft.category}\n- Resumen: ${draft.summary}\n- Prioridad sugerida: ${draft.priority}\nResponde 'sí' para crearlo o escribe la corrección.`;
}

