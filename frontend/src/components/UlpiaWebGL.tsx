import { useEffect, useRef, useState } from "react";
import { fetchPerspective, fetchSpatial, type SpatialObservable } from "../api";
import { packRestingBuffer } from "../binary";
import {
  HOME, panBy, pickNearest, projectionMatrix, viewMatrix, wheelFactor, zoomAt, type Camera,
} from "../camera";
import { fitPerspective } from "../perspective";
import { UlpiaRenderer } from "../ulpia_renderer";

interface UlpiaWebGLProps {
  token: string;
}

/** A click picks the nearest node within this many CSS pixels. */
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
}

const overlayStyle = {
  position: "absolute",
  top: 64,
  left: 12,
  zIndex: 6,
  display: "flex",
  flexDirection: "column",
  alignItems: "flex-start",
  gap: 6,
  maxWidth: "min(360px, calc(100% - 24px))",
  padding: "8px 12px",
  background: "#1E293B",
  border: "1px solid #334155",
  borderRadius: 6,
  color: "#F8FAFC",
  fontFamily: "monospace",
  fontSize: 13,
} as const;

/** Wheel zooms about the cursor, dragging pans, a click reports its pixel, double-click goes home. */
function attachNavigation(
  canvas: HTMLCanvasElement,
  get: () => Camera,
  set: (camera: Camera) => void,
  onClick: (px: number, py: number, width: number, height: number) => void
): () => void {
  let drag: { x: number; y: number; x0: number; y0: number } | null = null;

  const onWheel = (e: WheelEvent) => {
    e.preventDefault();
    const box = canvas.getBoundingClientRect();
    const factor = wheelFactor(e.deltaY, e.deltaMode);
    set(zoomAt(get(), factor, e.clientX - box.left, e.clientY - box.top, box.width, box.height));
  };
  const onDown = (e: PointerEvent) => {
    if (e.button !== 0) return;
    drag = { x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY };
    canvas.setPointerCapture(e.pointerId);
    canvas.style.cursor = "grabbing";
  };
  const onMove = (e: PointerEvent) => {
    if (!drag) return;
    const box = canvas.getBoundingClientRect();
    set(panBy(get(), e.clientX - drag.x, e.clientY - drag.y, box.width, box.height));
    drag.x = e.clientX;
    drag.y = e.clientY;
  };
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
  canvas.addEventListener("dblclick", onHome);
  return () => {
    canvas.removeEventListener("wheel", onWheel);
    canvas.removeEventListener("pointerdown", onDown);
    canvas.removeEventListener("pointermove", onMove);
    canvas.removeEventListener("pointerup", onUp);
    canvas.removeEventListener("pointercancel", release);
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
 */
export default function UlpiaWebGL({ token }: UlpiaWebGLProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const backRef = useRef<() => void>(() => {});
  const [perspective, setPerspective] = useState<PerspectiveInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

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
        const overview = packRestingBuffer(nodes);
        const overviewLayout = layoutOf(nodes);
        renderer.uploadRestingBuffer(overview);

        let camera: Camera = HOME;
        let shown = overviewLayout;
        let anchored = false;
        // Only the response to the latest request applies; going back voids the one in flight.
        let ticket = 0;

        const select = async (id: string) => {
          const mine = ++ticket;
          setError(null);
          try {
            const response = await fetchPerspective(token, id);
            if (cancelled || mine !== ticket) return;
            const fitted = fitPerspective(response.nodes);
            const index = fitted.findIndex((n) => n.id === response.anchor);
            if (index < 0) throw new Error(`Anchor ${response.anchor} is not in its perspective`);
            const buffer = packRestingBuffer(fitted);
            renderer.uploadRestingBuffer(buffer);
            renderer.setAnchor(index);
            shown = layoutOf(fitted);
            anchored = true;
            camera = HOME;
            setPerspective({
              anchor: response.anchor,
              poles: response.poles,
              fallback: response.fallback,
            });
          } catch (err) {
            if (!cancelled && mine === ticket) {
              setError(err instanceof Error ? err.message : String(err));
            }
          }
        };

        const back = () => {
          ticket++;
          setError(null);
          if (!anchored) return;
          renderer.uploadRestingBuffer(overview);
          renderer.setAnchor(-1);
          shown = overviewLayout;
          anchored = false;
          camera = HOME;
          setPerspective(null);
        };
        backRef.current = back;

        const onClick = (px: number, py: number, width: number, height: number) => {
          const index = pickNearest(camera, shown.xs, shown.ys, px, py, width, height, PICK_RADIUS);
          if (index >= 0) void select(shown.ids[index]);
        };
        const onKey = (e: KeyboardEvent) => {
          if (e.key === "Escape") back();
        };

        const setCamera = (next: Camera) => {
          camera = next;
        };
        const detachNavigation = attachNavigation(canvas, () => camera, setCamera, onClick);
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
        // Silence only when opted out; surface renderer init failures loudly.
        if (!cancelled) console.error("[UlpiaWebGL]", err);
      }
    })();

    return () => {
      cancelled = true;
      cancelAnimationFrame(rafId);
      detach();
      setPerspective(null);
      setError(null);
    };
  }, [token]);

  return (
    <>
      <canvas
        ref={canvasRef}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          zIndex: 5,
          cursor: "grab",
          touchAction: "none",
        }}
      />
      {perspective || error ? (
        <div style={overlayStyle}>
          {perspective ? (
            <>
              <div>Perspective at {perspective.anchor}</div>
              <div>
                {perspective.poles.join(" · ")}
                {perspective.fallback ? " (fallback dipole)" : ""}
              </div>
              <button
                onClick={() => backRef.current()}
                style={{
                  padding: "8px 16px",
                  background: "#6366F1",
                  border: "none",
                  borderRadius: 6,
                  color: "#F8FAFC",
                  fontFamily: "monospace",
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                Overview (Esc)
              </button>
            </>
          ) : null}
          {error ? <div style={{ color: "#F87171" }}>{error}</div> : null}
        </div>
      ) : null}
    </>
  );
}
