"use client";

import { useRef, useState, useCallback, useEffect } from "react";

/* ── MediaPipe CDN paths ────────────────────────────────────────────────── */

const TASKS_VISION_CDN =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/+esm";
const WASM_CDN =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm";
const MODEL_ASSET =
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task";

/** Runtime CDN ES module import — bypasses webpack static analysis */
function importFromCdn(url: string): Promise<any> {
  return new Function("url", "return import(url)")(url);
}

/* ── Drawing constants ──────────────────────────────────────────────────── */

const LANDMARK_RADIUS = 1.5;
const LANDMARK_COLOR = "rgba(56, 189, 248, 0.35)";
const LANDMARK_COLOR_IRIS = "rgba(99, 102, 241, 0.45)";
const LEFT_IRIS_INDICES = [468, 469, 470, 471, 472];
const RIGHT_IRIS_INDICES = [473, 474, 475, 476, 477];

/* ── Types ──────────────────────────────────────────────────────────────── */

export interface Landmark {
  x: number;
  y: number;
  z: number;
}

export interface Blendshapes {
  [categoryName: string]: number;
}

export interface FaceTrackerState {
  /** Normalized (0-1) blendshape scores for 52 categories */
  blendshapes: Blendshapes | null;
  /** 478 face landmark points (normalized 0-1 coords) */
  faceMesh: Landmark[] | null;
  /** Whether the tracker is actively running */
  isTracking: boolean;
  /** Error message, or null if healthy */
  error: string | null;
}

export interface FaceTrackerActions {
  /** Start face tracking (WASM init + webcam + detection loop) */
  start: () => Promise<void>;
  /** Stop face tracking and release all resources */
  stop: () => void;
}

/* ── Module-level singleton: FaceLandmarker is expensive to create ──────── */

let _landmarkerInstance: unknown = null;
let _landmarkerPromise: Promise<unknown> | null = null;

async function getLandmarker(): Promise<unknown> {
  if (_landmarkerInstance) return _landmarkerInstance;
  if (_landmarkerPromise) return _landmarkerPromise;

  _landmarkerPromise = (async () => {
    const { FilesetResolver, FaceLandmarker } = await importFromCdn(
      TASKS_VISION_CDN
    );
    const vision = await FilesetResolver.forVisionTasks(WASM_CDN);
    const landmarker = await FaceLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: MODEL_ASSET,
        delegate: "GPU",
      },
      runningMode: "VIDEO",
      outputFaceBlendshapes: true,
      outputFacialTransformationMatrixes: false,
      numFaces: 1,
    });
    _landmarkerInstance = landmarker;
    return landmarker;
  })();

  return _landmarkerPromise;
}

/* ── Drawing helpers ────────────────────────────────────────────────────── */

function drawLandmarks(
  ctx: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  landmarks: Landmark[]
): void {
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  for (let i = 0; i < landmarks.length; i++) {
    const { x, y } = landmarks[i];
    const px = x * w;
    const py = y * h;
    const isIris =
      LEFT_IRIS_INDICES.includes(i) || RIGHT_IRIS_INDICES.includes(i);

    ctx.beginPath();
    ctx.arc(px, py, LANDMARK_RADIUS, 0, 2 * Math.PI);
    ctx.fillStyle = isIris ? LANDMARK_COLOR_IRIS : LANDMARK_COLOR;
    ctx.fill();
  }
}

function clearCanvas(
  ctx: CanvasRenderingContext2D | null,
  canvas: HTMLCanvasElement | null
): void {
  if (!ctx || !canvas) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

/**
 * Resize the overlay canvas to match its parent container.
 */
function resizeCanvas(
  canvas: HTMLCanvasElement | null
): void {
  if (!canvas || !canvas.parentElement) return;
  const parent = canvas.parentElement;
  canvas.width = parent.clientWidth;
  canvas.height = parent.clientHeight;
}

/* ── Hook ───────────────────────────────────────────────────────────────── */

/**
 * React hook wrapping the MediaPipe FaceLandmarker pipeline.
 *
 * Ported from `cloudflare/pages/eim/mediapipe-face-tracker.js`.
 * Key changes from vanilla JS:
 *   - CustomEvent dispatch → React useState
 *   - EventTarget → hook return values
 *   - Direct DOM manipulation → useRef + useEffect
 *
 * @param canvasRef - Ref to the overlay <canvas> for face mesh rendering
 */
export function useFaceTracker(
  canvasRef: React.RefObject<HTMLCanvasElement | null>
): FaceTrackerState & FaceTrackerActions {
  const [blendshapes, setBlendshapes] = useState<Blendshapes | null>(null);
  const [faceMesh, setFaceMesh] = useState<Landmark[] | null>(null);
  const [isTracking, setIsTracking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const streamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const rafRef = useRef<number | null>(null);
  const lastVideoTimeRef = useRef(-1);
  const runningRef = useRef(false);
  const ctxRef = useRef<CanvasRenderingContext2D | null>(null);

  /* ── Detection loop ────────────────────────────────────────────────── */

  const detectionLoop = useCallback(() => {
    if (!runningRef.current || !videoRef.current) {
      rafRef.current = null;
      return;
    }

    const video = videoRef.current;
    const landmarker = _landmarkerInstance as {
      detectForVideo: (
        video: HTMLVideoElement,
        timestamp: number
      ) => {
        faceLandmarks?: Landmark[][];
        faceBlendshapes?: Array<{
          categories: Array<{ categoryName: string; score: number }>;
        }>;
      } | null;
      close?: () => void;
    } | null;

    if (!landmarker) {
      rafRef.current = requestAnimationFrame(detectionLoop);
      return;
    }

    if (video.currentTime !== lastVideoTimeRef.current) {
      try {
        const results = landmarker.detectForVideo(video, performance.now());

        if (results) {
          // Extract blendshapes
          if (
            results.faceBlendshapes &&
            results.faceBlendshapes.length > 0
          ) {
            const cats = results.faceBlendshapes[0].categories;
            const blends: Blendshapes = {};
            for (const c of cats) {
              blends[c.categoryName] = c.score;
            }
            setBlendshapes(blends);
          }

          // Extract and draw landmarks
          if (
            results.faceLandmarks &&
            results.faceLandmarks.length > 0
          ) {
            const landmarks = results.faceLandmarks[0];
            setFaceMesh(landmarks);

            const canvas = canvasRef.current;
            if (ctxRef.current && canvas) {
              drawLandmarks(ctxRef.current, canvas, landmarks);
            }
          } else {
            setFaceMesh(null);
            clearCanvas(ctxRef.current, canvasRef.current);
          }
        }

        lastVideoTimeRef.current = video.currentTime;
      } catch {
        // Silently skip frame errors; don't crash the loop
      }
    }

    rafRef.current = requestAnimationFrame(detectionLoop);
  }, [canvasRef]);

  /* ── Start ─────────────────────────────────────────────────────────── */

  const start = useCallback(async () => {
    if (runningRef.current) return;
    setError(null);

    try {
      // 1. Load WASM + model (singleton — shared across mounts)
      await getLandmarker();

      // 2. Request webcam
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 },
            facingMode: "user",
          },
        });
      } catch (camErr) {
        const err = camErr as DOMException;
        if (
          err.name === "NotAllowedError" ||
          err.name === "NotFoundError" ||
          err.name === "NotReadableError"
        ) {
          setError("Camera access required");
          return;
        }
        throw camErr;
      }
      streamRef.current = stream;

      // 3. Create hidden video element for webcam feed
      const video = document.createElement("video");
      video.setAttribute("playsinline", "");
      video.setAttribute("autoplay", "");
      video.style.display = "none";
      video.srcObject = stream;
      videoRef.current = video;

      // Wait for video ready
      await new Promise<void>((resolve, reject) => {
        video.onloadedmetadata = () => {
          video.play().then(resolve).catch(reject);
        };
      });

      // 4. Init canvas context
      const canvas = canvasRef.current;
      if (canvas) {
        ctxRef.current = canvas.getContext("2d");
        resizeCanvas(canvas);
      }

      // 5. Start detection loop
      runningRef.current = true;
      lastVideoTimeRef.current = -1;
      setIsTracking(true);
      rafRef.current = requestAnimationFrame(detectionLoop);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Perception engine unavailable";
      setError(message);
      setIsTracking(false);
    }
  }, [canvasRef, detectionLoop]);

  /* ── Stop ──────────────────────────────────────────────────────────── */

  const stop = useCallback(() => {
    runningRef.current = false;

    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    if (videoRef.current?.parentNode) {
      videoRef.current.parentNode.removeChild(videoRef.current);
    }
    videoRef.current = null;

    lastVideoTimeRef.current = -1;
    clearCanvas(ctxRef.current, canvasRef.current);
    setBlendshapes(null);
    setFaceMesh(null);
    setIsTracking(false);
    setError(null);
  }, [canvasRef]);

  /* ── Resize handler ────────────────────────────────────────────────── */

  useEffect(() => {
    function handleResize() {
      resizeCanvas(canvasRef.current);
    }

    window.addEventListener("resize", handleResize);
    // Initial size
    handleResize();

    return () => window.removeEventListener("resize", handleResize);
  }, [canvasRef]);

  /* ── Cleanup on unmount ────────────────────────────────────────────── */

  useEffect(() => {
    return () => {
      stop();
    };
  }, [stop]);

  return {
    blendshapes,
    faceMesh,
    isTracking,
    error,
    start,
    stop,
  };
}
