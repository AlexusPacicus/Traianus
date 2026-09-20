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

export interface SpatialObservable {
  id: string;
  x: number;
  y: number;
  z: number;
  l: number;
  c: number;
  h: number;
}

export interface SpatialResponse {
  nodes: SpatialObservable[];
}

export interface PerspectiveResponse extends SpatialResponse {
  anchor: string;
  poles: [string, string];
  fallback: boolean;
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

export async function fetchSpatial(token: string): Promise<SpatialObservable[]> {
  const res = await fetch("/spatial", {
    headers: { "X-Traianus-Token": token },
  });
  if (!res.ok) throw new Error(`GET /spatial failed: ${res.status}`);
  const data: SpatialResponse = await res.json();
  return data.nodes ?? [];
}

export async function fetchPerspective(token: string, anchor: string): Promise<PerspectiveResponse> {
  const res = await fetch(`/spatial?anchor=${encodeURIComponent(anchor)}`, {
    headers: { "X-Traianus-Token": token },
  });
  if (!res.ok) throw new Error(`GET /spatial?anchor failed: ${res.status}`);
  return res.json();
}

/** The engine turns an ingestion into a node asynchronously; GET /nodos is polled this often. */
export const POLL_INTERVAL_MS = 1000;
/** How long a node may take to be listed before the entry is reported as failed. */
export const NODE_WAIT_MS = 60_000;

/** Enters a note; a repeated `idempotencyKey` answers the first ingestion instead of a new one. */
export async function ingestText(text: string, token: string, idempotencyKey: string): Promise<string> {
  const res = await fetch("/ingesta", {
    method: "POST",
    headers: {
      "Content-Type": "text/plain",
      "X-Traianus-Token": token,
      "X-Idempotency-Key": idempotencyKey,
    },
    body: text,
  });
  if (!res.ok) throw new Error(`POST /ingesta failed: ${res.status}`);
  const data = await res.json();
  if (data.ingestion_id === undefined) throw new Error("POST /ingesta answered without an ingestion id");
  return String(data.ingestion_id);
}

/** Polls GET /nodos until `nodeId` is listed and returns that listing; rejects after NODE_WAIT_MS. */
export async function waitForNode(nodeId: string, signal?: AbortSignal): Promise<NodesNode[]> {
  const deadline = Date.now() + NODE_WAIT_MS;
  for (;;) {
    signal?.throwIfAborted();
    const nodes = await fetchNodes();
    if (nodes.some((node) => node.id === nodeId)) return nodes;
    if (Date.now() >= deadline) {
      throw new Error(`${nodeId} was not listed within ${NODE_WAIT_MS / 1000} s`);
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
}
