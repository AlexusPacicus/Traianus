import { useState, useSyncExternalStore, type CSSProperties } from "react";
import { download, record, snapshot, subscribe } from "../runlog";

const TASKS = Array.from({ length: 10 }, (_, i) => `T${String(i + 1).padStart(2, "0")}`);

const controlStyle: CSSProperties = {
  padding: "4px 10px",
  border: "none",
  borderRadius: 6,
  color: "#F8FAFC",
  fontFamily: "monospace",
  fontSize: 12,
};

const noteStyle: CSSProperties = { overflowWrap: "anywhere" };

/**
 * The R5 run marks and the download of the log (runlog.ts). It shows no clock and changes nothing
 * in either view: it only writes marks into the log. `view` and `anchor` are what a run starts on.
 */
export default function RunLog({
  view,
  anchor,
}: {
  view: "overview" | "map" | "list";
  anchor: string | null;
}) {
  const { count, full, saved } = useSyncExternalStore(subscribe, snapshot);
  const [task, setTask] = useState("");
  const [run, setRun] = useState<string | null>(null);

  const start = () => {
    record("run_start", { task, view, anchor });
    setRun(task);
  };
  const stop = () => {
    if (run === null) return;
    record("run_stop", { task: run });
    setRun(null);
  };

  const startOff = task === "" || run !== null;
  return (
    <div
      role="group"
      aria-label="Run log"
      style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: "6px 12px",
        flexShrink: 0,
        padding: "6px 12px",
        borderTop: "1px solid #334155",
        color: "#F8FAFC",
        fontFamily: "monospace",
        fontSize: 12,
      }}
    >
      <select
        aria-label="Task"
        value={task}
        disabled={run !== null}
        onChange={(e) => setTask(e.target.value)}
        style={{ ...controlStyle, background: "#1E293B", border: "1px solid #334155" }}
      >
        <option value="">Task</option>
        {TASKS.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
      <button
        onClick={start}
        disabled={startOff}
        style={{
          ...controlStyle,
          background: "#6366F1",
          opacity: startOff ? 0.5 : 1,
          cursor: startOff ? "default" : "pointer",
        }}
      >
        Start
      </button>
      <button
        onClick={stop}
        disabled={run === null}
        style={{
          ...controlStyle,
          background: "#334155",
          opacity: run === null ? 0.5 : 1,
          cursor: run === null ? "default" : "pointer",
        }}
      >
        Stop
      </button>
      <button
        onClick={() => download()}
        style={{ ...controlStyle, background: "#334155", cursor: "pointer" }}
      >
        Download log ({count})
      </button>
      {full ? (
        <span role="status" style={{ ...noteStyle, color: "#94A3B8" }}>
          log full
        </span>
      ) : null}
      {saved ? null : (
        <span role="alert" style={{ ...noteStyle, color: "#F87171" }}>
          not saved: storage unavailable
        </span>
      )}
    </div>
  );
}
