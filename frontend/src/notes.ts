import type { NodesNode, Relation, SpatialObservable } from "./api";

/** What GET /nodos says of a note: its text and its lifecycle state. */
export interface NoteInfo {
  readonly text: string;
  readonly state: string;
}

/** Notes in the nearest list. */
export const NEAREST_COUNT = 15;
/** Edges the note panel lists; the panel states the total besides. */
export const RELATIONS_SHOWN = 15;

/** Every current note, by id, as GET /nodos lists them. */
export const notesOf = (nodes: readonly NodesNode[]): ReadonlyMap<string, NoteInfo> =>
  new Map<string, NoteInfo>(
    nodes.map((node) => [node.id, { text: node.text, state: node.lifecycle_state }])
  );

/**
 * Ids of the `count` notes nearest to `anchor` in its perspective: the highest y, the anchor left
 * out, in descending order of y. y is the z-scored real-distance order to the anchor, so the list
 * needs no request beyond the perspective. Equal y keep the order of the response.
 */
export const nearestIds = (
  nodes: readonly SpatialObservable[],
  anchor: string,
  count = NEAREST_COUNT
): string[] =>
  nodes
    .filter((node) => node.id !== anchor)
    .sort((a, b) => b.y - a.y)
    .slice(0, count)
    .map((node) => node.id);

export interface NoteRelations {
  total: number;
  shown: { id: string; other: string; state: string }[];
}

/** The edges that have `id` at either end, as the other end and the edge state; `shown` is the first `limit`. */
export function relationsOf(
  id: string,
  relations: readonly Relation[],
  limit = RELATIONS_SHOWN
): NoteRelations {
  const own = relations.filter((r) => r.source === id || r.target === id);
  return {
    total: own.length,
    shown: own
      .slice(0, limit)
      .map((r) => ({ id: r.id, other: r.source === id ? r.target : r.source, state: r.state })),
  };
}
