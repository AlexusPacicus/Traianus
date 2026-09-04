import { useEffect, useRef } from "react";
import { fetchSpatial, type SpatialObservable } from "../api";
import { packRestingBuffer, buildTransitionBuffer } from "../binary";
import { UlpiaRenderer } from "../ulpia_renderer";

interface UlpiaWebGLProps {
  token: string;
}

/**
 * WebGL2 overlay for the Ulpia spatial canvas (Fase 3/4).
 *
 * Fetches per-node spatial observables from GET /spatial, packs them into the
 * 64-byte zero-copy contract, uploads to GPU memory and animates a subtle
 * breathing transition with escape vibration.
 */
export default function UlpiaWebGL({ token }: UlpiaWebGLProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    let renderer: UlpiaRenderer | null = null;
    let rafId = 0;
    let cancelled = false;

    (async () => {
      try {
        const nodes = await fetchSpatial(token);
        if (cancelled || nodes.length === 0) return;

        renderer = new UlpiaRenderer(canvas);
        // Orthographic-ish projection covering the [-1,1]^3 coordinate range.
        const projection = new Float32Array([
          1.2, 0, 0, 0,
          0, 1.2, 0, 0,
          0, 0, -1, 0,
          0, 0, 0, 1,
        ]);
        const view = new Float32Array([
          1, 0, 0, 0,
          0, 1, 0, 0,
          0, 0, 1, 0,
          0, 0, 0, 1,
        ]);
        renderer.updateCamera(projection, view);

        const resting = packRestingBuffer(nodes);
        renderer.uploadRestingBuffer(resting);

        // Breathing transition: arc through an orthogonal copy of the cloud.
        const moved: SpatialObservable[] = nodes.map((n, i) => {
          const phase = ((i % 7) - 3) * 0.05;
          return {
            ...n,
            x: n.x + phase,
            y: n.y - 0.03 * ((i % 3) + 1),
            z: n.z * 1.0,
          };
        });
        const arcSag = (i: number): [number, number, number] => {
          const n = nodes[i];
          return [n.x, n.y, n.z + 0.06 * (1 + (i % 3))];
        };
        const transition = buildTransitionBuffer(nodes, moved, arcSag);
        renderer.uploadTransitionBuffer(transition);
        const total = nodes.length;

        // Escape vibration proxy: mean h (escape distance) across the manifold.
        const meanEscape = nodes.reduce((acc, n) => acc + n.h, 0) / nodes.length;
        const vibration =
          meanEscape > 0.35 ? Math.min(1.0, (meanEscape - 0.35) * 3) : 0;

        const t0 = performance.now();
        const loop = () => {
          if (cancelled) return;
          const elapsed = (performance.now() - t0) / 1000;
          // Elastic ease-in-out: gentle 6s loop between idle and transit.
          const sweep = (Math.sin(elapsed * 0.5) + 1) / 2; // [0,1] oscillation
          const t = sweep * sweep * (3 - 2 * sweep); // smoothstep
          renderer?.renderFrame(total, t, t > 0.02 && t < 0.98 ? vibration : 0);
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
        pointerEvents: "none",
      }}
    />
  );
}