import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  fetchNodes,
  fetchRelations,
  ingestText,
  waitForNode,
  type NodesNode,
  type Relation,
} from "../api";
import { notesOf, type NoteInfo } from "../notes";
import { projectTo5d } from "../projection";
import UlpiaWebGL from "./UlpiaWebGL";

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

function buildFlowEdges(relations: Relation[]): Edge[] {
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
  const [entry, setEntry] = useState<{ text: string; failed: boolean } | null>(null);
  const [notes, setNotes] = useState<ReadonlyMap<string, NoteInfo>>(() => new Map());
  const [relations, setRelations] = useState<readonly Relation[]>([]);
  const [mapVersion, setMapVersion] = useState(0);
  // One idempotency key per submission: a retry of the same text reuses it.
  const submission = useRef<{ text: string; key: string } | null>(null);
  const mounted = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    mounted.current = controller;
    return () => controller.abort();
  }, []);

  const loadData = useCallback(
    async (nodesData: NodesNode[]) => {
      setNotes(notesOf(nodesData));
      const fetched = await fetchRelations(token);
      setRelations(fetched);

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
      setEdges(buildFlowEdges(fetched));
    },
    [token]
  );

  useEffect(() => {
    fetchNodes()
      .then(loadData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Unknown error"));
  }, [loadData]);

  const handleIngest = useCallback(async () => {
    const text = inputText.trim();
    if (!text || !token || ingesting) return;
    const current =
      submission.current?.text === text ? submission.current : { text, key: crypto.randomUUID() };
    submission.current = current;
    setIngesting(true);
    setEntry({ text: "Sending...", failed: false });
    let ingestionId: string | null = null;
    try {
      ingestionId = await ingestText(text, token, current.key);
      setEntry({ text: `Waiting for NODE_${ingestionId}...`, failed: false });
      const listed = await waitForNode(`NODE_${ingestionId}`, mounted.current?.signal);
      submission.current = null;
      setInputText("");
      setEntry({ text: `Entered as NODE_${ingestionId}`, failed: false });
      setMapVersion((v) => v + 1);
      await loadData(listed);
    } catch (e: unknown) {
      if (mounted.current?.signal.aborted) return;
      const reason = e instanceof Error ? e.message : "Ingest failed";
      setEntry({
        text: ingestionId === null ? reason : `Ingestion ${ingestionId} accepted, but ${reason}`,
        failed: true,
      });
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

  const ingestBar = (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          type="text"
          placeholder="Ingest a concept..."
          value={inputText}
          onChange={(e) => {
            setInputText(e.target.value);
            setEntry(null);
          }}
          onKeyDown={(e) => e.key === "Enter" && handleIngest()}
          disabled={ingesting}
          style={{
            flex: 1,
            minWidth: 0,
            padding: "8px 14px",
            background: "#1E293B",
            border: "1px solid #334155",
            borderRadius: 6,
            color: "#F8FAFC",
            fontFamily: "monospace",
            fontSize: 13,
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
      {entry ? (
        <div
          role={entry.failed ? "alert" : "status"}
          style={{
            padding: "6px 10px",
            background: "#1E293B",
            border: `1px solid ${entry.failed ? "#F87171" : "#334155"}`,
            borderRadius: 6,
            color: entry.failed ? "#F87171" : "#94A3B8",
            fontFamily: "monospace",
            fontSize: 12,
            overflowWrap: "anywhere",
          }}
        >
          {entry.text}
        </div>
      ) : null}
    </div>
  );

  return (
    <div style={{ width: "100vw", height: "100vh", background: "#0B0F19", position: "relative" }}>
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
      {token ? (
        <UlpiaWebGL token={token} notes={notes} relations={relations} version={mapVersion}>
          {ingestBar}
        </UlpiaWebGL>
      ) : (
        <div style={{ position: "absolute", top: 12, left: 12, width: 300, zIndex: 10 }}>
          {ingestBar}
        </div>
      )}
    </div>
  );
}
