import React, { useEffect, useRef, useState } from "react";
import { PHYSICS } from "../config/traianus.constants";

export interface UlpiaNode {
  id: string;
  label: string;
  soma: number;
  etica: number;
  topologia: number;
  expresion: number;
  silicio: number;
  alivio: number;
  x: number;
  y: number;
  z: number;
  px: number;
  py: number;
  pz: number;
  targetX: number;
  targetY: number;
  targetZ: number;
  color: string;
  size: number;
}

interface TraianusUlpia3DCanvasProps {
  width?: number;
  height?: number;
  alphaTarget?: number;
  heartRateBpm?: number;
}

export const TraianusUlpia3DCanvas: React.FC<TraianusUlpia3DCanvasProps> = ({
  width = PHYSICS.WIDTH,
  height = PHYSICS.HEIGHT,
  alphaTarget = PHYSICS.ALPHA_TARGET,
  heartRateBpm = PHYSICS.BPM_DEFAULT,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [activeNode, setActiveNode] = useState<UlpiaNode | null>(null);
  const [stabilized, setStabilized] = useState<boolean>(false);
  const [energy, setEnergy] = useState<number>(0);

  const nodesRef = useRef<UlpiaNode[]>([]);
  const rotationRef = useRef<{ x: number; y: number }>({ x: 0.5, y: -0.6 });
  const mouseRef = useRef<{ x: number; y: number; isDown: boolean; lastX: number; lastY: number }>({
    x: 0,
    y: 0,
    isDown: false,
    lastX: 0,
    lastY: 0,
  });
  const energyRef = useRef(0);
  const stabilizedRef = useRef(false);

  useEffect(() => {
    const rawData = [
      { id: "endolinfa", label: "Endolinfa Pura", coords: [0.95, 0.1, 0.0, 0.0, 0.1, 0.0], color: "#EF4444", size: 10 },
      { id: "conatus", label: "Conatus Absoluto", coords: [0.1, 0.95, 0.1, 0.0, 0.0, 0.0], color: "#F59E0B", size: 10 },
      { id: "topologia", label: "Topología Hermética", coords: [0.0, 0.1, 0.95, 0.0, 0.1, 0.0], color: "#10B981", size: 9 },
      { id: "glosolalia", label: "Glosolalia Fluida", coords: [0.1, 0.0, 0.1, 0.9, 0.0, 0.1], color: "#06B6D4", size: 9 },
      { id: "termofusion", label: "Termofusión Local", coords: [0.0, 0.0, 0.1, 0.1, 0.9, 0.1], color: "#8B5CF6", size: 8 },
      { id: "resistencia", label: "Resistencia Soberana", coords: [0.0, 0.0, 0.0, 0.0, 0.1, 0.99], color: "#3B82F6", size: 12 },
      { id: "axioma_ser", label: "Axioma del Ser", coords: [0.8, 0.8, 0.1, 0.0, 0.0, 0.0], color: "#EC4899", size: 11 },
      { id: "sinuosidad", label: "Sinuosidad Sanguínea", coords: [0.7, 0.4, 0.2, 0.1, 0.0, 0.1], color: "#DC2626", size: 10 },
      { id: "linea_fuga", label: "Línea de Fuga", coords: [0.2, 0.6, 0.3, 0.5, 0.1, 0.1], color: "#A855F7", size: 9 },
      { id: "muelle_sammon", label: "Muelle de Sammon", coords: [0.1, 0.2, 0.8, 0.2, 0.2, 0.1], color: "#10B981", size: 8 },
      { id: "caja_negra", label: "Caja Negra (Nube API)", coords: [0.1, 0.1, 0.1, 0.2, 0.1, 0.8], color: "#4B5563", size: 11 },
      { id: "tutor_neuro", label: "Tutor Neurosimbólico", coords: [0.3, 0.5, 0.6, 0.2, 0.4, 0.1], color: "#10B981", size: 9 },
      { id: "trazo_memoria", label: "Trazo de Memoria", coords: [0.5, 0.5, 0.2, 0.4, 0.1, 0.1], color: "#F59E0B", size: 8 },
      { id: "estimulo_purgado", label: "Estímulo Purgado", coords: [0.1, 0.1, 0.1, 0.1, 0.1, 0.9], color: "#3B82F6", size: 9 },
      { id: "frontera_2026", label: "Frontera 2026", coords: [0.4, 0.3, 0.5, 0.1, 0.3, 0.4], color: "#6B7280", size: 10 },
    ];

    const initializedNodes: UlpiaNode[] = rawData.map((item) => {
      const targetX = (item.coords[0] - item.coords[2] + item.coords[4] * 0.5) * 2.0;
      const targetY = (item.coords[1] - item.coords[3] - item.coords[5] * 0.3) * 2.0;
      const targetZ = (item.coords[0] * 0.4 + item.coords[1] * 0.4 - item.coords[5] * 0.8) * 1.5;
      const randomPerturbationX = (Math.random() - 0.5) * PHYSICS.PERTURB_RANGE;
      const randomPerturbationY = (Math.random() - 0.5) * PHYSICS.PERTURB_RANGE;
      const randomPerturbationZ = (Math.random() - 0.5) * PHYSICS.PERTURB_RANGE;
      const startX = targetX + randomPerturbationX;
      const startY = targetY + randomPerturbationY;
      const startZ = targetZ + randomPerturbationZ;
      return {
        id: item.id,
        label: item.label,
        soma: item.coords[0],
        etica: item.coords[1],
        topologia: item.coords[2],
        expresion: item.coords[3],
        silicio: item.coords[4],
        alivio: item.coords[5],
        x: startX,
        y: startY,
        z: startZ,
        px: startX,
        py: startY,
        pz: startZ,
        targetX,
        targetY,
        targetZ,
        color: item.color,
        size: item.size,
      };
    });

    nodesRef.current = initializedNodes;
    setStabilized(false);
    stabilizedRef.current = false;
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let time = 0;
    let lastEnergyUpdate = 0;

    const render = () => {
      time += PHYSICS.TIME_STEP;
      const nodes = nodesRef.current;
      if (nodes.length === 0) {
        animationFrameId = requestAnimationFrame(render);
        return;
      }

      let totalVelocitySq = 0;
      const hPulse = Math.sin((time * heartRateBpm * Math.PI) / 30) * PHYSICS.H_PULSE_AMP;

      const forces = nodes.map((node, i) => {
        let fx = 0;
        let fy = 0;
        let fz = 0;
        nodes.forEach((other, j) => {
          if (i === j) return;
          const dx = node.x - other.x;
          const dy = node.y - other.y;
          const dz = node.z - other.z;
          const distCurrent = Math.sqrt(dx * dx + dy * dy + dz * dz) + 1e-5;
          const dot = node.soma * other.soma + node.etica * other.etica + node.topologia * other.topologia + node.expresion * other.expresion + node.silicio * other.silicio + node.alivio * other.alivio;
          const distIdeal = (1.0 - dot) * PHYSICS.IDEAL_DIST_SCALE + PHYSICS.IDEAL_DIST_OFFSET;
          const fMag = -PHYSICS.K_SPRING * (distCurrent - distIdeal);
          fx += (dx / distCurrent) * fMag;
          fy += (dy / distCurrent) * fMag;
          fz += (dz / distCurrent) * fMag;
        });
        fx += alphaTarget * (node.targetX - node.x);
        fy += alphaTarget * (node.targetY - node.y);
        const rawTargetZ = node.targetZ + hPulse * (node.soma + PHYSICS.SOMATIC_BIAS);
        fz += alphaTarget * (rawTargetZ - node.z);
        return { fx, fy, fz };
      });

      nodes.forEach((node, i) => {
        const { fx, fy, fz } = forces[i];
        const tempX = node.x;
        const tempY = node.y;
        const tempZ = node.z;
        node.x = node.x + (node.x - node.px) * (1.0 - PHYSICS.FRICTION) + fx * (PHYSICS.DT * PHYSICS.DT);
        node.y = node.y + (node.y - node.py) * (1.0 - PHYSICS.FRICTION) + fy * (PHYSICS.DT * PHYSICS.DT);
        node.z = node.z + (node.z - node.pz) * (1.0 - PHYSICS.FRICTION) + fz * (PHYSICS.DT * PHYSICS.DT);
        node.px = tempX;
        node.py = tempY;
        node.pz = tempZ;
        const vx = (node.x - node.px) / PHYSICS.DT;
        const vy = (node.y - node.py) / PHYSICS.DT;
        const vz = (node.z - node.pz) / PHYSICS.DT;
        totalVelocitySq += vx * vx + vy * vy + vz * vz;
      });

      const kineticEnergy = 0.5 * totalVelocitySq;
      energyRef.current = kineticEnergy;
      if (time - lastEnergyUpdate > 0.2) {
        lastEnergyUpdate = time;
        setEnergy(kineticEnergy);
        const stable = kineticEnergy < PHYSICS.TOL;
        if (stable !== stabilizedRef.current) {
          stabilizedRef.current = stable;
          setStabilized(stable);
        }
      }

      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = "#0F172A";
      ctx.fillRect(0, 0, width, height);

      const pulseAlpha = Math.max(0, hPulse * 0.2);
      ctx.strokeStyle = `rgba(239, 68, 68, ${pulseAlpha})`;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(width / 2, height / 2, Math.min(width, height) * 0.45, 0, Math.PI * 2);
      ctx.stroke();

      const cosX = Math.cos(rotationRef.current.x);
      const sinX = Math.sin(rotationRef.current.x);
      const cosY = Math.cos(rotationRef.current.y);
      const sinY = Math.sin(rotationRef.current.y);

      const transformedNodes = nodes.map((node) => {
        const x1 = node.x * cosY - node.z * sinY;
        const z1 = node.x * sinY + node.z * cosY;
        const y2 = node.y * cosX - z1 * sinX;
        const z2 = node.y * sinX + z1 * cosX;
        const perspective = PHYSICS.PERSPECTIVE / (z2 + PHYSICS.CAM_DIST);
        const projX = width / 2 + x1 * perspective;
        const projY = height / 2 + y2 * perspective;
        return { node, projX, projY, depth: z2, size: node.size * (perspective / 150) };
      });

      transformedNodes.sort((a, b) => b.depth - a.depth);

      ctx.lineWidth = 1;
      transformedNodes.forEach((a, idxA) => {
        transformedNodes.forEach((b, idxB) => {
          if (idxA >= idxB) return;
          const dx = a.node.x - b.node.x;
          const dy = a.node.y - b.node.y;
          const dz = a.node.z - b.node.z;
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
          if (dist < 2.0) {
            const opacity = Math.max(0, 1.0 - dist / 2.0) * 0.25;
            ctx.strokeStyle = `rgba(148, 163, 184, ${opacity})`;
            ctx.beginPath();
            ctx.moveTo(a.projX, a.projY);
            ctx.lineTo(b.projX, b.projY);
            ctx.stroke();
          }
        });
      });

      ctx.strokeStyle = "rgba(51, 65, 85, 0.15)";
      ctx.lineWidth = 0.5;
      for (let i = -PHYSICS.GRID_SEG; i <= PHYSICS.GRID_SEG; i++) {
        ctx.beginPath();
        for (let j = -PHYSICS.GRID_SEG; j <= PHYSICS.GRID_SEG; j++) {
          const gx = (i / PHYSICS.GRID_SEG) * 3.0;
          const gy = (j / PHYSICS.GRID_SEG) * 3.0;
          const distCenter = Math.sqrt(gx * gx + gy * gy);
          const gz = hPulse * Math.exp(-distCenter * distCenter * 0.5) * 1.5 - 0.5;
          const rx1 = gx * cosY - gz * sinY;
          const rz1 = gx * sinY + gz * cosY;
          const ry2 = gy * cosX - rz1 * sinX;
          const rz2 = gy * sinX + rz1 * cosX;
          const pers = PHYSICS.PERSPECTIVE / (rz2 + PHYSICS.CAM_DIST);
          const px = width / 2 + rx1 * pers;
          const py = height / 2 + ry2 * pers;
          if (j === -PHYSICS.GRID_SEG) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.stroke();
      }

      transformedNodes.forEach(({ node }) => {
        const floorZ = -1.2;
        const x1 = node.x * cosY - floorZ * sinY;
        const z1 = node.x * sinY + floorZ * cosY;
        const y2 = node.y * cosX - z1 * sinX;
        const z2 = node.y * sinX + z1 * cosX;
        const pers = PHYSICS.PERSPECTIVE / (z2 + PHYSICS.CAM_DIST);
        const shadowX = width / 2 + x1 * pers;
        const shadowY = height / 2 + y2 * pers;
        ctx.fillStyle = "rgba(15, 23, 42, 0.6)";
        ctx.beginPath();
        ctx.arc(shadowX, shadowY, 6 * (pers / 120), 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = "rgba(51, 65, 85, 0.4)";
        ctx.beginPath();
        ctx.arc(shadowX, shadowY, 6 * (pers / 120), 0, Math.PI * 2);
        ctx.stroke();
      });

      transformedNodes.forEach(({ node, projX, projY, depth, size }) => {
        const depthShade = Math.max(0.3, Math.min(1.0, 1.2 - (depth + 1.5) / 3.0));
        ctx.fillStyle = node.color;
        ctx.shadowBlur = activeNode?.id === node.id ? 15 : 4;
        ctx.shadowColor = node.color;
        ctx.beginPath();
        ctx.arc(projX, projY, size, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
        if (depthShade > 0.4 || activeNode?.id === node.id) {
          ctx.fillStyle = activeNode?.id === node.id ? "#FFFFFF" : `rgba(226, 232, 240, ${depthShade})`;
          ctx.font = activeNode?.id === node.id ? "bold 11px sans-serif" : "9px sans-serif";
          ctx.fillText(node.label, projX + size + 4, projY + 3);
        }
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationFrameId);
  }, [width, height, alphaTarget, heartRateBpm]);

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    mouseRef.current.isDown = true;
    mouseRef.current.lastX = mouseX;
    mouseRef.current.lastY = mouseY;
    const cosX = Math.cos(rotationRef.current.x);
    const sinX = Math.sin(rotationRef.current.x);
    const cosY = Math.cos(rotationRef.current.y);
    const sinY = Math.sin(rotationRef.current.y);
    let clickedNode: UlpiaNode | null = null;
    let minDistance = PHYSICS.HITBOX_RADIUS;
    nodesRef.current.forEach((node) => {
      const x1 = node.x * cosY - node.z * sinY;
      const z1 = node.x * sinY + node.z * cosY;
      const y2 = node.y * cosX - z1 * sinX;
      const z2 = node.y * sinX + z1 * cosX;
      const perspective = PHYSICS.PERSPECTIVE / (z2 + PHYSICS.CAM_DIST);
      const projX = width / 2 + x1 * perspective;
      const projY = height / 2 + y2 * perspective;
      const dx = mouseX - projX;
      const dy = mouseY - projY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < minDistance) {
        minDistance = dist;
        clickedNode = node;
      }
    });
    if (clickedNode) setActiveNode(clickedNode);
    else setActiveNode(null);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    if (mouseRef.current.isDown) {
      if (activeNode) {
        const deltaX = (mouseX - mouseRef.current.lastX) * PHYSICS.DRAG_SCALE;
        const deltaY = (mouseY - mouseRef.current.lastY) * PHYSICS.DRAG_SCALE;
        activeNode.x += deltaX;
        activeNode.y += deltaY;
        setStabilized(false);
        stabilizedRef.current = false;
      } else {
        const deltaX = mouseX - mouseRef.current.lastX;
        const deltaY = mouseY - mouseRef.current.lastY;
        rotationRef.current.y += deltaX * PHYSICS.ROT_SENS;
        rotationRef.current.x += deltaY * PHYSICS.ROT_SENS;
      }
    }
    mouseRef.current.lastX = mouseX;
    mouseRef.current.lastY = mouseY;
  };

  const handleMouseUp = () => {
    mouseRef.current.isDown = false;
  };

  return (
    <div className="flex flex-col items-center bg-slate-950 p-6 rounded-xl border border-slate-800 shadow-2xl max-w-4xl mx-auto">
      <div className="w-full flex justify-between items-center mb-4 border-b border-slate-800 pb-3">
        <div>
          <h2 className="text-white text-lg font-bold tracking-wide">Capa de Observación Ulpia 3D</h2>
          <p className="text-slate-400 text-xs">Sustrato de visualización elástica e inmanente bajo pulso hemodinámico</p>
        </div>
        <div className="flex gap-4">
          <div className="text-right">
            <div className="text-slate-500 text-[10px] uppercase font-semibold">Homeostasis</div>
            <div className={`text-xs font-bold ${stabilized ? "text-emerald-400" : "text-amber-400 animate-pulse"}`}>{stabilized ? "ESTABLE" : "RELAJANDO..."}</div>
          </div>
          <div className="text-right">
            <div className="text-slate-500 text-[10px] uppercase font-semibold">Energía Cinética</div>
            <div className="text-xs font-bold text-sky-400 font-mono">{energy.toFixed(6)} J</div>
          </div>
        </div>
      </div>

      <div className="relative border border-slate-800 rounded-lg overflow-hidden bg-slate-900 shadow-inner">
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          className="cursor-grab active:cursor-grabbing block"
        />
        {activeNode && (
          <div className="absolute top-4 left-4 bg-slate-950/90 border border-slate-800 backdrop-blur-md p-4 rounded-lg text-white max-w-xs text-xs shadow-lg animate-fade-in">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-3 h-3 rounded-full block" style={{ backgroundColor: activeNode.color }} />
              <div className="font-bold text-sm tracking-tight">{activeNode.label}</div>
            </div>
            <div className="space-y-1 mb-2 text-slate-300 font-mono text-[10px]">
              <div className="flex justify-between"><span>Endolinfa (Soma):</span><span className="text-red-400 font-bold">{(activeNode.soma * 100).toFixed(1)}%</span></div>
              <div className="flex justify-between"><span>Conatus (Ética):</span><span className="text-amber-400 font-bold">{(activeNode.etica * 100).toFixed(1)}%</span></div>
              <div className="flex justify-between"><span>Homología (Math):</span><span className="text-emerald-400 font-bold">{(activeNode.topologia * 100).toFixed(1)}%</span></div>
              <div className="flex justify-between"><span>Glosolalia (Exp):</span><span className="text-cyan-400 font-bold">{(activeNode.expresion * 100).toFixed(1)}%</span></div>
              <div className="flex justify-between"><span>Termofusión (Silicio):</span><span className="text-purple-400 font-bold">{(activeNode.silicio * 100).toFixed(1)}%</span></div>
              <div className="flex justify-between"><span>Resistencia (Alivio):</span><span className="text-blue-400 font-bold">{(activeNode.alivio * 100).toFixed(1)}%</span></div>
            </div>
            <p className="text-[10px] text-slate-400 italic border-t border-slate-900 pt-2">Haz clic y arrastra para perturbar las fuerzas del muelle local o rota la cámara.</p>
          </div>
        )}
      </div>

      <div className="w-full mt-4 flex justify-between items-center text-slate-500 text-[10px] tracking-wide uppercase border-t border-slate-900 pt-3">
        <span>Arnés de Control: Click + Arrastrar para rotar cámara orbit</span>
        <span>Pulso hemodinámico activo: {heartRateBpm} BPM</span>
        <span>Alineamiento Global (Alpha): {alphaTarget}</span>
      </div>
    </div>
  );
};
