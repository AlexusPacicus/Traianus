/**
 * useUlpiaStore — Ulpia local-first store.
 *
 * Node geometry derives from semantic projections (projections_json ->
 * XYZ/LCH). This store does NOT read or write the 64B .purgativa struct;
 * that is a portable PKM concern confined to frontend/src/pkm/ (exodus).
 */
import { create } from "zustand";
import { TOPOLOGY } from "../config/traianus.constants";
import { sanitizeSomaticFlow } from "../pkm/sanitize";

export interface RenderNode {
  x: number;
  y: number;
  z: number;
  l: number;
  c: number;
  h: number;
  id: string;
}

export interface QuarantineItem {
  node: RenderNode;
  rawText: string;
  metadata: Record<string, unknown>;
  timestamp: number;
}

interface UlpiaState {
  nodes: Map<string, RenderNode>;
  quarantineQueue: Map<string, QuarantineItem>;
  activeNodeId: string | null;
  isLoading: boolean;
  error: string | null;
  heartRateBpm: number;
  isSomaticSyncActive: boolean;

  initializeStore: () => Promise<void>;
  ingestThought: (id: string, text: string, coords: Omit<RenderNode, "id">, metadata?: Record<string, unknown>) => void;
  consolidateThought: (id: string) => Promise<void>;
  rejectThought: (id: string) => void;
  selectNode: (id: string | null) => void;
  setHeartRate: (bpm: number) => void;
  toggleSomaticSync: () => void;
}

export const useUlpiaStore = create<UlpiaState>((set, get) => ({
  nodes: new Map(),
  quarantineQueue: new Map(),
  activeNodeId: null,
  isLoading: true,
  error: null,
  heartRateBpm: 60,
  isSomaticSyncActive: false,

  initializeStore: async () => {
    set({ isLoading: true, error: null });
    try {
      set({ isLoading: false, error: null });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ error: msg, isLoading: false });
    }
  },

  ingestThought: (id, text, coords, metadata = {}) => {
    let sanitized = text;
    let flagged = false;
    try {
      const res = sanitizeSomaticFlow(text);
      sanitized = res.sanitized;
      flagged = res.flagged;
    } catch {
      flagged = false;
    }
    if (flagged) metadata = { ...metadata, sanitized_by_guardian: true };
    const node: RenderNode = { id, ...coords };
    const item: QuarantineItem = { node, rawText: sanitized, metadata, timestamp: Date.now() };
    const q = new Map(get().quarantineQueue);
    q.set(id, item);
    set({ quarantineQueue: q });
  },

  consolidateThought: async (id) => {
    const { quarantineQueue, nodes } = get();
    const item = quarantineQueue.get(id);
    if (!item) throw new Error(`Nodo '${id}' no está en cuarentena`);
    const updatedNodes = new Map(nodes);
    updatedNodes.set(id, item.node);
    const q2 = new Map(quarantineQueue);
    q2.delete(id);
    set({ nodes: updatedNodes, quarantineQueue: q2 });
  },

  rejectThought: (id) => {
    const q = new Map(get().quarantineQueue);
    if (q.delete(id)) set({ quarantineQueue: q });
  },

  selectNode: (id) => set({ activeNodeId: id }),

  setHeartRate: (bpm) => set({ heartRateBpm: bpm }),

  toggleSomaticSync: () => set((s) => ({ isSomaticSyncActive: !s.isSomaticSyncActive })),
}));

export const useTraianusStore = useUlpiaStore;

export function computeIslands(vectors: Float32Array[], threshold = TOPOLOGY.THRESHOLD): number {
  if (vectors.length < 2) return vectors.length;
  const n = vectors.length;
  const visited = new Array(n).fill(false);
  let components = 0;
  const dist = (a: Float32Array, b: Float32Array) => {
    let s = 0;
    for (let i = 0; i < a.length; i++) {
      const d = a[i] - b[i];
      s += d * d;
    }
    return Math.sqrt(s);
  };
  for (let i = 0; i < n; i++) {
    if (visited[i]) continue;
    components++;
    const stack = [i];
    visited[i] = true;
    while (stack.length) {
      const u = stack.pop()!;
      for (let v = 0; v < n; v++) {
        if (!visited[v] && dist(vectors[u], vectors[v]) < threshold) {
          visited[v] = true;
          stack.push(v);
        }
      }
    }
  }
  return components;
}
