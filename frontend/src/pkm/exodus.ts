/**
 * exodus — Export/Import .purgativa (portable PKM stream, 64B-aligned).
 * Optional data-port utility; independent of the render loop.
 */
import { BINARY, unpackRecord, type TraianusNode } from "./bin";
import { TraianusBinaryStore } from "./storage";

export function validatePurgativaBuffer(buffer: ArrayBuffer): void {
  if (buffer.byteLength % BINARY.RECORD_SIZE !== 0) {
    throw new Error(`purgativa.bin inválido: ${buffer.byteLength}B no es múltiplo de ${BINARY.RECORD_SIZE}`);
  }
}

export async function exportPurgativaBin(store?: TraianusBinaryStore): Promise<Blob> {
  const s = store ?? new TraianusBinaryStore();
  let shouldClose = false;
  if (!(s as unknown as { db: IDBDatabase | null })["db"]) {
    await s.connect();
    shouldClose = true;
  }
  const contiguous = await s.getAllNodesContiguous();
  if (shouldClose) s.close();
  return new Blob([contiguous], { type: "application/octet-stream" });
}

export function downloadBlob(blob: Blob, filename = "purgativa.bin"): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export async function exportAndDownload(store?: TraianusBinaryStore): Promise<{ blob: Blob; count: number }> {
  const blob = await exportPurgativaBin(store);
  const count = blob.size / BINARY.RECORD_SIZE;
  downloadBlob(blob, "purgativa.bin");
  return { blob, count };
}

export async function importPurgativaBin(
  file: File,
  store?: TraianusBinaryStore
): Promise<{ count: number; errors: string[] }> {
  const buffer = await file.arrayBuffer();
  return importPurgativaBuffer(buffer, store);
}

export async function importPurgativaBuffer(
  buffer: ArrayBuffer,
  store?: TraianusBinaryStore
): Promise<{ count: number; errors: string[] }> {
  validatePurgativaBuffer(buffer);
  const s = store ?? new TraianusBinaryStore();
  let shouldClose = false;
  if (!(s as unknown as { db: IDBDatabase | null })["db"]) {
    await s.connect();
    shouldClose = true;
  }
  const total = buffer.byteLength / BINARY.RECORD_SIZE;
  const map = new Map<string, ArrayBuffer>();
  const errors: string[] = [];
  for (let i = 0; i < total; i++) {
    const slice = buffer.slice(i * BINARY.RECORD_SIZE, (i + 1) * BINARY.RECORD_SIZE);
    try {
      const node = unpackRecord(slice);
      if (!node.id) {
        errors.push(`registro ${i}: id vacío`);
        continue;
      }
      map.set(node.id, slice);
    } catch (e) {
      errors.push(`registro ${i}: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
  if (map.size > 0) await s.bulkPutNodes(map);
  if (shouldClose) s.close();
  return { count: map.size, errors };
}

export type { TraianusNode };
