/**
 * RECON-MESH Step 12: Three.js WebGL Laser Arc Overlay
 * =====================================================
 * Transparent hardware-accelerated WebGL canvas positioned behind React Flow.
 * Renders razor-sharp 1px glowing green bezier laser arcs between matched node
 * coordinates, synchronized with React Flow's pan/zoom viewport transform.
 */

import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export interface LaserLine {
  id: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  color?: string;
  progress?: number;
}

interface ThreeLaserArcOverlayProps {
  lasers: LaserLine[];
  viewport: { x: number; y: number; zoom: number };
}

export const ThreeLaserArcOverlay: React.FC<ThreeLaserArcOverlayProps> = ({ lasers, viewport }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.OrthographicCamera | null>(null);
  const lineGroupRef = useRef<THREE.Group | null>(null);
  const frameIdRef = useRef<number>(0);

  // Initialize Three.js scene, orthographic camera, and WebGL renderer
  useEffect(() => {
    if (!mountRef.current) return;
    const el = mountRef.current;
    const width = el.clientWidth || window.innerWidth;
    const height = el.clientHeight || window.innerHeight;

    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const camera = new THREE.OrthographicCamera(
      -width / 2, width / 2,
      height / 2, -height / 2,
      1, 1000
    );
    camera.position.z = 10;
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    el.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const lineGroup = new THREE.Group();
    scene.add(lineGroup);
    lineGroupRef.current = lineGroup;

    const animate = () => {
      frameIdRef.current = requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!el || !rendererRef.current || !cameraRef.current) return;
      const w = el.clientWidth;
      const h = el.clientHeight;
      rendererRef.current.setSize(w, h);
      const cam = cameraRef.current;
      cam.left = -w / 2;
      cam.right = w / 2;
      cam.top = h / 2;
      cam.bottom = -h / 2;
      cam.updateProjectionMatrix();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(frameIdRef.current);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      if (el.contains(renderer.domElement)) {
        el.removeChild(renderer.domElement);
      }
    };
  }, []);

  // Sync Three.js orthographic camera with React Flow's viewport transform
  // React Flow viewport: { x: pan_x (px from left), y: pan_y (px from top), zoom }
  // Three.js orthographic camera: (0,0) = screen center, y-up
  // World position of camera center: ((w/2 - vp.x) / vp.zoom,  (vp.y - h/2) / vp.zoom)
  useEffect(() => {
    if (!cameraRef.current || !mountRef.current) return;
    const el = mountRef.current;
    const w = el.clientWidth || window.innerWidth;
    const h = el.clientHeight || window.innerHeight;
    const cam = cameraRef.current;

    // Apply zoom by setting the orthographic camera's zoom factor
    cam.zoom = viewport.zoom;
    // Pan: translate camera so that the Three.js origin (0,0) maps to React Flow (0,0)
    // RF (0,0) renders at screen pixel (viewport.x, viewport.y)
    // In camera world-space (centre=origin): RF(0,0) is at (-w/2 + viewport.x, h/2 - viewport.y)
    // Camera position is offset from that by 0, so camera.position = negation
    cam.position.x = (w / 2 - viewport.x) / viewport.zoom;
    cam.position.y = -(h / 2 - viewport.y) / viewport.zoom;
    cam.updateProjectionMatrix();
  }, [viewport]);

  // Rebuild laser arc geometry whenever laser connections change
  useEffect(() => {
    if (!lineGroupRef.current) return;
    const group = lineGroupRef.current;

    // Dispose and remove all existing line objects
    while (group.children.length > 0) {
      const obj = group.children[0] as THREE.Line;
      obj.geometry.dispose();
      const mat = obj.material;
      if (Array.isArray(mat)) {
        mat.forEach((m) => m.dispose());
      } else {
        (mat as THREE.Material).dispose();
      }
      group.remove(obj);
    }

    // Draw one cubic bezier arc per laser connection
    lasers.forEach((laser) => {
      const p0 = new THREE.Vector3(laser.sourceX, -laser.sourceY, 0);
      const p3 = new THREE.Vector3(laser.targetX, -laser.targetY, 0);
      const midX = (p0.x + p3.x) / 2;
      const cp1 = new THREE.Vector3(midX, p0.y, 0);
      const cp2 = new THREE.Vector3(midX, p3.y, 0);

      const curve = new THREE.CubicBezierCurve3(p0, cp1, cp2, p3);
      const points = curve.getPoints(16);
      const geometry = new THREE.BufferGeometry().setFromPoints(points);

      const hexColor = laser.color ? parseInt(laser.color.replace('#', ''), 16) : 0x00ff66;
      const material = new THREE.LineBasicMaterial({
        color: hexColor,
        transparent: true,
        opacity: 0.45,
        linewidth: 1,
      });

      const line = new THREE.Line(geometry, material);
      group.add(line);
    });
  }, [lasers]);

  return <div ref={mountRef} className="absolute inset-0 w-full h-full pointer-events-none z-0" />;
};
