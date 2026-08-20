import { useState } from "react";
import UlpiaCanvas from "./components/UlpiaCanvas";

export default function App() {
  const [token, setToken] = useState("");
  const [connected, setConnected] = useState(false);

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
        <h1 style={{ fontSize: 24, marginBottom: 8, color: "#38BDF8" }}>
          Ulpia
        </h1>
        <p style={{ fontSize: 12, color: "#64748B", marginBottom: 24 }}>
          Traianus 5D Chromatic Canvas
        </p>
        <input
          type="text"
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

  return <UlpiaCanvas token={token || undefined} />;
}
