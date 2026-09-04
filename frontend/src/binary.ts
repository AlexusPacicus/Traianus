/**
 * Client-side packer for the Ulpia 64-byte binary contract.
 *
 * Mirrors traianus/geometry/zero_copy.py (Fase 1):
 *   offset  0-11  x, y, z        (3 x float32)
 *   offset 12-23  L, C, H        (3 x float32, channels normalized [0,1])
 *   offset 24-55  note_id        (32-char lowercase hex)
 *   offset 56-63  padding        (8-byte alignment)
 *
 * The Traianus node ids (NODE_1, VEC_...) are not 32-hex UUIDs, so the binary
 * note_id is a deterministic 32-hex digest of the node id (keeping the GPU
 * buffer and the Python exporter contract aligned: exactly 32 lowercase hex).
 */

import type { SpatialObservable } from "./api";

/** Resting block size, matches ULPIABLOCK_BYTES in ulpia_renderer.ts. */
export const BLOCK_BYTES = 64;

/** Deterministic 32-char lowercase hex digest of a string (FNV-family mixer). */
export function noteIdFromLabel(label: string): string {
  let hash = 0x811c9dc5 ^ 0x9e3779b9;
  let hash2 = 0x01000193 ^ 0x85ebca6b;
  for (let i = 0; i < label.length; i++) {
    hash ^= label.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
    hash2 ^= label.charCodeAt(label.length - 1 - i);
    hash2 = Math.imul(hash2, 0x85ebca77);
  }
  const a = hash >>> 0;
  const b = hash2 >>> 0;
  const c = (hash ^ hash2) >>> 0;
  const d = (hash + hash2) >>> 0;
  return (
    a.toString(16).padStart(8, "0") +
    b.toString(16).padStart(8, "0") +
    c.toString(16).padStart(8, "0") +
    d.toString(16).padStart(8, "0")
  );
}

/**
 * Pack one observable node into a 64-byte ArrayBuffer (little-endian float32).
 * Throws if any channel is outside [0,1] (mirrors the Python exporter).
 */
export function packNode(node: SpatialObservable): ArrayBuffer {
  const buf = new ArrayBuffer(BLOCK_BYTES);
  const view = new DataView(buf);
  const writeF32 = (offset: number, value: number) => {
    if (!Number.isFinite(value)) {
      throw new Error(`Channel is not finite for node ${node.id}`);
    }
    view.setFloat32(offset, value, true);
  };
  writeF32(0, node.x);
  writeF32(4, node.y);
  writeF32(8, node.z);
  for (const [offset, name, value] of [
    [12, "l", node.l],
    [16, "c", node.c],
    [20, "h", node.h],
  ] as const) {
    if (value < 0 || value > 1) {
      throw new Error(`${name} must be in [0,1] for node ${node.id}, got ${value}`);
    }
    writeF32(offset, value);
  }
  const digest = noteIdFromLabel(node.id);
  new TextEncoder().encodeInto(digest, new Uint8Array(buf, 24, 32));
  return buf;
}

/** Pack many nodes into one contiguous zero-copy buffer (n * 64 bytes). */
export function packRestingBuffer(nodes: SpatialObservable[]): ArrayBuffer {
  const total = nodes.length * BLOCK_BYTES;
  const buf = new ArrayBuffer(total);
  for (let i = 0; i < nodes.length; i++) {
    const block = new Uint8Array(packNode(nodes[i]));
    new Uint8Array(buf).set(block, i * BLOCK_BYTES);
  }
  return buf;
}

/**
 * Build a transition buffer for the Parabolic Corrector: 9 contiguous float32
 * per node = (start_pos, end_pos, mid_deviation). Only meaningful while a
 * parabolic animation is active.
 *
 * Mid-point D_mid = arc_mid - (start + end) / 2 where arc_mid is an optional
 * control point; when no arc is given the transition is a straight path
 * (zero deviation).
 */
export function buildTransitionBuffer(
  from: SpatialObservable[],
  to: SpatialObservable[],
  arcMid: (i: number) => [number, number, number] | null = () => null
): ArrayBuffer {
  if (from.length !== to.length) {
    throw new Error(`from/to length mismatch: ${from.length} vs ${to.length}`);
  }
  const buf = new ArrayBuffer(from.length * 36);
  const view = new DataView(buf);
  let offset = 0;
  for (let i = 0; i < from.length; i++) {
    const start = [from[i].x, from[i].y, from[i].z];
    const end = [to[i].x, to[i].y, to[i].z];
    const mid = [
      (from[i].x + to[i].x) / 2,
      (from[i].y + to[i].y) / 2,
      (from[i].z + to[i].z) / 2,
    ];
    const arc = arcMid(i) ?? [mid[0], mid[1], mid[2]];
    const dev = [arc[0] - mid[0], arc[1] - mid[1], arc[2] - mid[2]];
    for (const p of [start, end, dev]) {
      for (const v of p) {
        view.setFloat32(offset, v, true);
        offset += 4;
      }
    }
  }
  return buf;
}