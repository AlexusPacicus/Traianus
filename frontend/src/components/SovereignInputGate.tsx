/**
 * SovereignInputGate — Pasarela con filtro clínico y cuarentena Doble Llave
 * Consume CLINICAL_REGEX centralizado; nunca consolida unilateralmente
 */
import React, { useCallback, useState } from "react";
import { useUlpiaStore } from "../store/useUlpiaStore";
import { fetchNodes } from "../api";
import { projectTo5d } from "../projection";
import { sanitizeSomaticFlow } from "../pkm/sanitize";

function sanitizeWithFlag(text: string): { sanitized: string; flagged: boolean } {
  return sanitizeSomaticFlow(text);
}

function deriveCoordsFromProjections(allNodes: { id: string; projections_json: Record<string, number> }[], targetId: string) {
  const matrix = allNodes.map((n) => Object.keys(n.projections_json).sort().map((k) => n.projections_json[k]));
  if (matrix.length === 0) throw new Error("No projections available");
  if (matrix.length === 1) {
    const v = matrix[0];
    return { x: v[0] ?? 0, y: v[1] ?? 0, z: v[2] ?? 0, l: 0.5, c: 0.5, h: 180 };
  }
  const projected = projectTo5d(matrix);
  const idx = allNodes.findIndex((n) => n.id === targetId);
  if (idx === -1) throw new Error(`Node ${targetId} not found in projections`);
  const [x, y, r, g, b] = projected[idx];
  return { x, y, z: 0, l: r, c: g, h: b * 360 };
}

interface SovereignInputGateProps {
  token?: string;
  onIngested?: (id: string) => void;
}

type GateState = "idle" | "quarantine" | "consolidating" | "consolidated" | "error";
type LifecycleHint = "incubating" | "pending_approval" | "consolidated" | "quarantine_local";

export const SovereignInputGate: React.FC<SovereignInputGateProps> = ({ token, onIngested }) => {
  const [text, setText] = useState("");
  const [gateState, setGateState] = useState<GateState>("idle");
  const [hint, setHint] = useState<LifecycleHint | null>(null);
  const [lastId, setLastId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sanitizedPreview, setSanitizedPreview] = useState<string | null>(null);

  const ingestThought = useUlpiaStore((s) => s.ingestThought);
  const consolidateThought = useUlpiaStore((s) => s.consolidateThought);
  const quarantineQueue = useUlpiaStore((s) => s.quarantineQueue);

  const handleTextChange = useCallback((value: string) => {
    setText(value);
    if (!value.trim()) {
      setSanitizedPreview(null);
      return;
    }
    const { sanitized, flagged } = sanitizeWithFlag(value);
    setSanitizedPreview(flagged ? sanitized : null);
  }, []);

  const handleIngest = useCallback(async () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    if (trimmed.includes("\x00")) {
      setError("Entrada rechazada: contiene null bytes");
      setGateState("error");
      return;
    }
    try {
      const enc = new TextEncoder().encode(trimmed);
      new TextDecoder("utf-8", { fatal: true }).decode(enc);
    } catch {
      setError("Entrada rechazada: UTF-8 inválido");
      setGateState("error");
      return;
    }

    const { sanitized, flagged } = sanitizeWithFlag(trimmed);

    if (!token) {
      const id = `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const coords = { x: 0, y: 0, z: 0, l: 0.5, c: 0.5, h: 180 };
      ingestThought(id, sanitized, coords, flagged ? { sanitized_by_guardian: true, offline: true } : { offline: true });
      setLastId(id);
      setGateState("quarantine");
      setHint("quarantine_local");
      setError(null);
      return;
    }

    setError(null);
    setGateState("quarantine");
    try {
      const res = await fetch("/ingesta", {
        method: "POST",
        headers: {
          "Content-Type": "text/plain",
          "X-Traianus-Token": token,
          "X-Idempotency-Key": crypto.randomUUID(),
        },
        body: sanitized,
      });
      if (!res.ok) {
        const t = await res.text().catch(() => "");
        throw new Error(`Ingesta ${res.status} ${t}`.trim());
      }
      const data = await res.json().catch(() => ({}));
      const nodeId: string | undefined = data.node_id ?? data.id ?? data.ingestion_id;
      if (!nodeId) throw new Error("Ingesta sin node_id");

      const allNodes = await fetchNodes();
      const found = allNodes.find((n) => n.id === nodeId);
      if (!found) throw new Error(`Nodo ${nodeId} no encontrado tras ingesta`);
      if (found.lifecycle_state === "pending_approval") setHint("pending_approval");
      else if (found.lifecycle_state === "incubating") setHint("incubating");
      else if (found.lifecycle_state === "consolidated") setHint("consolidated");
      else setHint("quarantine_local");

      let coords: { x: number; y: number; z: number; l: number; c: number; h: number };
      try {
        coords = deriveCoordsFromProjections(
          allNodes.map((n) => ({ id: n.id, projections_json: n.projections_json })),
          nodeId
        );
      } catch (e) {
        throw new Error(`Proyección fallida: ${e instanceof Error ? e.message : String(e)}`);
      }

      ingestThought(nodeId, sanitized, coords, flagged ? { sanitized_by_guardian: true } : {});
      setLastId(nodeId);
      onIngested?.(nodeId);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      setGateState("error");
      setHint(null);
    }
  }, [text, token, ingestThought, onIngested]);

  const handleConsolidate = useCallback(async () => {
    if (!lastId) return;
    setGateState("consolidating");
    setError(null);
    try {
      await consolidateThought(lastId);
      if (token) {
        const res = await fetch(`/nodos/${encodeURIComponent(lastId)}/consolidar`, {
          method: "POST",
          headers: { "X-Traianus-Token": token, "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
        if (!res.ok && res.status !== 404) {
          const t = await res.text().catch(() => "");
          throw new Error(`Consolidar ${res.status} ${t}`.trim());
        }
      }
      setGateState("consolidated");
      setHint("consolidated");
      setText("");
      setSanitizedPreview(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setGateState("error");
    }
  }, [lastId, consolidateThought, token]);

  const handleReject = useCallback(() => {
    if (!lastId) return;
    const { rejectThought } = useUlpiaStore.getState();
    rejectThought(lastId);
    setLastId(null);
    setGateState("idle");
    setHint(null);
    setError(null);
  }, [lastId]);

  const quarantineSize = quarantineQueue.size;
  const canConsolidate = gateState === "quarantine" && !!lastId;

  return (
    <div className="w-full max-w-xl bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-slate-100 text-sm font-bold tracking-wide">Sovereign Input Gate</h3>
        <span className="text-[10px] font-mono px-2 py-1 rounded bg-slate-800 text-slate-400">
          cuarentena: {quarantineSize} · {gateState}
        </span>
      </div>

      <textarea
        value={text}
        onChange={(e) => handleTextChange(e.target.value)}
        placeholder="Pensamiento libre (local-first)…"
        rows={3}
        className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-slate-100 text-sm placeholder:text-slate-500 focus:outline-none focus:border-slate-600 resize-none"
      />

      {sanitizedPreview && (
        <div className="mt-2 p-2 bg-amber-950/40 border border-amber-800/50 rounded text-amber-200 text-xs">
          <div className="font-semibold mb-1">⚠️ Agnosticismo clínico activo — purificado:</div>
          <div className="font-mono break-words">{sanitizedPreview}</div>
        </div>
      )}

      {hint && (
        <div className="mt-2 text-xs font-mono">
          {hint === "quarantine_local" && <span className="text-amber-400">🔒 Doble Llave: en cuarentena local — firma soberana requerida para consolidar (no toca IndexedDB aún).</span>}
          {hint === "incubating" && <span className="text-sky-400">incubating — falta σ²≥θ_dyn (Topological Key).</span>}
          {hint === "pending_approval" && <span className="text-emerald-400">pending_approval — falta EthicalKey (HITL).</span>}
          {hint === "consolidated" && <span className="text-emerald-400">consolidated ✓</span>}
        </div>
      )}

      {error && <div className="mt-2 text-xs text-red-400 bg-red-950/30 border border-red-900 rounded p-2 break-words">{error}</div>}

      <div className="mt-3 flex gap-2">
        <button
          onClick={handleIngest}
          disabled={!text.trim()}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm rounded-lg font-medium"
        >
          Ingerir → Cuarentena
        </button>
        <button
          onClick={handleConsolidate}
          disabled={!canConsolidate}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm rounded-lg font-medium"
        >
          Firmar & Consolidar
        </button>
        {canConsolidate && (
          <button onClick={handleReject} className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm rounded-lg">
            Descartar
          </button>
        )}
      </div>

      <p className="mt-3 text-[10px] text-slate-500 leading-relaxed">
        Aduana clínica local-first. La consolidación requiere ambas llaves (`σ²≥θ_dyn ∧ EthicalKey`) — sin consolidación unilateral.
      </p>
    </div>
  );
};

export default SovereignInputGate;
