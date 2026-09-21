import { useEffect, useRef, useState, type ReactNode } from "react";
import { fetchPerspective, fetchSpatial, type Relation, type SpatialObservable } from "../api";
import { packRestingBuffer } from "../binary";
import {
  HOME, panBy, pickNearest, projectionMatrix, viewMatrix, wheelFactor, zoomAt, type Camera,
} from "../camera";
import { LIFECYCLE_MARKS, markDotStyle, packLifecycle } from "../lifecycle";
import { nearestIds, type NoteInfo } from "../notes";
import { fitPerspective } from "../perspective";
import { UlpiaRenderer } from "../ulpia_renderer";
import NoteCard, { type Pointer } from "./NoteCard";
import NoteList from "./NoteList";
import NotePanel from "./NotePanel";

interface UlpiaWebGLProps {
  token: string;
  /** Text and lifecycle state of every current node, by id (GET /nodos). */
  notes: ReadonlyMap<string, NoteInfo>;
  /** Every current edge (GET /relations). */
  relations: readonly Relation[];
  /** Raised once per note entered: the map fetches GET /spatial again and shows the new node. */
  version: number;
  /** The entry bar: it heads the same wrapping row as the id field and the perspective overlay. */
  children: ReactNode;
}

/** A click, and the hover card, pick the nearest node within this many CSS pixels. */
const PICK_RADIUS = 12;
/** A pointer that moves at most this many pixels between down and up is a click; more is a pan. */
const CLICK_SLOP = 4;

interface Layout {
  ids: string[];
  xs: number[];
  ys: number[];
}

/** Ids and world positions of a node list, in the order its buffer is drawn. */
const layoutOf = (nodes: SpatialObservable[]): Layout => ({
  ids: nodes.map((n) => n.id),
  xs: nodes.map((n) => n.x),
  ys: nodes.map((n) => n.y),
});

interface PerspectiveInfo {
  anchor: string;
  poles: [string, string];
  fallback: boolean;
  /** The nearest notes to the anchor, nearest first. */
  nearest: string[];
}

/** The pointer is on this node; `x`, `y` and the size are those of the pointer, see `Pointer`. */
type Hover = Pointer & { id: string };

type View = "map" | "list";

/** Below this window width the panel goes under the map or the list; from it, beside. */
const WIDE_QUERY = "(min-width: 900px)";
/** Room the header keeps at its right for App.jsx's Disconnect button (top 12, right 12, z 20). */
const DISCONNECT_ROOM = 108;
const RULE = "1px solid #334155";

const blockStyle = { flex: "1 1 280px", minWidth: 0, maxWidth: 420 } as const;

const boxStyle = {
  display: "flex",
  flexDirection: "column",
  alignItems: "flex-start",
  gap: 6,
  padding: "8px 12px",
  background: "#1E293B",
  border: RULE,
  borderRadius: 6,
  color: "#F8FAFC",
  fontFamily: "monospace",
  fontSize: 13,
  overflowWrap: "anywhere",
} as const;

const buttonStyle = {
  padding: "8px 16px",
  border: "none",
  borderRadius: 6,
  color: "#F8FAFC",
  fontFamily: "monospace",
  fontSize: 13,
  cursor: "pointer",
} as const;

function useWideScreen(): boolean {
  const [wide, setWide] = useState(() => window.matchMedia(WIDE_QUERY).matches);
  useEffect(() => {
    const query = window.matchMedia(WIDE_QUERY);
    const onChange = () => setWide(query.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return wide;
}

/** Wheel zooms about the cursor, dragging pans, a click reports its pixel, double-click goes home. */
function attachNavigation(
  canvas: HTMLCanvasElement,
  get: () => Camera,
  set: (camera: Camera) => void,
  onClick: (px: number, py: number, width: number, height: number) => void,
  onHover: (at: Pointer | null) => void
): () => void {
  let drag: { x: number; y: number; x0: number; y0: number } | null = null;

  const onWheel = (e: WheelEvent) => {
    e.preventDefault();
    onHover(null);
    const box = canvas.getBoundingClientRect();
    const factor = wheelFactor(e.deltaY, e.deltaMode);
    set(zoomAt(get(), factor, e.clientX - box.left, e.clientY - box.top, box.width, box.height));
  };
  const onDown = (e: PointerEvent) => {
    if (e.button !== 0) return;
    onHover(null);
    drag = { x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY };
    canvas.setPointerCapture(e.pointerId);
    canvas.style.cursor = "grabbing";
  };
  const onMove = (e: PointerEvent) => {
    const box = canvas.getBoundingClientRect();
    if (!drag) {
      onHover({
        x: e.clientX - box.left,
        y: e.clientY - box.top,
        width: box.width,
        height: box.height,
      });
      return;
    }
    set(panBy(get(), e.clientX - drag.x, e.clientY - drag.y, box.width, box.height));
    drag.x = e.clientX;
    drag.y = e.clientY;
  };
  const onLeave = () => onHover(null);
  const release = () => {
    drag = null;
    canvas.style.cursor = "grab";
  };
  const onUp = (e: PointerEvent) => {
    const start = drag;
    release();
    if (start && Math.hypot(e.clientX - start.x0, e.clientY - start.y0) <= CLICK_SLOP) {
      const box = canvas.getBoundingClientRect();
      onClick(e.clientX - box.left, e.clientY - box.top, box.width, box.height);
    }
  };
  const onHome = () => set(HOME);

  canvas.addEventListener("wheel", onWheel, { passive: false });
  canvas.addEventListener("pointerdown", onDown);
  canvas.addEventListener("pointermove", onMove);
  canvas.addEventListener("pointerup", onUp);
  canvas.addEventListener("pointercancel", release);
  canvas.addEventListener("pointerleave", onLeave);
  canvas.addEventListener("dblclick", onHome);
  return () => {
    canvas.removeEventListener("wheel", onWheel);
    canvas.removeEventListener("pointerdown", onDown);
    canvas.removeEventListener("pointermove", onMove);
    canvas.removeEventListener("pointerup", onUp);
    canvas.removeEventListener("pointercancel", release);
    canvas.removeEventListener("pointerleave", onLeave);
    canvas.removeEventListener("dblclick", onHome);
  };
}

/**
 * WebGL2 overlay for the Ulpia spatial canvas.
 *
 * Fetches per-node spatial observables from GET /spatial, packs them into the 64-byte zero-copy
 * contract and draws them at rest: a node never moves on screen except by the camera. Zoom and
 * pan only change the view matrix, and a click on a node swaps the resting buffer for the
 * perspective at that node (GET /spatial?anchor=), so navigation writes nothing to the engine (R2).
 *
 * Each node carries its lifecycle mark, a ring outside its body, from a separate one-byte buffer.
 * A new `version` refreshes the map on the same renderer: an overview keeps its camera, because
 * the epoch frame keeps every node where it was; an open perspective is requested again from the
 * same anchor, so it includes the new node, and keeps its camera too.
 *
 * It also lays out the whole screen as one column, so that no piece covers another and the map
 * gets what is left: the header (entry bar, id field, perspective overlay), the map or the list
 * with the note panel beside or under it, and the legend. The selection is the anchor of the open
 * perspective; pointing at a node shows a card and touches neither the selection nor the camera.
 * The map stays mounted, hidden, while the list is shown, so its camera is kept.
 */
export default function UlpiaWebGL({ token, notes, relations, version, children }: UlpiaWebGLProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const backRef = useRef<() => void>(() => {});
  const selectRef = useRef<(id: string) => void>(() => {});
  const refreshRef = useRef<() => void>(() => {});
  const marksRef = useRef<() => void>(() => {});
  const notesRef = useRef(notes);
  const [perspective, setPerspective] = useState<PerspectiveInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>("map");
  const [opened, setOpened] = useState<string | null>(null);
  const [hover, setHover] = useState<Hover | null>(null);
  const [idInput, setIdInput] = useState("");
  const [idMessage, setIdMessage] = useState<string | null>(null);
  const wide = useWideScreen();

  useEffect(() => {
    notesRef.current = notes;
    marksRef.current();
  }, [notes]);

  useEffect(() => {
    if (version > 0) refreshRef.current();
  }, [version]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    let rafId = 0;
    let cancelled = false;
    let detach = () => {};

    (async () => {
      try {
        const nodes = await fetchSpatial(token);
        if (cancelled || nodes.length === 0) return;

        const renderer = new UlpiaRenderer(canvas);
        let overview = packRestingBuffer(nodes);
        let overviewLayout = layoutOf(nodes);

        let camera: Camera = HOME;
        let shown = overviewLayout;
        let anchor: string | null = null;
        // Only the response to the latest request applies; going back voids the one in flight.
        let ticket = 0;

        // The lifecycle buffer always follows the resting buffer node for node.
        const showMarks = () =>
          renderer.uploadLifecycle(packLifecycle(shown.ids, notesRef.current));
        const show = (layout: Layout, buffer: ArrayBuffer) => {
          renderer.uploadRestingBuffer(buffer);
          shown = layout;
          showMarks();
          setHover(null);
        };
        show(overviewLayout, overview);
        marksRef.current = showMarks;

        const select = async (id: string, keepCamera = false) => {
          const mine = ++ticket;
          setError(null);
          try {
            const response = await fetchPerspective(token, id);
            if (cancelled || mine !== ticket) return;
            const fitted = fitPerspective(response.nodes);
            const index = fitted.findIndex((n) => n.id === response.anchor);
            if (index < 0) throw new Error(`Anchor ${response.anchor} is not in its perspective`);
            show(layoutOf(fitted), packRestingBuffer(fitted));
            renderer.setAnchor(index);
            anchor = response.anchor;
            if (!keepCamera) camera = HOME;
            setPerspective({
              anchor: response.anchor,
              poles: response.poles,
              fallback: response.fallback,
              nearest: nearestIds(response.nodes, response.anchor),
            });
            if (!keepCamera) setOpened(null);
          } catch (err) {
            if (!cancelled && mine === ticket) {
              setError(err instanceof Error ? err.message : String(err));
            }
          }
        };
        selectRef.current = (id) => void select(id);

        const back = () => {
          ticket++;
          setError(null);
          if (anchor === null) return;
          show(overviewLayout, overview);
          renderer.setAnchor(-1);
          anchor = null;
          camera = HOME;
          setPerspective(null);
          setOpened(null);
          setView("map");
        };
        backRef.current = back;

        const refresh = async () => {
          const seen = ticket;
          try {
            const fresh = await fetchSpatial(token);
            if (cancelled) return;
            overview = packRestingBuffer(fresh);
            overviewLayout = layoutOf(fresh);
            // A perspective is requested again unless the user has moved on since the refresh began.
            if (anchor === null) show(overviewLayout, overview);
            else if (seen === ticket) await select(anchor, true);
          } catch (err) {
            if (!cancelled) setError(err instanceof Error ? err.message : String(err));
          }
        };
        refreshRef.current = () => void refresh();

        const onClick = (px: number, py: number, width: number, height: number) => {
          const index = pickNearest(camera, shown.xs, shown.ys, px, py, width, height, PICK_RADIUS);
          if (index >= 0) void select(shown.ids[index]);
        };
        const onKey = (e: KeyboardEvent) => {
          if (e.key === "Escape") back();
        };

        const onHover = (at: Pointer | null) => {
          const index = at
            ? pickNearest(camera, shown.xs, shown.ys, at.x, at.y, at.width, at.height, PICK_RADIUS)
            : -1;
          const next = at && index >= 0 ? { ...at, id: shown.ids[index] } : null;
          // The card stays where it appeared for as long as the pointer stays on the same node.
          setHover((prev) => (prev?.id === next?.id ? prev : next));
        };

        const setCamera = (next: Camera) => {
          camera = next;
        };
        const detachNavigation = attachNavigation(canvas, () => camera, setCamera, onClick, onHover);
        window.addEventListener("keydown", onKey);
        detach = () => {
          detachNavigation();
          window.removeEventListener("keydown", onKey);
        };

        const loop = () => {
          if (cancelled) return;
          renderer.updateCamera(
            projectionMatrix(canvas.clientWidth, canvas.clientHeight),
            viewMatrix(camera)
          );
          renderer.renderFrame(shown.ids.length);
          rafId = requestAnimationFrame(loop);
        };
        rafId = requestAnimationFrame(loop);
      } catch (err) {
        if (!cancelled) {
          console.error("[UlpiaWebGL]", err);
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    })();

    return () => {
      cancelled = true;
      cancelAnimationFrame(rafId);
      detach();
      selectRef.current = () => {};
      refreshRef.current = () => {};
      marksRef.current = () => {};
      setPerspective(null);
      setError(null);
    };
  }, [token]);

  const list = view === "list" && perspective !== null;
  const panelId = perspective ? (opened ?? perspective.anchor) : null;

  const submitId = () => {
    const id = idInput.trim();
    if (!id) return;
    if (!notes.has(id)) {
      setIdMessage(`Unknown id: ${id}`);
      return;
    }
    setIdMessage(null);
    selectRef.current(id);
  };

  const chooseView = (next: View) => {
    setView(next);
    setHover(null);
    if (next === "map") setOpened(null);
  };

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        zIndex: 5,
        display: "flex",
        flexDirection: "column",
        background: "#0B0F19",
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "flex-start",
          gap: 8,
          flexShrink: 0,
          padding: `12px ${DISCONNECT_ROOM}px 8px 12px`,
        }}
      >
        <div style={blockStyle}>{children}</div>
        <div style={{ ...blockStyle, display: "flex", flexDirection: "column", gap: 6 }}>
          <input
            type="text"
            aria-label="Select note by id"
            placeholder="Select note by id"
            value={idInput}
            onChange={(e) => {
              setIdInput(e.target.value);
              setIdMessage(null);
            }}
            onKeyDown={(e) => e.key === "Enter" && submitId()}
            style={{
              padding: "8px 14px",
              background: "#1E293B",
              border: RULE,
              borderRadius: 6,
              color: "#F8FAFC",
              fontFamily: "monospace",
              fontSize: 13,
              outline: "none",
            }}
          />
          {idMessage ? (
            <div
              role="alert"
              style={{
                padding: "6px 10px",
                background: "#1E293B",
                border: "1px solid #F87171",
                borderRadius: 6,
                color: "#F87171",
                fontFamily: "monospace",
                fontSize: 12,
                overflowWrap: "anywhere",
              }}
            >
              {idMessage}
            </div>
          ) : null}
        </div>
        {perspective || error ? (
          <div style={{ ...blockStyle, ...boxStyle }}>
            {perspective ? (
              <>
                <div>Perspective at {perspective.anchor}</div>
                <div>
                  {perspective.poles.join(" · ")}
                  {perspective.fallback ? " (fallback dipole)" : ""}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  <button
                    onClick={() => backRef.current()}
                    style={{ ...buttonStyle, background: "#6366F1" }}
                  >
                    Overview (Esc)
                  </button>
                  <div role="group" aria-label="View" style={{ display: "flex", gap: 4 }}>
                    {(["map", "list"] as const).map((choice) => (
                      <button
                        key={choice}
                        aria-pressed={view === choice}
                        onClick={() => chooseView(choice)}
                        style={{ ...buttonStyle, background: view === choice ? "#6366F1" : "#334155" }}
                      >
                        {choice === "map" ? "Map" : "List"}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            ) : null}
            {error ? <div style={{ color: "#F87171" }}>{error}</div> : null}
          </div>
        ) : null}
      </div>
      <div
        style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: wide ? "row" : "column" }}
      >
        <div style={{ position: "relative", flex: 1, minWidth: 0, minHeight: 0 }}>
          <canvas
            ref={canvasRef}
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              cursor: "grab",
              touchAction: "none",
              visibility: list ? "hidden" : "visible",
            }}
          />
          {hover && !list ? <NoteCard id={hover.id} note={notes.get(hover.id)} at={hover} /> : null}
          {list ? (
            <NoteList
              key={perspective.anchor}
              ids={perspective.nearest}
              notes={notes}
              opened={opened}
              onOpen={setOpened}
            />
          ) : null}
        </div>
        {perspective && panelId !== null ? (
          <div
            key={panelId}
            style={
              wide
                ? { flex: "0 0 380px", overflowY: "auto", borderLeft: RULE }
                : { flex: "0 1 auto", maxHeight: "40vh", overflowY: "auto", borderTop: RULE }
            }
          >
            <NotePanel
              id={panelId}
              note={notes.get(panelId)}
              relations={relations}
              onSelect={panelId === perspective.anchor ? null : () => selectRef.current(panelId)}
            />
          </div>
        ) : null}
      </div>
      <div
        role="group"
        aria-label="Lifecycle marks"
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "4px 16px",
          flexShrink: 0,
          padding: "6px 12px",
          borderTop: RULE,
          color: "#F8FAFC",
          fontFamily: "monospace",
          fontSize: 13,
        }}
      >
        {LIFECYCLE_MARKS.map((mark) => (
          <div key={mark.state} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={markDotStyle(mark.state)} />
            {mark.state}
          </div>
        ))}
      </div>
    </div>
  );
}
