/**
 * MediaPipe Face Tracker — Client-Side Face Landmarker
 * ====================================================
 * Loads MediaPipe FaceLandmarker WASM via CDN, captures webcam video,
 * runs real-time 478-point face mesh detection + 52 blendshape scores.
 * ALL processing is local to the browser — zero server uploads.
 *
 * @module mediapipe-face-tracker
 * @exports FaceTracker
 *
 * Usage:
 *   import FaceTracker from './mediapipe-face-tracker.js';
 *   const tracker = new FaceTracker({ canvasId: 'face-mesh-canvas' });
 *   tracker.addEventListener('blendshape', (e) => console.log(e.detail));
 *   tracker.addEventListener('status', (e) => console.log(e.detail.status));
 *   await tracker.start();
 */

/* ── MediaPipe CDN paths ────────────────────────────────────────────────── */

// JS API: ES module bundle from jsDelivr
const TASKS_VISION_CDN =
  'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.18/+esm';

// WASM binaries: FilesetResolver loads the .wasm and .js glue from here
const WASM_CDN =
  'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.18/wasm';

// Model asset: pre-trained FaceLandmarker model (float16, latest)
const MODEL_ASSET =
  'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task';

/* ── Drawing constants ──────────────────────────────────────────────────── */

const LANDMARK_RADIUS = 1.5;
const LANDMARK_COLOR = 'rgba(56, 189, 248, 0.35)'; // --color-accent / low opacity
const LANDMARK_COLOR_IRIS = 'rgba(99, 102, 241, 0.45)'; // --color-secondary

// Iris landmark indices (left iris: 468–472, right iris: 473–477)
const LEFT_IRIS_INDICES = [468, 469, 470, 471, 472];
const RIGHT_IRIS_INDICES = [473, 474, 475, 476, 477];

/* ── FaceTracker Class ──────────────────────────────────────────────────── */

export default class FaceTracker extends EventTarget {
  /**
   * @param {Object} [options]
   * @param {string} [options.canvasId='face-mesh-canvas'] — id of <canvas> for overlay
   * @param {string} [options.containerSelector='.canvas-frame'] — parent container
   * @param {number} [options.numFaces=1] — max faces to track
   * @param {string} [options.delegate='GPU'] — "GPU" or "CPU"
   */
  constructor(options = {}) {
    super();

    this.canvasId = options.canvasId || 'face-mesh-canvas';
    this.containerSelector = options.containerSelector || '.canvas-frame';
    this.numFaces = options.numFaces ?? 1;
    this.delegate = options.delegate || 'GPU';

    // Internal state
    this._status = 'idle';
    this._landmarker = null;
    this._vision = null;
    this._videoEl = null;
    this._stream = null;
    this._rafId = null;
    this._lastVideoTime = -1;
    this._ctx = null;
    this._canvas = null;
    this._lastResult = null;
    this._lastBlendshapes = null;
    this._running = false;
  }

  /* ── Public API ──────────────────────────────────────────────────────── */

  /**
   * Start face tracking: load WASM + model, request webcam, begin loop.
   * Dispatches `status` events as state changes.
   * @returns {Promise<void>}
   */
  async start() {
    if (this._running) return;

    this._dispatchStatus('initializing');

    try {
      await this._initWasm();
      await this._initModel();
      await this._initCamera();
      this._initCanvas();
      this._startLoop();
      this._running = true;
      this._dispatchStatus('running');
    } catch (err) {
      console.error('[FaceTracker] Start failed:', err);
      if (err.code !== 'CAMERA_UNAVAILABLE') {
        this._dispatchStatus('error', { message: err.message || String(err) });
      }
    }
  }

  /**
   * Stop face tracking: stop webcam, cancel animation frame, clean up.
   */
  stop() {
    this._running = false;

    if (this._rafId) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }

    if (this._stream) {
      this._stream.getTracks().forEach((t) => t.stop());
      this._stream = null;
    }

    if (this._videoEl && this._videoEl.parentNode) {
      this._videoEl.parentNode.removeChild(this._videoEl);
    }
    this._videoEl = null;

    if (this._landmarker) {
      this._landmarker.close();
      this._landmarker = null;
    }

    this._lastVideoTime = -1;
    this._lastResult = null;
    this._lastBlendshapes = null;

    this._clearCanvas();
    this._dispatchStatus('idle');
  }

  /**
   * Return the last FaceLandmarkerResult synchronously (for testing).
   * @returns {Object|null}
   */
  detectOnce() {
    return this._lastResult;
  }

  /**
   * Return the latest blendshape scores object.
   * @returns {Object|null} — { blendshapeName: score, ... }
   */
  getBlendshapes() {
    return this._lastBlendshapes;
  }

  /* ── Initialization methods ──────────────────────────────────────────── */

  async _initWasm() {
    const { FilesetResolver, FaceLandmarker } = await import(TASKS_VISION_CDN);

    this._FaceLandmarker = FaceLandmarker;
    this._vision = await FilesetResolver.forVisionTasks(WASM_CDN);
  }

  async _initModel() {
    this._landmarker = await this._FaceLandmarker.createFromOptions(
      this._vision,
      {
        baseOptions: {
          modelAssetPath: MODEL_ASSET,
          delegate: this.delegate,
        },
        runningMode: 'VIDEO',
        outputFaceBlendshapes: true,
        outputFacialTransformationMatrixes: false,
        numFaces: this.numFaces,
      }
    );
  }

  /**
   * Request webcam access and create a hidden video element.
   */
  async _initCamera() {
    try {
      this._stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user',
        },
      });
    } catch (err) {
      if (
        err.name === 'NotAllowedError' ||
        err.name === 'NotFoundError' ||
        err.name === 'NotReadableError'
      ) {
        this._dispatchStatus('no-camera', {
          message: 'Camera access denied or unavailable. Check permissions.',
        });
        const camErr = new Error('Camera unavailable');
        camErr.code = 'CAMERA_UNAVAILABLE';
        throw camErr;
      }
      throw err;
    }

    this._videoEl = document.createElement('video');
    this._videoEl.setAttribute('playsinline', '');
    this._videoEl.setAttribute('autoplay', '');
    this._videoEl.style.display = 'none';
    this._videoEl.srcObject = this._stream;

    // Wait for video to be ready
    await new Promise((resolve, reject) => {
      this._videoEl.onloadedmetadata = () => {
        this._videoEl.play().then(resolve).catch(reject);
      };
    });
  }

  /**
   * Prepare the overlay canvas for face mesh rendering.
   */
  _initCanvas() {
    const container = document.querySelector(this.containerSelector);
    if (!container) return;

    this._canvas = document.getElementById(this.canvasId);
    if (!this._canvas) return;

    this._ctx = this._canvas.getContext('2d');

    // Size canvas to match the container
    this._resizeCanvas();
    window.addEventListener('resize', () => this._resizeCanvas());
  }

  _resizeCanvas() {
    if (!this._canvas || !this._canvas.parentElement) return;
    const parent = this._canvas.parentElement;
    const w = parent.clientWidth;
    const h = parent.clientHeight;
    this._canvas.width = w;
    this._canvas.height = h;
  }

  /* ── Detection Loop ──────────────────────────────────────────────────── */

  _startLoop() {
    const loop = () => {
      if (!this._running || !this._videoEl || !this._landmarker) {
        this._rafId = null;
        return;
      }

      const video = this._videoEl;

      // Only process when a new frame is available
      if (video.currentTime !== this._lastVideoTime) {
        try {
          const results = this._landmarker.detectForVideo(
            video,
            performance.now()
          );

          this._lastResult = results;

          // Extract blendshapes
          if (
            results.faceBlendshapes &&
            results.faceBlendshapes.length > 0
          ) {
            const cats = results.faceBlendshapes[0].categories;
            const blends = {};
            for (const c of cats) {
              blends[c.categoryName] = c.score;
            }
            this._lastBlendshapes = blends;
            this._dispatchBlendshape(blends);
          }

          // Extract landmarks
          if (
            results.faceLandmarks &&
            results.faceLandmarks.length > 0
          ) {
            const landmarks = results.faceLandmarks[0];
            this._dispatchLandmarks(landmarks);
            this._drawLandmarks(landmarks);
          } else {
            this._clearCanvas();
          }

          this._lastVideoTime = video.currentTime;
        } catch (err) {
          // Silently skip frame errors; don't crash the loop
          console.warn('[FaceTracker] Detection frame error:', err.message);
        }
      }

      this._rafId = requestAnimationFrame(loop);
    };

    this._rafId = requestAnimationFrame(loop);
  }

  /* ── Canvas Drawing ──────────────────────────────────────────────────── */

  _drawLandmarks(landmarks) {
    if (!this._ctx || !this._canvas) return;

    const ctx = this._ctx;
    const w = this._canvas.width;
    const h = this._canvas.height;

    ctx.clearRect(0, 0, w, h);

    for (let i = 0; i < landmarks.length; i++) {
      const { x, y } = landmarks[i];
      // MediaPipe returns normalized coordinates (0–1 for x, y from top-left)
      const px = x * w;
      const py = y * h;
      const isIris = LEFT_IRIS_INDICES.includes(i) || RIGHT_IRIS_INDICES.includes(i);

      ctx.beginPath();
      ctx.arc(px, py, LANDMARK_RADIUS, 0, 2 * Math.PI);
      ctx.fillStyle = isIris ? LANDMARK_COLOR_IRIS : LANDMARK_COLOR;
      ctx.fill();
    }
  }

  _clearCanvas() {
    if (!this._ctx || !this._canvas) return;
    this._ctx.clearRect(
      0,
      0,
      this._canvas.width,
      this._canvas.height
    );
  }

  /* ── Event Helpers ───────────────────────────────────────────────────── */

  _dispatchStatus(status, extra = {}) {
    this._status = status;
    this.dispatchEvent(
      new CustomEvent('status', {
        detail: { status, ...extra },
      })
    );
  }

  _dispatchBlendshape(blendshapes) {
    this.dispatchEvent(
      new CustomEvent('blendshape', {
        detail: blendshapes,
      })
    );
  }

  _dispatchLandmarks(landmarks) {
    this.dispatchEvent(
      new CustomEvent('landmarks', {
        detail: {
          landmarks,
          count: landmarks.length,
        },
      })
    );
  }
}
