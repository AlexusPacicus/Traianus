/**
 * PKM binary layout — portable .purgativa record format (64B).
 *
 * Origin: NotebookLM experimentation notebook. NOT a Traianus substrate
 * contract. The render loop and useUlpiaStore must derive geometry from
 * semantic projections (projections_json), not from this struct.
 *
 * Record: <ffffff32s8x = 6 x float32 + 32-byte id + 8-byte pad.
 */
import { sanitizeSomaticFlow } from "./sanitize";

export const BINARY = {
  RECORD_SIZE: 64,
  FLOATS: 6,
  ID_BYTES: 32,
  PAD: 8,
  FLOAT_BYTES: 4,
  get ID_OFFSET() {
    return this.FLOATS * this.FLOAT_BYTES;
  },
  get ID_END() {
    return this.ID_OFFSET + this.ID_BYTES;
  },
} as const;

export interface TraianusNode {
  x: number;
  y: number;
  z: number;
  l: number;
  c: number;
  h: number;
  id: string;
}

export function safeUtf8Truncate(text: string, maxBytes: number = BINARY.ID_BYTES): Uint8Array {
  const raw = new TextEncoder().encode(text);
  if (raw.length <= maxBytes) {
    const out = new Uint8Array(maxBytes);
    out.set(raw);
    return out;
  }
  let len = maxBytes;
  while (len > 0 && (raw[len - 1] & 0xc0) === 0x80) len--;
  if (len > 0 && (raw[len - 1] & 0x80) !== 0) len--;
  const out = new Uint8Array(maxBytes);
  out.set(raw.subarray(0, len));
  return out;
}

export function packRecord(node: TraianusNode): ArrayBuffer {
  const { sanitized: safeId } = sanitizeSomaticFlow(node.id);
  const idBytes = safeUtf8Truncate(safeId, BINARY.ID_BYTES);
  const buffer = new ArrayBuffer(BINARY.RECORD_SIZE);
  const view = new DataView(buffer);
  view.setFloat32(0, node.x, true);
  view.setFloat32(4, node.y, true);
  view.setFloat32(8, node.z, true);
  view.setFloat32(12, node.l, true);
  view.setFloat32(16, node.c, true);
  view.setFloat32(20, node.h, true);
  new Uint8Array(buffer, BINARY.ID_OFFSET, BINARY.ID_BYTES).set(idBytes);
  return buffer;
}

export function unpackRecord(buffer: ArrayBuffer): TraianusNode {
  if (buffer.byteLength !== BINARY.RECORD_SIZE) {
    throw new Error(`Buffer inválido: ${buffer.byteLength}B, se requieren ${BINARY.RECORD_SIZE}B`);
  }
  const view = new DataView(buffer);
  const x = view.getFloat32(0, true);
  const y = view.getFloat32(4, true);
  const z = view.getFloat32(8, true);
  const l = view.getFloat32(12, true);
  const c = view.getFloat32(16, true);
  const h = view.getFloat32(20, true);
  const idBytes = new Uint8Array(buffer, BINARY.ID_OFFSET, BINARY.ID_BYTES);
  let end = idBytes.indexOf(0);
  if (end === -1) end = BINARY.ID_BYTES;
  const id = new TextDecoder("utf-8").decode(idBytes.subarray(0, end));
  return { x, y, z, l, c, h, id };
}

export function unpackAt(contiguous: ArrayBuffer, index: number): TraianusNode {
  const offset = index * BINARY.RECORD_SIZE;
  if (offset + BINARY.RECORD_SIZE > contiguous.byteLength) {
    throw new Error(`Índice fuera de rango: ${index}`);
  }
  const slice = contiguous.slice(offset, offset + BINARY.RECORD_SIZE);
  return unpackRecord(slice);
}
