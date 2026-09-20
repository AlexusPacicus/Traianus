import type { CSSProperties } from "react";

/**
 * A lifecycle state the map marks. The mark is a ring drawn outside the node's body, so the body
 * keeps the size and colour that l, c and h give it; `ringPx` is the ring's width in CSS pixels.
 */
export interface LifecycleMark {
  state: string;
  hex: string;
  ringPx: number;
  alpha: number;
}

/** Incubating is the state of the whole corpus, so its ring is thin and translucent. */
export const LIFECYCLE_MARKS: readonly LifecycleMark[] = [
  { state: "pending_approval", hex: "#F59E0B", ringPx: 3, alpha: 1 },
  { state: "incubating", hex: "#3B82F6", ringPx: 1, alpha: 0.6 },
  { state: "consolidated", hex: "#10B981", ringPx: 2, alpha: 1 },
];

/** Shader table size: slot 0 is "no mark", slot i + 1 is LIFECYCLE_MARKS[i]. */
export const MARK_SLOTS = LIFECYCLE_MARKS.length + 1;

const slotOf = (state: string | undefined): number =>
  LIFECYCLE_MARKS.findIndex((mark) => mark.state === state) + 1;

/** One slot per id, in the order of the resting buffer; a state with no mark, or no state, is 0. */
export const packLifecycle = (
  ids: readonly string[],
  notes: ReadonlyMap<string, { readonly state: string }>
): Uint8Array => Uint8Array.from(ids, (id) => slotOf(notes.get(id)?.state));

const channel = (hex: string, index: number): number =>
  parseInt(hex.slice(1 + 2 * index, 3 + 2 * index), 16);

/** CSS colour of a mark, translucent as it is drawn on the map. */
const markCss = (mark: LifecycleMark): string =>
  `rgba(${channel(mark.hex, 0)}, ${channel(mark.hex, 1)}, ${channel(mark.hex, 2)}, ${mark.alpha})`;

/** A dot with the ring of `state`'s mark, as the legend and the note views show it; no ring without a mark. */
export const markDotStyle = (state: string | undefined): CSSProperties => {
  const mark = LIFECYCLE_MARKS.find((m) => m.state === state);
  return {
    display: "inline-block",
    flexShrink: 0,
    width: 10,
    height: 10,
    margin: 3,
    borderRadius: "50%",
    background: "#64748B",
    boxShadow: mark ? `0 0 0 ${mark.ringPx}px ${markCss(mark)}` : "none",
  };
};

/** The shader's tables: rgba per slot and ring width per slot, slot 0 all zero. */
export function markTables(): { colors: Float32Array; rings: Float32Array } {
  const colors = new Float32Array(4 * MARK_SLOTS);
  const rings = new Float32Array(MARK_SLOTS);
  LIFECYCLE_MARKS.forEach((mark, i) => {
    const slot = i + 1;
    colors.set(
      [channel(mark.hex, 0) / 255, channel(mark.hex, 1) / 255, channel(mark.hex, 2) / 255, mark.alpha],
      4 * slot
    );
    rings[slot] = mark.ringPx;
  });
  return { colors, rings };
}
