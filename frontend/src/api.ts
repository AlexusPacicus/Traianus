/**
 * Ulpia API client — fetches nodes and relations from Traianus backend.
 */

export interface NodesResponse {
  status: string;
  nodes: NodesNode[];
}

export interface NodesNode {
  id: string;
  text: string;
  toon_factor: string;
  lifecycle_state: string;
  action_potential: number;
  revision_milestone: number;
  projections_json: Record<string, number>;
}

export interface Relation {
  id: string;
  source: string;
  target: string;
  state: string;
}

export async function fetchNodes(): Promise<NodesNode[]> {
  const res = await fetch("/nodos");
  if (!res.ok) throw new Error(`GET /nodos failed: ${res.status}`);
  const data: NodesResponse = await res.json();
  return data.nodes ?? [];
}

export async function fetchRelations(token?: string): Promise<Relation[]> {
  try {
    const headers: Record<string, string> = {};
    if (token) headers["X-Traianus-Token"] = token;
    const res = await fetch("/relations", { headers });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export async function ingestText(text: string, token: string): Promise<string> {
  const res = await fetch("/ingesta", {
    method: "POST",
    headers: {
      "Content-Type": "text/plain",
      "X-Traianus-Token": token,
      "X-Idempotency-Key": crypto.randomUUID(),
    },
    body: text,
  });
  if (!res.ok) throw new Error(`POST /ingesta failed: ${res.status}`);
  const data = await res.json();
  return data.ingestion_id;
}
