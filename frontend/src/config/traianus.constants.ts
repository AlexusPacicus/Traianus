/**
 * Traianus — Constantes congeladas (Zero Magic Numbers) — render layer.
 * OBSERVATION-LAYER (Ulpia). The 64B .purgativa layout and CLINICAL_REGEX
 * live in frontend/src/pkm/ (portable PKM), not here. The render consumes
 * semantic projections (projections_json) — ADR-022/024 keep traianus/ == 0.
 */

export const OKLCH = {
  L_MIN: 0.3,
  L_RANGE: 0.6,
  C_MIN: 0.05,
  C_RANGE: 0.25,
  H_MAX: 360.0,
  EPS: 1e-8,
} as const;

export const PHYSICS = {
  K_SPRING: 0.20,
  FRICTION: 0.12,
  DT: 0.15,
  TOL: 1e-5,
  H_PULSE_AMP: 0.15,
  PERSPECTIVE: 400,
  CAM_DIST: 5.0,
  GRID_SEG: 10,
  ROT_SENS: 0.007,
  DRAG_SCALE: 0.01,
  ALPHA_TARGET: 0.35,
  BPM_DEFAULT: 60,
  WIDTH: 800,
  HEIGHT: 600,
  HITBOX_RADIUS: 20,
  TIME_STEP: 0.05,
  PERTURB_RANGE: 1.5,
  IDEAL_DIST_SCALE: 2.5,
  IDEAL_DIST_OFFSET: 0.5,
  SOMATIC_BIAS: 0.2,
} as const;

export const TOPOLOGY = {
  THRESHOLD: 0.6,
  DIM_INIT: 2,
  GRID_RES: 40,
  SOFTENING: 0.1,
  ANCHOR: [1.0, 1.0] as const,
  EPSILON_EDGE: 0.8,
} as const;

Object.freeze(OKLCH);
Object.freeze(PHYSICS);
Object.freeze(TOPOLOGY);
