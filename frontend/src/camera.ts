/**
 * Pan and zoom of the WebGL map: a camera over the [-1, 1]^2 observable plane.
 *
 * The camera is the world point at the centre of the canvas plus a zoom factor. It only feeds the
 * view matrix, so navigation never writes to the engine (R2). One world unit is the same number of
 * pixels on both axes; zoom 1 centred on the origin shows the whole plane on the smaller side.
 */

export interface Camera {
  readonly cx: number;
  readonly cy: number;
  readonly zoom: number;
}

/** Share of half the smaller canvas side that one world unit spans at zoom 1. */
export const BASE_SCALE = 0.95;
export const MIN_ZOOM = 0.5;
export const MAX_ZOOM = 64;
/** Centre limit: the view can be centred anywhere on the observable plane, not beyond it. */
const CENTRE_LIMIT = 1;
/** Zoom per pixel of wheel travel: one 100 px notch is about 14%. */
const WHEEL_SENSITIVITY = 0.0015;
const PIXELS_PER_LINE = 16;
const PIXELS_PER_PAGE = 400;

export const HOME: Camera = { cx: 0, cy: 0, zoom: 1 };

const clamp = (value: number, low: number, high: number) => Math.min(high, Math.max(low, value));

const limited = (cx: number, cy: number, zoom: number): Camera => ({
  cx: clamp(cx, -CENTRE_LIMIT, CENTRE_LIMIT),
  cy: clamp(cy, -CENTRE_LIMIT, CENTRE_LIMIT),
  zoom: clamp(zoom, MIN_ZOOM, MAX_ZOOM),
});

/** Pixels per world unit at `zoom`, equal on both axes. */
function pixelsPerUnit(zoom: number, width: number, height: number): number {
  return (BASE_SCALE * zoom * Math.min(width, height)) / 2;
}

/** World point under the canvas pixel (px, py), measured from the canvas's top-left corner. */
export function screenToWorld(
  cam: Camera, px: number, py: number, width: number, height: number
): [number, number] {
  const u = pixelsPerUnit(cam.zoom, width, height);
  return [cam.cx + (px - width / 2) / u, cam.cy - (py - height / 2) / u];
}

/** Canvas pixel of the world point (x, y): the inverse of `screenToWorld`. */
export function worldToScreen(
  cam: Camera, x: number, y: number, width: number, height: number
): [number, number] {
  const u = pixelsPerUnit(cam.zoom, width, height);
  return [width / 2 + u * (x - cam.cx), height / 2 - u * (y - cam.cy)];
}

/** Zoom by `factor`, keeping the world point under pixel (px, py) where it is on screen. */
export function zoomAt(
  cam: Camera, factor: number, px: number, py: number, width: number, height: number
): Camera {
  const zoom = clamp(cam.zoom * factor, MIN_ZOOM, MAX_ZOOM);
  const [wx, wy] = screenToWorld(cam, px, py, width, height);
  const u = pixelsPerUnit(zoom, width, height);
  return limited(wx - (px - width / 2) / u, wy + (py - height / 2) / u, zoom);
}

/** Pan by a pointer drag of (dx, dy) pixels: the map follows the pointer. */
export function panBy(cam: Camera, dx: number, dy: number, width: number, height: number): Camera {
  const u = pixelsPerUnit(cam.zoom, width, height);
  return limited(cam.cx - dx / u, cam.cy + dy / u, cam.zoom);
}

/**
 * Index of the point (xs[i], ys[i]) nearest to the canvas pixel (px, py) within `radius` pixels,
 * the lower index on equal distance, or -1 when none is that close.
 */
export function pickNearest(
  cam: Camera,
  xs: ArrayLike<number>,
  ys: ArrayLike<number>,
  px: number,
  py: number,
  width: number,
  height: number,
  radius: number
): number {
  let best = -1;
  let bestSq = Infinity;
  for (let i = 0; i < xs.length; i++) {
    const [sx, sy] = worldToScreen(cam, xs[i], ys[i], width, height);
    const sq = (sx - px) ** 2 + (sy - py) ** 2;
    if (sq <= radius * radius && sq < bestSq) {
      best = i;
      bestSq = sq;
    }
  }
  return best;
}

/** Zoom factor of one wheel event; `deltaMode` is the DOM's (0 pixels, 1 lines, 2 pages). */
export function wheelFactor(deltaY: number, deltaMode: number): number {
  const pixels =
    deltaMode === 1 ? deltaY * PIXELS_PER_LINE : deltaMode === 2 ? deltaY * PIXELS_PER_PAGE : deltaY;
  return Math.exp(-pixels * WHEEL_SENSITIVITY);
}

/** Column-major view matrix: world -> (world - centre) * zoom. The projection carries the pixel scale. */
export function viewMatrix(cam: Camera): Float32Array {
  const z = cam.zoom;
  return new Float32Array([
    z, 0, 0, 0,
    0, z, 0, 0,
    0, 0, 1, 0,
    -z * cam.cx, -z * cam.cy, 0, 1,
  ]);
}

/**
 * Column-major projection for a canvas of `width` x `height` pixels: with `viewMatrix` it maps a
 * world point to the clip coordinates of its pixel, on the same scale for both axes.
 */
export function projectionMatrix(width: number, height: number): Float32Array {
  const w = Math.max(1, width);
  const h = Math.max(1, height);
  const s = BASE_SCALE * Math.min(w, h);
  return new Float32Array([
    s / w, 0, 0, 0,
    0, s / h, 0, 0,
    0, 0, -1, 0,
    0, 0, 0, 1,
  ]);
}
