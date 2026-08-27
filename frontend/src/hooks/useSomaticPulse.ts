/**
 * useSomaticPulse — rPPG fotopletismografía por video (local-only)
 * Solo modula PHYSICS.FRICTION y h_pulse en canvas; nunca bloquea SovereignInputGate
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { PHYSICS } from "../config/traianus.constants";

export interface SomaticPulseState {
  bpm: number | null;
  confidence: number;
  active: boolean;
  error: string | null;
}

export interface UseSomaticPulseReturn extends SomaticPulseState {
  start: () => Promise<void>;
  stop: () => void;
  videoRef: React.RefObject<HTMLVideoElement>;
}

const BUFFER_SIZE = 90;
const FPS_TARGET = 30;
const GREEN_BAND_LOW = 0.7;
const GREEN_BAND_HIGH = 4.0;

export function useSomaticPulse(): UseSomaticPulseReturn {
  const [bpm, setBpm] = useState<number | null>(null);
  const [confidence, setConfidence] = useState(0);
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null) as React.RefObject<HTMLVideoElement>;
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const greenBufferRef = useRef<number[]>([]);
  const lastTickRef = useRef<number>(0);

  const stop = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setActive(false);
  }, []);

  const estimateBpm = useCallback((samples: number[]) => {
    if (samples.length < BUFFER_SIZE) return { bpm: null as number | null, conf: 0 };
    const mean = samples.reduce((a, b) => a + b, 0) / samples.length;
    const detrended = samples.map((v) => v - mean);
    let maxPeak = 0;
    let peakIdx = -1;
    const minLag = Math.floor((FPS_TARGET / GREEN_BAND_HIGH));
    const maxLag = Math.floor((FPS_TARGET / GREEN_BAND_LOW));
    for (let lag = minLag; lag <= maxLag; lag++) {
      let corr = 0;
      for (let i = 0; i < detrended.length - lag; i++) corr += detrended[i] * detrended[i + lag];
      if (corr > maxPeak) {
        maxPeak = corr;
        peakIdx = lag;
      }
    }
    if (peakIdx <= 0) return { bpm: null, conf: 0 };
    const fpsEst = FPS_TARGET;
    const bpmEst = (fpsEst * 60) / peakIdx;
    if (bpmEst < 42 || bpmEst > 180) return { bpm: null, conf: 0 };
    const conf = Math.min(1, maxPeak / (samples.length * 50));
    return { bpm: Math.round(bpmEst), conf };
  }, []);

  const tick = useCallback(() => {
    const video = videoRef.current;
    if (!video || video.readyState < 2) {
      rafRef.current = requestAnimationFrame(tick);
      return;
    }
    const now = performance.now();
    if (now - lastTickRef.current < 1000 / FPS_TARGET) {
      rafRef.current = requestAnimationFrame(tick);
      return;
    }
    lastTickRef.current = now;

    if (!canvasRef.current) canvasRef.current = document.createElement("canvas");
    const canvas = canvasRef.current;
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      rafRef.current = requestAnimationFrame(tick);
      return;
    }
    const vw = video.videoWidth || 64;
    const vh = video.videoHeight || 64;
    ctx.drawImage(video, 0, 0, 64, 64);
    try {
      const data = ctx.getImageData(16, 16, 32, 32).data;
      let gSum = 0;
      for (let i = 0; i < data.length; i += 4) gSum += data[i + 1];
      const gMean = gSum / (data.length / 4);
      const buf = greenBufferRef.current;
      buf.push(gMean);
      if (buf.length > BUFFER_SIZE) buf.shift();
      if (buf.length === BUFFER_SIZE) {
        const { bpm: est, conf } = estimateBpm([...buf]);
        if (est) {
          setBpm(est);
          setConfidence(conf);
        }
      }
    } catch {
      // ignore canvas taint
    }
    rafRef.current = requestAnimationFrame(tick);
  }, [estimateBpm]);

  const start = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: 160, height: 120 } });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }
      greenBufferRef.current = [];
      setActive(true);
      lastTickRef.current = performance.now();
      rafRef.current = requestAnimationFrame(tick);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      setActive(false);
    }
  }, [tick]);

  useEffect(() => () => stop(), [stop]);

  return { bpm, confidence, active, error, start, stop, videoRef };
}

export function modulatedFriction(baseFriction: number = PHYSICS.FRICTION, bpm: number | null, confidence: number): number {
  if (bpm === null || confidence < 0.25) return baseFriction;
  const norm = (bpm - 60) / 60;
  return Math.max(0.02, Math.min(0.35, baseFriction + norm * 0.04 * confidence));
}

export function modulatedPulseAmp(baseAmp: number = PHYSICS.H_PULSE_AMP, bpm: number | null, confidence: number): number {
  if (bpm === null || confidence < 0.25) return baseAmp;
  return baseAmp * (0.85 + confidence * 0.3);
}
