"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export default function MatrixPanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [webglSupported, setWebglSupported] = useState(true);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // ── WebGL support check ──────────────────────────────────────────
    let gl: WebGLRenderingContext | null = null;
    try {
      const canvas = document.createElement("canvas");
      gl =
        (canvas.getContext("webgl") as WebGLRenderingContext | null) ||
        (canvas.getContext("experimental-webgl") as WebGLRenderingContext | null) ||
        null;
    } catch {
      gl = null;
    }
    if (!gl) {
      setWebglSupported(false);
      return;
    }

    const rect = container.getBoundingClientRect();
    const initialWidth = rect.width || 1;
    const initialHeight = rect.height || 1;

    // ── Scene ────────────────────────────────────────────────────────
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#1e293b");

    // ── Camera ───────────────────────────────────────────────────────
    const camera = new THREE.PerspectiveCamera(
      50,
      initialWidth / initialHeight,
      0.1,
      100,
    );
    camera.position.set(15, 10, 15);
    camera.lookAt(0, 0, 0);

    // ── Renderer ─────────────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(initialWidth, initialHeight);
    container.appendChild(renderer.domElement);

    // ── Grid ─────────────────────────────────────────────────────────
    const gridHelper = new THREE.GridHelper(20, 20, 0x334155, 0x253247);
    scene.add(gridHelper);

    // ── Columns ──────────────────────────────────────────────────────
    const gridSize = 20;
    const half = gridSize / 2;
    const cyanBright = new THREE.Color("#22d3ee");
    const cyanDim = new THREE.Color("#0e7490");
    const columns: THREE.Mesh[] = [];

    for (let x = -half; x <= half; x++) {
      for (let z = -half; z <= half; z++) {
        const height = Math.random() * 2.5 + 0.5; // 0.5 – 3.0
        const t = (height - 0.5) / 2.5; // 0 → 1
        const color = new THREE.Color().copy(cyanDim).lerp(cyanBright, t);

        const geometry = new THREE.BoxGeometry(0.1, height, 0.1);
        const material = new THREE.MeshBasicMaterial({
          color,
          wireframe: true,
        });
        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(x, height / 2, z);
        mesh.userData.originalColor = color.clone();

        scene.add(mesh);
        columns.push(mesh);
      }
    }

    // ── Orbit Controls ───────────────────────────────────────────────
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0, 0);

    // ── Raycaster (hover) ────────────────────────────────────────────
    const raycaster = new THREE.Raycaster();
    raycaster.params.Points.threshold = 0.3;
    const mouse = new THREE.Vector2();
    let hovered: THREE.Mesh | null = null;

    // ── Render helpers ───────────────────────────────────────────────
    function renderScene() {
      renderer.render(scene, camera);
    }

    function resetHover() {
      if (!hovered) return;
      (hovered.material as THREE.MeshBasicMaterial).color.copy(
        hovered.userData.originalColor,
      );
      hovered = null;
    }

    // ── Events ───────────────────────────────────────────────────────
    controls.addEventListener("change", renderScene);

    function onPointerMove(event: MouseEvent) {
      const r = container!.getBoundingClientRect();
      mouse.x = ((event.clientX - r.left) / r.width) * 2 - 1;
      mouse.y = -((event.clientY - r.top) / r.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(columns);

      if (intersects.length > 0) {
        const mesh = intersects[0].object as THREE.Mesh;
        if (hovered !== mesh) {
          resetHover();
          hovered = mesh;
          (mesh.material as THREE.MeshBasicMaterial).color.set("#67e8f9");
          container!.style.cursor = "pointer";
          renderScene();
        }
      } else if (hovered) {
        resetHover();
        container!.style.cursor = "default";
        renderScene();
      }
    }

    container.addEventListener("pointermove", onPointerMove);

    // ── Responsive resize ────────────────────────────────────────────
    let resizeRAF = 0;
    function onResize() {
      cancelAnimationFrame(resizeRAF);
      resizeRAF = requestAnimationFrame(() => {
        const r = container!.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) return;
        renderer.setSize(r.width, r.height);
        camera.aspect = r.width / r.height;
        camera.updateProjectionMatrix();
        renderScene();
      });
    }
    window.addEventListener("resize", onResize);

    // ── Initial render ───────────────────────────────────────────────
    renderScene();

    // ── Cleanup ──────────────────────────────────────────────────────
    return () => {
      window.removeEventListener("resize", onResize);
      container.removeEventListener("pointermove", onPointerMove);
      controls.removeEventListener("change", renderScene);
      controls.dispose();

      // Dispose all column meshes
      for (const mesh of columns) {
        scene.remove(mesh);
        mesh.geometry.dispose();
        (mesh.material as THREE.MeshBasicMaterial).dispose();
      }

      // Dispose grid
      scene.remove(gridHelper);
      gridHelper.geometry.dispose();
      if (Array.isArray(gridHelper.material)) {
        gridHelper.material.forEach((m) => m.dispose());
      } else {
        gridHelper.material.dispose();
      }

      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      cancelAnimationFrame(resizeRAF);
    };
  }, []);

  // ── Fallback: WebGL not available ─────────────────────────────────
  if (!webglSupported) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-app-panel">
        <span className="text-sm font-medium uppercase tracking-widest text-app-text-muted">
          WebGL required
        </span>
      </div>
    );
  }

  return <div ref={containerRef} className="h-full w-full" />;
}
