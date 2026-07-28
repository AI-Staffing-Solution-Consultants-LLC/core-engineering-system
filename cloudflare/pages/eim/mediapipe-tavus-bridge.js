/**
 * MediaPipe ↔ Tavus Bridge
 * =========================
 * Bridges MediaPipe FaceTracker blendshape events to Tavus-ready context data.
 * Throttles output to 500ms intervals to avoid flooding downstream consumers.
 * Dispatches `tavus-context` events that carry formatted emotional context.
 *
 * Operates independently from TavusAvatar — both initialize independently,
 * but share data through the bridge.
 *
 * @module mediapipe-tavus-bridge
 * @exports MediapipeTavusBridge (default)
 *
 * Usage:
 *   import MediapipeTavusBridge from './mediapipe-tavus-bridge.js';
 *   const bridge = new MediapipeTavusBridge();
 *   bridge.addEventListener('tavus-context', (e) => console.log(e.detail));
 *   bridge.attach(faceTracker); // connects to FaceTracker blendshape events
 */

/* ── Throttle Configuration ─────────────────────────────────────────────── */

const THROTTLE_MS = 500;
const SIGNIFICANT_CHANGE_THRESHOLD = 0.05;

/* ── Key blendshape mapping ─────────────────────────────────────────────── */

// Map MediaPipe blendshape names to simplified categories useful for Tavus context
const BLENDSHAPE_CATEGORIES = {
  // Positive expressions
  browInnerUp: 'expression',
  browDownLeft: 'expression',
  browDownRight: 'expression',
  browOuterUpLeft: 'expression',
  browOuterUpRight: 'expression',

  // Eye expressions
  eyeLookUpLeft: 'gaze',
  eyeLookUpRight: 'gaze',
  eyeLookDownLeft: 'gaze',
  eyeLookDownRight: 'gaze',
  eyeLookInLeft: 'gaze',
  eyeLookInRight: 'gaze',
  eyeLookOutLeft: 'gaze',
  eyeLookOutRight: 'gaze',
  eyeBlinkLeft: 'eye',
  eyeBlinkRight: 'eye',
  eyeSquintLeft: 'eye',
  eyeSquintRight: 'eye',
  eyeWideLeft: 'eye',
  eyeWideRight: 'eye',

  // Mouth expressions
  mouthSmileLeft: 'expression',
  mouthSmileRight: 'expression',
  mouthFrownLeft: 'expression',
  mouthFrownRight: 'expression',
  mouthDimpleLeft: 'expression',
  mouthDimpleRight: 'expression',
  mouthStretchLeft: 'expression',
  mouthStretchRight: 'expression',
  mouthRollLower: 'expression',
  mouthRollUpper: 'expression',
  mouthShrugLower: 'expression',
  mouthShrugUpper: 'expression',
  mouthPressLeft: 'expression',
  mouthPressRight: 'expression',
  mouthLowerDownLeft: 'expression',
  mouthLowerDownRight: 'expression',
  mouthUpperUpLeft: 'expression',
  mouthUpperUpRight: 'expression',

  // Brow / cheek
  cheekSquintLeft: 'expression',
  cheekSquintRight: 'expression',
  cheekPuff: 'expression',

  // Jaw
  jawOpen: 'expression',
  jawForward: 'expression',
  jawLeft: 'expression',
  jawRight: 'expression',

  // Nose, tongue, lip
  noseSneerLeft: 'expression',
  noseSneerRight: 'expression',
  tongueOut: 'expression',
  lipFunnel: 'expression',
  lipSuck: 'expression',
  lipPucker: 'expression',
};

/* ── Emotion inference from blendshapes ─────────────────────────────────── */

/**
 * Infer a high-level emotional state from raw blendshape scores.
 * This is a lightweight rule-based heuristic — can be upgraded to ML later.
 *
 * @param {Object} blendshapes — { blendshapeName: score, ... }
 * @returns {Object} — { primary: string, confidence: number, details: Object }
 */
function inferEmotion(blendshapes) {
  const smileScore = Math.max(
    blendshapes.mouthSmileLeft || 0,
    blendshapes.mouthSmileRight || 0
  );
  const frownScore = Math.max(
    blendshapes.mouthFrownLeft || 0,
    blendshapes.mouthFrownRight || 0
  );
  const browInnerUp = Math.max(
    blendshapes.browInnerUp || 0
  );
  const browDownAvg = (
    (blendshapes.browDownLeft || 0) + (blendshapes.browDownRight || 0)
  ) / 2;
  const jawOpen = blendshapes.jawOpen || 0;
  const eyeWideAvg = (
    (blendshapes.eyeWideLeft || 0) + (blendshapes.eyeWideRight || 0)
  ) / 2;

  let primary = 'neutral';
  let confidence = 0;

  if (smileScore > 0.3) {
    primary = 'happy';
    confidence = smileScore;
  } else if (frownScore > 0.3) {
    primary = 'sad';
    confidence = frownScore;
  } else if (browDownAvg > 0.3) {
    primary = 'angry';
    confidence = browDownAvg;
  } else if (jawOpen > 0.4 && eyeWideAvg > 0.3) {
    primary = 'surprised';
    confidence = (jawOpen + eyeWideAvg) / 2;
  } else if (browInnerUp > 0.3 && eyeWideAvg < 0.2) {
    primary = 'worried';
    confidence = browInnerUp;
  }

  return {
    primary,
    confidence: Math.round(confidence * 100) / 100,
    smile: Math.round(smileScore * 100) / 100,
    frown: Math.round(frownScore * 100) / 100,
    attention: Math.round((1 - Math.max(
      blendshapes.eyeLookUpLeft || 0,
      blendshapes.eyeLookUpRight || 0,
      blendshapes.eyeLookDownLeft || 0,
      blendshapes.eyeLookDownRight || 0
    )) * 100) / 100,
  };
}

/* ── MediapipeTavusBridge Class ──────────────────────────────────────────── */

export default class MediapipeTavusBridge extends EventTarget {
  constructor() {
    super();

    this._faceTracker = null;
    this._lastSentTime = 0;
    this._lastBlendshapes = null;
    this._running = false;
    this._onBlendshapeBound = null;
  }

  /* ── Public API ──────────────────────────────────────────────────────── */

  /**
   * Attach to a FaceTracker instance and start bridging.
   * @param {Object} faceTracker — FaceTracker instance from mediapipe-face-tracker.js
   */
  attach(faceTracker) {
    if (this._running) {
      this.detach();
    }

    this._faceTracker = faceTracker;
    this._running = true;

    this._onBlendshapeBound = (e) => {
      this._handleBlendshape(e.detail);
    };

    faceTracker.addEventListener('blendshape', this._onBlendshapeBound);
    console.log('[MediapipeTavusBridge] Attached to FaceTracker');
  }

  /**
   * Detach from the FaceTracker and stop bridging.
   */
  detach() {
    if (this._faceTracker && this._onBlendshapeBound) {
      this._faceTracker.removeEventListener('blendshape', this._onBlendshapeBound);
    }

    this._faceTracker = null;
    this._onBlendshapeBound = null;
    this._running = false;
    this._lastBlendshapes = null;
    this._lastSentTime = 0;

    console.log('[MediapipeTavusBridge] Detached');
  }

  /**
   * Return the last processed blendshape context.
   * @returns {Object|null}
   */
  getLastContext() {
    return this._lastBlendshapes;
  }

  /* ── Internal ────────────────────────────────────────────────────────── */

  /**
   * Handle incoming blendshape data with throttling.
   * Only dispatches `tavus-context` if throttle interval has passed
   * AND the blendshapes have changed significantly.
   *
   * @param {Object} blendshapes — raw blendshape scores
   */
  _handleBlendshape(blendshapes) {
    if (!this._running) return;

    const now = performance.now();

    // Throttle: skip if less than THROTTLE_MS since last send
    if (now - this._lastSentTime < THROTTLE_MS) {
      // Still update last blendshapes for polling consumers
      this._lastBlendshapes = blendshapes;
      return;
    }

    // Check for significant change
    if (this._lastBlendshapes && !this._hasSignificantChange(blendshapes)) {
      return;
    }

    this._lastSentTime = now;
    this._lastBlendshapes = blendshapes;

    // Build Tavus-compatible context
    const emotion = inferEmotion(blendshapes);
    const context = {
      timestamp: Date.now(),
      emotion,
      // Top blendshapes (only those above threshold)
      topExpressions: this._topExpressions(blendshapes, 0.1),
      // Raw data for advanced consumers
      raw: blendshapes,
    };

    this.dispatchEvent(
      new CustomEvent('tavus-context', {
        detail: context,
      })
    );
  }

  /**
   * Check if new blendshape data has changed significantly from last sent.
   * @param {Object} newBlendshapes
   * @returns {boolean}
   */
  _hasSignificantChange(newBlendshapes) {
    const prev = this._lastBlendshapes;
    if (!prev) return true;

    // Check key expressive blendshapes for meaningful delta
    const keyExpressions = [
      'mouthSmileLeft', 'mouthSmileRight',
      'mouthFrownLeft', 'mouthFrownRight',
      'browInnerUp', 'browDownLeft', 'browDownRight',
      'jawOpen', 'eyeWideLeft', 'eyeWideRight',
    ];

    for (const key of keyExpressions) {
      const prevVal = prev[key] || 0;
      const newVal = newBlendshapes[key] || 0;
      if (Math.abs(newVal - prevVal) > SIGNIFICANT_CHANGE_THRESHOLD) {
        return true;
      }
    }

    return false;
  }

  /**
   * Extract the top N active blendshape expressions sorted by score.
   * @param {Object} blendshapes
   * @param {number} threshold — minimum score to include
   * @returns {Array<{name: string, score: number, category: string}>}
   */
  _topExpressions(blendshapes, threshold = 0.1) {
    return Object.entries(blendshapes)
      .filter(([, score]) => score > threshold)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 8)
      .map(([name, score]) => ({
        name,
        score: Math.round(score * 100) / 100,
        category: BLENDSHAPE_CATEGORIES[name] || 'other',
      }));
  }
}
