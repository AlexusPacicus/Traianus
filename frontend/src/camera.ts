/**
 * Pan and zoom of the WebGL map: a camera over the [-1, 1]^2 observable plane.
 *
 * The camera is the world point at the centre of the canvas plus a zoom factor. It only feeds the
 * view matrix, so navigation never writes to the engine (R2). Zoom 1 centred on the origin is
 * the overview as it was drawn before the camera existed.
 */

export interface Camera {
  readonly cx: number;
  readonly cy: number;
  readonly zoom: number;
}

/** Projection scale of the overview: world x and y are multiplied by it into clip space. */
export const BASE_SCALE = 1.2;
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

/** World point under the canvas pixel (px, py), measured from the canvas's top-left corner. */
export function screenToWorld(
  cam: Camera, px: number, py: number, width: number, height: number
): [number, number] {
  const k = BASE_SCALE * cam.zoom;
  return [cam.cx + (2 * px / width - 1) / k, cam.cy + (1 - 2 * py / height) / k];
}

/** Zoom by `factor`, keeping the world point under pixel (px, py) where it is on screen. */
export function zoomAt(
  cam: Camera, factor: number, px: number, py: number, width: number, height: number
): Camera {
  const zoom = clamp(cam.zoom * factor, MIN_ZOOM, MAX_ZOOM);
  const [wx, wy] = screenToWorld(cam, px, py, width, height);
  const k = BASE_SCALE * zoom;
  return limited(wx - (2 * px / width - 1) / k, wy - (1 - 2 * py / height) / k, zoom);
}

/** Pan by a pointer drag of (dx, dy) pixels: the map follows the pointer. */
export function panBy(cam: Camera, dx: number, dy: number, width: number, height: number): Camera {
  const k = BASE_SCALE * cam.zoom;
  return limited(cam.cx - 2 * dx / (width * k), cam.cy + 2 * dy / (height * k), cam.zoom);
}

/** Zoom factor of one wheel event; `deltaMode` is the DOM's (0 pixels, 1 lines, 2 pages). */
export function wheelFactor(deltaY: number, deltaMode: number): number {
  const pixels =
    deltaMode === 1 ? deltaY * PIXELS_PER_LINE : deltaMode === 2 ? deltaY * PIXELS_PER_PAGE : deltaY;
  return Math.exp(-pixels * WHEEL_SENSITIVITY);
}

/** Column-major view matrix: world -> (world - centre) * zoom. BASE_SCALE lives in the projection. */
export function viewMatrix(cam: Camera): Float32Array {
  const z = cam.zoom;
  return new Float32Array([
    z, 0, 0, 0,
    0, z, 0, 0,
    0, 0, 1, 0,
    -z * cam.cx, -z * cam.cy, 0, 1,
  ]);
}
