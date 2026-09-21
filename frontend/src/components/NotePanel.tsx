import { useMemo, useState } from "react";
import type { Relation } from "../api";
import { markDotStyle } from "../lifecycle";
import { relationsOf, type NoteInfo } from "../notes";

const buttonStyle = {
  alignSelf: "flex-start",
  padding: "8px 16px",
  background: "#6366F1",
  border: "none",
  borderRadius: 6,
  color: "#F8FAFC",
  fontFamily: "monospace",
  fontSize: 13,
  cursor: "pointer",
} as const;

/**
 * One note in full: id, lifecycle state and text. Its edges from GET /relations, each as the other
 * end and the edge state, stay hidden until the toggle is pressed; the toggle starts off for every
 * mounted panel. `onSelect`, when given, offers to make this note the selection.
 */
export default function NotePanel({
  id,
  note,
  relations,
  onSelect,
}: {
  id: string;
  note: NoteInfo | undefined;
  relations: readonly Relation[];
  onSelect: (() => void) | null;
}) {
  const [showRelations, setShowRelations] = useState(false);
  const { total, shown } = useMemo(() => relationsOf(id, relations), [id, relations]);
  return (
    <section
      aria-label="Note"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 8,
        padding: "10px 12px",
        color: "#F8FAFC",
        fontFamily: "monospace",
        fontSize: 13,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 600 }}>
        <span style={markDotStyle(note?.state)} />
        <span style={{ overflowWrap: "anywhere" }}>{id}</span>
      </div>
      <div style={{ color: "#94A3B8" }}>{note?.state ?? "unknown"}</div>
      <div style={{ overflowWrap: "anywhere", whiteSpace: "pre-wrap" }}>{note?.text}</div>
      {onSelect ? (
        <button onClick={onSelect} style={buttonStyle}>
          Select this note
        </button>
      ) : null}
      <button
        aria-pressed={showRelations}
        onClick={() => setShowRelations((on) => !on)}
        style={{ ...buttonStyle, background: showRelations ? "#6366F1" : "#334155" }}
      >
        {showRelations ? "Hide relations" : "Show relations"}
      </button>
      {showRelations ? (
        <>
          <div style={{ color: "#94A3B8" }}>
            {total === 0
              ? "No relations"
              : `Relations: ${total}${total > shown.length ? ` (first ${shown.length})` : ""}`}
          </div>
          {shown.map((r) => (
            <div key={r.id} style={{ overflowWrap: "anywhere" }}>
              {r.other} · {r.state}
            </div>
          ))}
        </>
      ) : null}
    </section>
  );
}
