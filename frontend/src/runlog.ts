const KEY = "r5-run-log";
const CAP = 20000;

interface EventFields {
  select: { id: string; source: "map_click" | "id_field" | "panel_button" };
  point: { id: string };
  open: { id: string };
  view: { to: "map" | "list" };
  overview: { via: "escape" | "button" };
  relations_toggle: { id: string; on: boolean };
  ingest_submit: { length: number };
  run_start: { task: string; view: "overview" | "map" | "list"; anchor: string | null };
  run_stop: { task: string };
}

export type EventType = keyof EventFields;

export interface LogEvent {
  t: string;
  ms: number;
  type: EventType;
  [field: string]: unknown;
}

export interface LogState {
  count: number;
  full: boolean;
  /** False while the events exist in memory only, because localStorage failed. */
  saved: boolean;
}

function load(): { events: LogEvent[]; saved: boolean } {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    if (!Array.isArray(stored)) throw new TypeError("stored run log is not an array");
    return { events: stored as LogEvent[], saved: true };
  } catch {
    return { events: [], saved: false };
  }
}

const loaded = load();
const events = loaded.events;
let saved = loaded.saved;
let state: LogState = { count: events.length, full: events.length >= CAP, saved };
const listeners = new Set<() => void>();

/** Writes the whole log, so a write that failed earlier is made good by the next one that works. */
function persist() {
  try {
    localStorage.setItem(KEY, JSON.stringify(events));
    saved = true;
  } catch {
    saved = false;
  }
}

/** Ids, counts, task names and view names only: never a token, a body or the text of a note. */
export function record<T extends EventType>(type: T, fields: EventFields[T]): void {
  if (events.length >= CAP) return;
  events.push({ t: new Date().toISOString(), ms: Math.round(performance.now()), type, ...fields });
  persist();
  state = { count: events.length, full: events.length >= CAP, saved };
  listeners.forEach((listener) => listener());
}

export const snapshot = (): LogState => state;

export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Saves the log from memory as a JSON file. */
export function download(): void {
  const exportedAt = new Date().toISOString();
  const payload = {
    schema: "r5-run-log/1",
    exportedAt,
    viewport: [window.innerWidth, window.innerHeight],
    events,
  };
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `r5-run-log-${exportedAt.slice(0, 19).replace(/:/g, "-")}.json`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
