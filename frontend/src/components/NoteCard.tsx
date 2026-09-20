import { markDotStyle } from "../lifecycle";
import type { NoteInfo } from "../notes";

/** A pointer position on the map, in CSS pixels from the canvas's top-left corner, and the canvas's size. */
export interface Pointer {
  x: number;
  y: number;
  width: number;
  height: number;
}

const CARD_WIDTH = 320;
const GAP = 14;
const MARGIN = 8;

/**
 * The card of a note pointed at on the map. It sits beside the pointer, on the side with room: to
 * the right unless that leaves the canvas, below in the upper half and above in the lower half.
 * It takes no pointer events, so it never gets between the pointer and the map.
 */
export default function NoteCard({
  id,
  note,
  at,
}: {
  id: string;
  note: NoteInfo | undefined;
  at: Pointer;
}) {
  const width = Math.min(CARD_WIDTH, at.width - 2 * MARGIN);
  const left =
    at.x + GAP + width <= at.width - MARGIN ? at.x + GAP : Math.max(MARGIN, at.x - GAP - width);
  const below = at.y <= at.height / 2;
  return (
    <div
      style={{
        position: "absolute",
        zIndex: 1,
        left,
        width,
        ...(below ? { top: at.y + GAP } : { bottom: at.height - at.y + GAP }),
        maxHeight: (below ? at.height - at.y : at.y) - GAP - MARGIN,
        overflow: "hidden",
        boxSizing: "border-box",
        padding: "8px 12px",
        background: "#1E293B",
        border: "1px solid #334155",
        borderRadius: 6,
        color: "#F8FAFC",
        fontFamily: "monospace",
        fontSize: 12,
        pointerEvents: "none",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 600 }}>
        <span style={markDotStyle(note?.state)} />
        <span style={{ overflowWrap: "anywhere" }}>{id}</span>
      </div>
      <div style={{ color: "#94A3B8" }}>{note?.state ?? "unknown"}</div>
      <div style={{ marginTop: 6, overflowWrap: "anywhere", whiteSpace: "pre-wrap" }}>
        {note?.text}
      </div>
    </div>
  );
}
