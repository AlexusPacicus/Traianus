import type { SpatialObservable } from "./api";

/** Largest |x| or |y| of a perspective once placed on the plane, which spans [-1, 1]. */
export const PERSPECTIVE_EXTENT = 0.8;

/**
 * Places a perspective's z-scored coordinates on the plane: x and y are multiplied by one common
 * factor, so that the largest |x| or |y| equals `extent`; z, l, c, h and ids are untouched.
 *
 * Nothing is clipped. The anchor's own y is the largest similarity there is, so it and its nearest
 * neighbours lie in the far tail, and clipping at a few standard deviations would pile them on the
 * edge. One factor for both axes keeps the Euclidean geometry the engine measured.
 */
export function fitPerspective(
  nodes: readonly SpatialObservable[],
  extent = PERSPECTIVE_EXTENT
): SpatialObservable[] {
  let largest = 0;
  for (const { x, y } of nodes) largest = Math.max(largest, Math.abs(x), Math.abs(y));
  const factor = largest === 0 ? 1 : extent / largest;
  return nodes.map((node) => ({ ...node, x: node.x * factor, y: node.y * factor }));
}
