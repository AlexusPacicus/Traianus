import { useMemo } from "react";
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
 * One note in full: id, lifecycle state, text and its edges from GET /relations, each as the other
 * end and the edge state. `onSelect`, when given, offers to make this note the selection.
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
    </section>
  );
}
