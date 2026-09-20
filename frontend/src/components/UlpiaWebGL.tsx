import { useEffect, useRef } from "react";
import { fetchSpatial } from "../api";
import { packRestingBuffer } from "../binary";
import { BASE_SCALE, HOME, panBy, viewMatrix, wheelFactor, zoomAt, type Camera } from "../camera";
import { UlpiaRenderer } from "../ulpia_renderer";

interface UlpiaWebGLProps {
  token: string;
}

/** Orthographic-ish projection covering the [-1,1]^3 coordinate range. */
const PROJECTION = new Float32Array([
  BASE_SCALE, 0, 0, 0,
  0, BASE_SCALE, 0, 0,
  0, 0, -1, 0,
  0, 0, 0, 1,
]);

/** Wheel zooms about the cursor, dragging pans, double-click goes home. */
function attachNavigation(
  canvas: HTMLCanvasElement,
  get: () => Camera,
  set: (camera: Camera) => void
): () => void {
  let drag: { x: number; y: number } | null = null;

  const onWheel = (e: WheelEvent) => {
    e.preventDefault();
    const box = canvas.getBoundingClientRect();
    const factor = wheelFactor(e.deltaY, e.deltaMode);
    set(zoomAt(get(), factor, e.clientX - box.left, e.clientY - box.top, box.width, box.height));
  };
  const onDown = (e: PointerEvent) => {
    if (e.button !== 0) return;
    drag = { x: e.clientX, y: e.clientY };
    canvas.setPointerCapture(e.pointerId);
    canvas.style.cursor = "grabbing";
  };
  const onMove = (e: PointerEvent) => {
    if (!drag) return;
    const box = canvas.getBoundingClientRect();
    set(panBy(get(), e.clientX - drag.x, e.clientY - drag.y, box.width, box.height));
    drag = { x: e.clientX, y: e.clientY };
  };
  const onUp = () => {
    drag = null;
    canvas.style.cursor = "grab";
  };
  const onHome = () => set(HOME);

  canvas.addEventListener("wheel", onWheel, { passive: false });
  canvas.addEventListener("pointerdown", onDown);
  canvas.addEventListener("pointermove", onMove);
  canvas.addEventListener("pointerup", onUp);
  canvas.addEventListener("pointercancel", onUp);
  canvas.addEventListener("dblclick", onHome);
  return () => {
    canvas.removeEventListener("wheel", onWheel);
    canvas.removeEventListener("pointerdown", onDown);
    canvas.removeEventListener("pointermove", onMove);
    canvas.removeEventListener("pointerup", onUp);
    canvas.removeEventListener("pointercancel", onUp);
    canvas.removeEventListener("dblclick", onHome);
  };
}

/**
 * WebGL2 overlay for the Ulpia spatial canvas.
 *
 * Fetches per-node spatial observables from GET /spatial, packs them into the 64-byte zero-copy
 * contract and draws them at rest: a node never moves on screen except by the camera. Zoom and
 * pan only change the view matrix, so navigation writes nothing to the engine (R2).
 */
export default function UlpiaWebGL({ token }: UlpiaWebGLProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    let renderer: UlpiaRenderer | null = null;
    let rafId = 0;
    let cancelled = false;
    let detach = () => {};

    (async () => {
      try {
        const nodes = await fetchSpatial(token);
        if (cancelled || nodes.length === 0) return;

        renderer = new UlpiaRenderer(canvas);
        renderer.uploadRestingBuffer(packRestingBuffer(nodes));

        let camera: Camera = HOME;
        const setCamera = (next: Camera) => {
          camera = next;
          renderer?.updateCamera(PROJECTION, viewMatrix(camera));
        };
        setCamera(HOME);
        detach = attachNavigation(canvas, () => camera, setCamera);

        const total = nodes.length;
        const loop = () => {
          if (cancelled) return;
          renderer?.renderFrame(total);
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
    };
  }, [token]);

  return (
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
  );
}
