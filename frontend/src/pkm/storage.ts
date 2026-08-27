/**
 * PKM IndexedDB store — contiguous 64B .purgativa persistence, portable and
 * independent of the render loop.
 */
import { BINARY, packRecord, unpackRecord, type TraianusNode } from "./bin";

export class TraianusBinaryStore {
  private dbName: string;
  private storeName: string;
  private dbVersion: number;
  private db: IDBDatabase | null = null;

  constructor(dbName = "TraianusLocalStore", storeName = "nodes", dbVersion = 1) {
    this.dbName = dbName;
    this.storeName = storeName;
    this.dbVersion = dbVersion;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          db.createObjectStore(this.storeName);
        }
      };
      request.onblocked = () => reject(new Error("IndexedDB bloqueada por pestaña abierta"));
      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };
      request.onerror = () => reject(new Error(`IndexedDB open failed: ${request.error?.message}`));
    });
  }

  private getDB(): IDBDatabase {
    if (!this.db) throw new Error("DB no inicializada. Llama a connect() primero.");
    return this.db;
  }

  close(): void {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }

  unpack(buffer: ArrayBuffer): TraianusNode {
    return unpackRecord(buffer);
  }

  pack(node: TraianusNode): ArrayBuffer {
    return packRecord(node);
  }

  putNodeBuffer(id: string, buffer: ArrayBuffer): Promise<void> {
    if (buffer.byteLength !== BINARY.RECORD_SIZE) {
      return Promise.reject(new Error(`putNodeBuffer: buffer debe ser ${BINARY.RECORD_SIZE}B`));
    }
    return new Promise((resolve, reject) => {
      const tx = this.getDB().transaction([this.storeName], "readwrite");
      const store = tx.objectStore(this.storeName);
      const req = store.put(buffer, id);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  }

  getNodeBuffer(id: string): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      const tx = this.getDB().transaction([this.storeName], "readonly");
      const store = tx.objectStore(this.storeName);
      const req = store.get(id);
      req.onsuccess = () => {
        if (!req.result) reject(new Error(`Nodo '${id}' no encontrado`));
        else resolve(req.result as ArrayBuffer);
      };
      req.onerror = () => reject(req.error);
    });
  }

  bulkPutNodes(nodes: Map<string, ArrayBuffer>): Promise<void> {
    for (const [, buf] of nodes) {
      if (buf.byteLength !== BINARY.RECORD_SIZE) {
        return Promise.reject(new Error(`bulkPutNodes: cada buffer debe ser ${BINARY.RECORD_SIZE}B`));
      }
    }
    return new Promise((resolve, reject) => {
      const tx = this.getDB().transaction([this.storeName], "readwrite");
      const store = tx.objectStore(this.storeName);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      for (const [id, buffer] of nodes.entries()) store.put(buffer, id);
    });
  }

  getAllNodesContiguous(): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      const tx = this.getDB().transaction([this.storeName], "readonly");
      const store = tx.objectStore(this.storeName);
      const req = store.getAll();
      req.onsuccess = () => {
        const buffers = req.result as ArrayBuffer[];
        const total = buffers.length;
        const contiguous = new ArrayBuffer(total * BINARY.RECORD_SIZE);
        const view = new Uint8Array(contiguous);
        for (let i = 0; i < total; i++) view.set(new Uint8Array(buffers[i]), i * BINARY.RECORD_SIZE);
        resolve(contiguous);
      };
      req.onerror = () => reject(req.error);
    });
  }

  clear(): Promise<void> {
    return new Promise((resolve, reject) => {
      const tx = this.getDB().transaction([this.storeName], "readwrite");
      const req = tx.objectStore(this.storeName).clear();
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  }

  count(): Promise<number> {
    return new Promise((resolve, reject) => {
      const tx = this.getDB().transaction([this.storeName], "readonly");
      const req = tx.objectStore(this.storeName).count();
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
}
