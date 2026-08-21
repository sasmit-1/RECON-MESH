# STEP 12: High-Density 2D Bipartite Board + Synced Three.js Laser Canvas (`GraphCanvas.tsx`)

**Model Recommendation:** Heavier Model (e.g., Sonnet 3.7 / Gemini 1.5 Pro / GPT-4o)  
**Target Files:**  
- `frontend/src/components/GraphCanvas.tsx`  
- `frontend/src/components/LaserBackgroundCanvas.tsx`  
- `frontend/src/components/CustomTransactionNode.tsx`  
**Dependencies:** React 19, `@xyflow/react`, `three`, `@types/three`, `lucide-react`

---

## 1. Domain Context & Visual Architecture

FinOps operators need to see how hundreds of disparate transactions match across 3 streams without getting dizzy from 3D distortion or distracted by blurry neon AI slop.

RECON-MESH uses a **2-Layer Coordinated Viewport Architecture**:
1. **Interactive 2D Board Layer (`@xyflow/react`)**: 3 clean columnar lanes displaying Razorpay Orders, Bank Statements, and ERP Invoices with crisp text, tabular numbers, and micro-badges.
2. **Hardware-Accelerated WebGL Background (`three`)**: Dedicated Three.js canvas positioned behind React Flow that renders razor-sharp 1px glowing green bezier laser arcs between matching nodes.

```
┌────────────────────────────────────────────────────────────────────────┐
│ REACT FLOW 2D VIEWPORT (Captures Pan & Zoom: { x, y, zoom })           │
│                                                                        │
│  COLUMN A: Razorpay        COLUMN B: Bank            COLUMN C: ERP     │
│  ┌──────────────────┐      ┌──────────────────┐      ┌───────────────┐ │
│  │ pay_9876543210   │      │ bnk_stmt_001     │      │ INV-2026-001  │ │
│  │ ₹1,00,000.00     │────┐ │ ₹97,640.00       │ ┌────│ ₹1,00,000.00  │ │
│  │ MDR: ₹2,000      │    │ │ UTR: 9876543210  │ │    │ AR: Razorpay  │ │
│  │ GST: ₹360        │    │ └──────────────────┘ │    └───────────────┘ │
│  └──────────────────┘    │           ▲          │                      │
│                          └───────────┼──────────┘                      │
│                           1px Razor Sharp Green Laser                  │
├────────────────────────────────────────────────────────────────────────┤
│ THREE.JS WEBGL OVERLAY (Camera Synced: position & zoom updated live)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Canvas Coordinate Synchronization

### ⚠️ Critical Invariant: WebGL Coordinate Synchronization
> [!IMPORTANT]
> When the user pans or zooms the React Flow canvas, `@xyflow/react` updates its internal viewport transform.  
> If the Three.js camera is static, the laser arcs will drift away from the transaction cards during interaction.  
> You **MUST** capture `const { x, y, zoom } = useViewport()` in React Flow, pass it down to `LaserBackgroundCanvas`, and update the Three.js camera in the render loop:
> ```typescript
> camera.position.set(-x / zoom, y / zoom, 10);
> camera.zoom = zoom;
> camera.updateProjectionMatrix();
> ```

---

## 3. Implementation Details

### A. Viewport-Synced Three.js Laser Canvas (`frontend/src/components/LaserBackgroundCanvas.tsx`)

```typescript
import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export interface LaserLine {
  id: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  color?: string; // default #00FF66
  progress: number; // 0.0 to 1.0 animation
}

interface LaserCanvasProps {
  lasers: LaserLine[];
  viewport: { x: number; y: number; zoom: number };
}

export const LaserBackgroundCanvas: React.FC<LaserCanvasProps> = ({ lasers, viewport }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.OrthographicCamera | null>(null);
  const lineGroupRef = useRef<THREE.Group | null>(null);

  // Initialize WebGL Scene
  useEffect(() => {
    if (!mountRef.current) return;
    const width = mountRef.current.clientWidth;
    const height = mountRef.current.clientHeight;

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
    mountRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const lineGroup = new THREE.Group();
    scene.add(lineGroup);
    lineGroupRef.current = lineGroup;

    let frameId: number;
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!mountRef.current || !rendererRef.current || !cameraRef.current) return;
      const w = mountRef.current.clientWidth;
      const h = mountRef.current.clientHeight;
      rendererRef.current.setSize(w, h);
      cameraRef.current.left = -w / 2;
      cameraRef.current.right = w / 2;
      cameraRef.current.top = h / 2;
      cameraRef.current.bottom = -h / 2;
      cameraRef.current.updateProjectionMatrix();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      mountRef.current?.removeChild(renderer.domElement);
    };
  }, []);

  // Synchronize Camera with React Flow Viewport Transform
  useEffect(() => {
    if (!cameraRef.current || !mountRef.current) return;
    const width = mountRef.current.clientWidth;
    const height = mountRef.current.clientHeight;

    const camera = cameraRef.current;
    camera.zoom = viewport.zoom;
    camera.position.x = -(viewport.x - width / 2) / viewport.zoom;
    camera.position.y = (viewport.y - height / 2) / viewport.zoom;
    camera.updateProjectionMatrix();
  }, [viewport]);

  // Update Dynamic Laser Arcs
  useEffect(() => {
    if (!lineGroupRef.current) return;
    const group = lineGroupRef.current;
    
    // Clear old lines
    while (group.children.length > 0) {
      const obj = group.children[0] as THREE.Line;
      obj.geometry.dispose();
      if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
      else obj.material.dispose();
      group.remove(obj);
    }

    // Draw crisp 1px Bezier Laser Arcs
    lasers.forEach((laser) => {
      const p0 = new THREE.Vector3(laser.sourceX, -laser.sourceY, 0);
      const p3 = new THREE.Vector3(laser.targetX, -laser.targetY, 0);
      const midX = (p0.x + p3.x) / 2;
      const p1 = new THREE.Vector3(midX, p0.y, 0);
      const p2 = new THREE.Vector3(midX, p3.y, 0);

      const curve = new THREE.CubicBezierCurve3(p0, p1, p2, p3);
      const points = curve.getPoints(30);
      const geometry = new THREE.BufferGeometry().setFromPoints(points);

      const material = new THREE.LineBasicMaterial({
        color: laser.color || 0x00FF66,
        transparent: true,
        opacity: 0.85,
        linewidth: 1
      });

      const line = new THREE.Line(geometry, material);
      group.add(line);
    });
  }, [lasers]);

  return <div ref={mountRef} className="absolute inset-0 pointer-events-none z-0" />;
};
```

### B. High-Density React Flow Canvas Container (`frontend/src/components/GraphCanvas.tsx`)

```tsx
import React, { useMemo } from 'react';
import { ReactFlow, Background, Controls, Node, Edge, useViewport, ReactFlowProvider } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { LaserBackgroundCanvas, LaserLine } from './LaserBackgroundCanvas';

interface GraphCanvasProps {
  nodes: Node[];
  edges: Edge[];
  lasers?: LaserLine[];
  onNodeClick?: (nodeId: string) => void;
}

const FlowViewportConnector: React.FC<{ lasers: LaserLine[] }> = ({ lasers }) => {
  const { x, y, zoom } = useViewport();
  return <LaserBackgroundCanvas lasers={lasers} viewport={{ x, y, zoom }} />;
};

export const GraphCanvas: React.FC<GraphCanvasProps> = ({ nodes, edges, lasers = [], onNodeClick }) => {
  return (
    <div className="relative w-full h-full bg-[#000000] overflow-hidden select-none">
      <ReactFlowProvider>
        {/* Layer 0: Synced WebGL Laser Overlay */}
        <FlowViewportConnector lasers={lasers} />

        {/* Layer 1: Crisp 2D Interactive Node Viewport */}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodeClick={(_, node) => onNodeClick && onNodeClick(node.id)}
          fitView
          minZoom={0.2}
          maxZoom={2.0}
          className="z-10"
        >
          <Background color="#121212" gap={20} size={1} />
          <Controls className="!bg-[#080808] !border !border-[#181818] !fill-[#888888] [&>button]:!border-b-[#181818]" />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
};
```

---

## 4. Standalone Verification Command
```bash
cd frontend && npm run build
```
