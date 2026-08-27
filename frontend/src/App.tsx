import { useEffect, useState } from "react";
import UlpiaCanvas from "./components/UlpiaCanvas";
import { TraianusUlpia3DCanvas } from "./components/TraianusUlpia3DCanvas";
import SovereignInputGate from "./components/SovereignInputGate";
import { useSomaticPulse, modulatedFriction } from "./hooks/useSomaticPulse";
import { useUlpiaStore } from "./store/useUlpiaStore";
import { exportAndDownload, importPurgativaBin } from "./pkm/exodus";
import { PHYSICS } from "./config/traianus.constants";

export default function App() {
  const [token, setToken] = useState("");
  const [connected, setConnected] = useState(false);
  const [view, setView] = useState<"3d" | "5d">("3d");
  const { bpm, confidence, active, error: pulseError, start, stop, videoRef } = useSomaticPulse();
  const heartRateBpm = bpm ?? PHYSICS.BPM_DEFAULT;
  const friction = modulatedFriction(PHYSICS.FRICTION, bpm, confidence);
  const initializeStore = useUlpiaStore((s) => s.initializeStore);
  const setHeartRate = useUlpiaStore((s) => s.setHeartRate);

  useEffect(() => {
    initializeStore();
  }, [initializeStore]);

  useEffect(() => {
    if (bpm) setHeartRate(bpm);
  }, [bpm, setHeartRate]);

  const handleExport = async () => {
    try {
      const { count } = await exportAndDownload();
      console.log(`purgativa.bin exportado: ${count} registros 64B`);
    } catch (e) {
      console.error(e);
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const { count, errors } = await importPurgativaBin(file);
      console.log(`importados ${count} registros`, errors);
      await initializeStore();
    } catch (err) {
      console.error(err);
    } finally {
      e.target.value = "";
    }
  };

  if (!connected) {
    return (
      <div
        style={{
          width: "100vw",
          height: "100vh",
          background: "#0B0F19",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "monospace",
          color: "#F8FAFC",
        }}
      >
        <h1 style={{ fontSize: 24, marginBottom: 8, color: "#38BDF8" }}>Ulpia</h1>
        <p style={{ fontSize: 12, color: "#64748B", marginBottom: 24 }}>Traianus 3D Membrane · Local-First</p>
        <input
          type="password"
          placeholder="Operator token (required for protected endpoints)"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          style={{
            padding: "8px 12px",
            background: "#1E293B",
            border: "1px solid #334155",
            borderRadius: 6,
            color: "#F8FAFC",
            fontFamily: "monospace",
            fontSize: 13,
            width: 320,
            marginBottom: 16,
          }}
        />
        <button
          onClick={() => setConnected(true)}
          style={{
            padding: "8px 24px",
            background: "#6366F1",
            border: "none",
            borderRadius: 6,
            color: "#F8FAFC",
            fontFamily: "monospace",
            fontSize: 13,
            cursor: "pointer",
          }}
        >
          Connect
        </button>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0B0F19", color: "#F8FAFC", fontFamily: "monospace" }}>
      <header className="sticky top-0 z-20 bg-slate-950/80 backdrop-blur border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="text-sky-400 font-bold">Ulpia 3D Membrane</span>
            <span className="text-[10px] px-2 py-1 rounded bg-slate-800 text-slate-400">research/ulpia-3d-membrane</span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setView(view === "3d" ? "5d" : "3d")} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700">
              Vista: {view === "3d" ? "3D Verlet" : "5D Chromatic"}
            </button>
            <button onClick={handleExport} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700">
              Export purgativa.bin
            </button>
            <label className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-xs rounded cursor-pointer">
              Import purgativa.bin
              <input type="file" accept=".bin" onChange={handleImport} className="hidden" />
            </label>
            <button
              onClick={() => {
                setToken("");
                setConnected(false);
              }}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700"
            >
              Disconnect
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <SovereignInputGate token={token || undefined} />
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-bold">Pulso Somático (rPPG)</h4>
              <span className={`text-xs px-2 py-1 rounded ${active ? "bg-emerald-900 text-emerald-200" : "bg-slate-800 text-slate-400"}`}>
                {active ? "activo" : "inactivo"}
              </span>
            </div>
            <div className="text-xs space-y-1 font-mono">
              <div className="flex justify-between"><span className="text-slate-400">BPM:</span><span className="text-sky-400">{heartRateBpm} {bpm ? "" : "(default)"}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Confianza:</span><span>{(confidence * 100).toFixed(0)}%</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Fricción λ:</span><span>{friction.toFixed(3)}</span></div>
              {pulseError && <div className="text-red-400 break-words">{pulseError}</div>}
            </div>
            <div className="mt-3 flex gap-2">
              {!active ? (
                <button onClick={start} className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-xs rounded">Activar cámara</button>
              ) : (
                <button onClick={stop} className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-xs rounded">Detener</button>
              )}
            </div>
            <video ref={videoRef} autoPlay playsInline muted className={`mt-3 w-full rounded bg-black ${active ? "block" : "hidden"}`} style={{ maxHeight: 160 }} />
            <p className="mt-2 text-[10px] text-slate-500">Solo modula h_pulse y λ; nunca bloquea la pasarela (soberanía operativa).</p>
          </div>
        </div>

        <div className="lg:col-span-2">
          {view === "3d" ? <TraianusUlpia3DCanvas heartRateBpm={heartRateBpm} alphaTarget={PHYSICS.ALPHA_TARGET} /> : <UlpiaCanvas token={token || undefined} />}
        </div>
      </div>
    </div>
  );
}
