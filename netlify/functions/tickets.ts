import type { Config } from "@netlify/functions";
import { listTickets } from "./_shared/storage";

export default async (req: Request) => {
  if (req.method !== "GET") return new Response("Method not allowed", { status: 405 });
  return Response.json(await listTickets());
};

export const config: Config = {
  path: "/tickets"
};

