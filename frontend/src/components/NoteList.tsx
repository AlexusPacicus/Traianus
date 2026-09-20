import { markDotStyle } from "../lifecycle";
import type { NoteInfo } from "../notes";

/**
 * The notes nearest to the selected one, nearest first, each with its id and full text at once.
 * A row is a button: it opens that note in the panel and leaves the selection alone.
 */
export default function NoteList({
  ids,
  notes,
  opened,
  onOpen,
}: {
  ids: readonly string[];
  notes: ReadonlyMap<string, NoteInfo>;
  opened: string | null;
  onOpen: (id: string) => void;
}) {
  return (
    <div
      aria-label="Nearest notes"
      style={{
        position: "absolute",
        inset: 0,
        overflowY: "auto",
        background: "#0B0F19",
        color: "#F8FAFC",
        fontFamily: "monospace",
        fontSize: 13,
      }}
    >
      <ol style={{ margin: 0, padding: 0, listStyle: "none" }}>
        {ids.map((id, i) => {
          const note = notes.get(id);
          return (
            <li key={id}>
              <button
                aria-current={id === opened}
                title={note?.state}
                onClick={() => onOpen(id)}
                style={{
                  display: "flex",
                  gap: 10,
                  width: "100%",
                  padding: "8px 12px",
                  background: id === opened ? "#1E293B" : "transparent",
                  border: "none",
                  borderBottom: "1px solid #1E293B",
                  color: "inherit",
                  font: "inherit",
                  textAlign: "left",
                  cursor: "pointer",
                }}
              >
                <span style={{ flexShrink: 0, minWidth: "2ch", color: "#94A3B8" }}>{i + 1}</span>
                <span style={{ minWidth: 0 }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 600 }}>
                    <span style={markDotStyle(note?.state)} />
                    <span style={{ overflowWrap: "anywhere" }}>{id}</span>
                  </span>
                  <span
                    style={{ display: "block", overflowWrap: "anywhere", whiteSpace: "pre-wrap" }}
                  >
                    {note?.text}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
