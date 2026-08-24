import { useState, useEffect, useCallback, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { fetchNodes, fetchRelations, ingestText, type NodesNode } from "../api";
import { projectTo5d } from "../projection";

const SCALE = 400;

const LIFECYCLE_COLORS: Record<string, string> = {
  pending_approval: "#F59E0B",
  incubating: "#3B82F6",
  consolidated: "#10B981",
  telemetry_error: "#EF4444",
};

function buildFlowNodes(
  nodes: NodesNode[],
  projections: number[][]
): Node[] {
  return nodes.map((node, i) => {
    const [x, y, r, g, b] = projections[i];
    const bg = `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`;
    const border = LIFECYCLE_COLORS[node.lifecycle_state] ?? "#475569";
    return {
      id: node.id,
      position: { x: x * SCALE, y: y * SCALE },
      data: {
        label: (
          <div style={{ textAlign: "center", color: "#F8FAFC", fontSize: 11 }}>
            <div style={{ fontWeight: 600 }}>{node.id}</div>
            <div style={{ fontSize: 9, opacity: 0.7, maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {node.text}
            </div>
          </div>
        ),
      },
      style: {
        background: bg,
        border: `2px solid ${border}`,
        borderRadius: "50%",
        width: 52,
        height: 52,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      },
    };
  });
}

function buildFlowEdges(relations: { source: string; target: string; state: string }[]): Edge[] {
  return relations.map((r, i) => ({
    id: r.id ?? `edge-${i}`,
    source: r.source,
    target: r.target,
    animated: r.state === "auto",
    style: { stroke: r.state === "auto" ? "#334155" : "#6366F1", strokeWidth: 1 },
  }));
}

interface UlpiaCanvasProps {
  token?: string;
}

export default function UlpiaCanvas({ token }: UlpiaCanvasProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [inputText, setInputText] = useState("");
  const [ingesting, setIngesting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [nodesData, relations] = await Promise.all([
        fetchNodes(),
        fetchRelations(token),
      ]);

      if (nodesData.length === 0) {
        setNodes([]);
        setEdges([]);
        return;
      }

      const matrix = nodesData.map((n) => {
        const p = n.projections_json;
        return Object.keys(p)
          .sort()
          .map((k) => p[k]);
      });

      const projections = projectTo5d(matrix);
      setNodes(buildFlowNodes(nodesData, projections));
      setEdges(buildFlowEdges(relations));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    }
  }, [token]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleIngest = useCallback(async () => {
    if (!inputText.trim() || !token || ingesting) return;
    setIngesting(true);
    try {
      await ingestText(inputText.trim(), token);
      setInputText("");
      await new Promise((r) => setTimeout(r, 600));
      await loadData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ingest failed");
    } finally {
      setIngesting(false);
    }
  }, [inputText, token, ingesting, loadData]);

  const defaultViewport = useMemo(() => ({ x: 0, y: 0, zoom: 1 }), []);

  if (error) {
    return (
      <div style={{ color: "#F87171", padding: 24, fontFamily: "monospace" }}>
        Error: {error}
      </div>
    );
  }

  return (
    <div style={{ width: "100vw", height: "100vh", background: "#0B0F19", position: "relative" }}>
      <div
        style={{
          position: "absolute",
          top: 12,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 10,
          display: "flex",
          gap: 8,
        }}
      >
        <input
          type="text"
          placeholder="Ingest a concept..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleIngest()}
          disabled={ingesting}
          style={{
            padding: "8px 14px",
            background: "#1E293B",
            border: "1px solid #334155",
            borderRadius: 6,
            color: "#F8FAFC",
            fontFamily: "monospace",
            fontSize: 13,
            width: 300,
            outline: "none",
          }}
        />
        <button
          onClick={handleIngest}
          disabled={ingesting || !inputText.trim() || !token}
          style={{
            padding: "8px 16px",
            background: ingesting ? "#334155" : "#6366F1",
            border: "none",
            borderRadius: 6,
            color: "#F8FAFC",
            fontFamily: "monospace",
            fontSize: 13,
            cursor: ingesting ? "wait" : "pointer",
            opacity: !inputText.trim() || !token ? 0.5 : 1,
          }}
        >
          {ingesting ? "..." : "Ingest"}
        </button>
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        defaultViewport={defaultViewport}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#1E293B" gap={40} />
        <Controls
          style={{ background: "#1E293B", borderColor: "#334155" }}
        />
      </ReactFlow>
    </div>
  );
}
