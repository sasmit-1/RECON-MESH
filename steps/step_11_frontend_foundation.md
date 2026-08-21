# STEP 11: AMOLED Dark Frontend Foundation & Real-Time State Engine (`React/Vite`)

**Model Recommendation:** Lighter Model (e.g., Flash / Claude 3.5 Haiku / GPT-4o-mini)  
**Target Files:**  
- `frontend/package.json`  
- `frontend/vite.config.ts`  
- `frontend/src/App.tsx`  
- `frontend/src/hooks/useReconStream.ts`  
- `frontend/src/components/MetricsBar.tsx`  
- `frontend/src/components/LiveEventTicker.tsx`  
- `frontend/src/components/AgentTerminal.tsx`  
- `frontend/src/components/DispatchModal.tsx`  
**Dependencies:** React 19, Vite, TailwindCSS, `lucide-react`, `clsx`, `tailwind-merge`

---

## 1. Domain Context & UI/UX Design System (Anti-"AI Slop" Precision)

Evaluators reviewing hundreds of hackathon submissions suffer from "Streamlit and generic AI slop fatigue"—messy neon gradients, unreadable glassmorphism bubbles, washed-out text, and giant landing page padding.

RECON-MESH adopts a **High-Density Enterprise FinOps Terminal Aesthetic** inspired by Linear, Bloomberg, Raycast, and Stripe.

```
================================================================================
CRITICAL DESIGN RULES: WHAT TO STRICTLY AVOID ("AI SLOP" ANTI-PATTERNS)
================================================================================
1. NO excessive, blurry neon glows, giant purple/cyan radial gradient blobs, or messy "cyberpunk" halos.
2. NO oversized 3D glassmorphic bubbles, low-contrast washed-out text, or unreadable rounded cards.
3. NO generic marketing landing page fluff (e.g., giant bouncy hero badges, spinning decorative 3D donuts, or huge empty padding).
4. NO non-standard custom scrollbars that glitch on zoom.
5. NO cluttered Bento-grid card overload with random mismatched border radiuses.

================================================================================
THE PRODUCTION FINOPS DESIGN SYSTEM (AMOLED PRECISION)
================================================================================
1. Palette & Surface Depth:
   - True Pitch Black Base: #000000 (100% AMOLED black, not washed-out dark gray).
   - Elevated Card Surfaces: #080808 to #0D0D0D with crisp 1px borders using #181818 or #1F1F1F.
   - Subtle Interactive Hover Borders: #2A2A2A.
   - Typography Colors:
     • Primary Labels & Headings: #EDEDED (crisp white, font-weight 500/600).
     • Secondary / Metadata: #888888 (clear readable neutral gray).
     • Tertiary / Muted Timestamps: #4E4E4E.
   - Semantic Status Indicators (Restrained 10-12px micro-badges with 10% opacity fills):
     • Settled / Match: #00FF66 text with border rgba(0, 255, 102, 0.2) and background rgba(0, 255, 102, 0.05).
     • Exception / Discrepancy: #FF3366 text with border rgba(255, 51, 102, 0.2).
     • Memory Cache Hit: #FFB800 text with border rgba(255, 184, 0, 0.2).
     • Ingesting Stream: #0C8CE9 text.

2. Typography & Numerical Layout:
   - Primary UI Font: Strict sans-serif system stack (Geist, Inter, or system-ui).
   - Numerical Currency & Monospace Data: Use tabular numbers (font-mono / font-variant-numeric: tabular-nums) for every single INR paise value, transaction hash, and UTR. 
   - Never allow layout shift when paise digits tick or increment.

3. Spatial Hierarchy & Density:
   - Dense, scannable, compact UI. Maximum 12px-16px padding on cards.
   - Header HUD: Slim 44px top bar showing status pills (Engine: C++ Native | Mode: Zero-Egress | Merkle: Active) and live throughput metrics.
   - 3-Column 2D Bipartite Board:
     • Column A: Razorpay Captured Feeds (Gross ₹, MDR, GST, UTR).
     • Column B: Core Bank Deposits (Net Credit ₹, Narration, Value Date).
     • Column C: ERP Invoices (Invoice ID, AR Account, Amount ₹).
   - Background WebGL FX: Three.js laser arcs must be razor-sharp 1px bezier lines with subtle bloom, perfectly synced to node coordinates, never obscuring text.

4. Collapsible Developer/Agent Drawer:
   - Minimalist bottom tray styled like a native terminal (#050505).
   - Clean monospace font with syntax-highlighted AST validation tokens and Merkle proof hashes.
```

---

## 2. Throttled Real-Time WebSocket Hook (`frontend/src/hooks/useReconStream.ts`)

### ⚠️ Critical Invariant: High-Frequency WebSocket Throttling
> [!IMPORTANT]
> When transaction events arrive at 10–50 Hz, triggering `setEvents()` on every single message causes React 19 re-render thrashing and frame drops.  
> You **MUST** use an internal mutable buffer (`useRef<StreamEvent[]>([])`) and throttle state flushes to 100ms intervals using `requestAnimationFrame` or `setInterval`.

```typescript
import { useState, useEffect, useRef } from 'react';

export interface ReconMetric {
  precision: number;
  recall: number;
  throughput: number;
  totalSettledPaise: number;
  discrepancyPaise: number;
  merkleRoot: string;
}

export interface StreamEvent {
  id: string;
  source: 'RAZORPAY' | 'BANK' | 'ERP';
  amountPaise: number;
  narration?: string;
  timestamp: string;
  orderId?: string;
  utr?: string;
}

export function useReconStream(wsUrl: string = 'ws://localhost:8000/ws/recon-stream') {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [terminalLogs, setTerminalLogs] = useState<string[]>([]);
  const [metrics, setMetrics] = useState<ReconMetric>({
    precision: 100.0,
    recall: 100.0,
    throughput: 0,
    totalSettledPaise: 0,
    discrepancyPaise: 0,
    merkleRoot: 'SHA-256 INITIALIZED'
  });

  // Internal mutable buffers to prevent UI thrashing
  const eventBufferRef = useRef<StreamEvent[]>([]);
  const logBufferRef = useRef<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    ws.onmessage = (msg) => {
      try {
        const payload = JSON.parse(msg.data);
        if (payload.type === 'NODE_INGESTED') {
          eventBufferRef.current.unshift(payload.data);
        } else if (payload.type === 'METRICS_UPDATE') {
          setMetrics(payload.data);
        } else if (payload.type === 'AGENT_LOG') {
          logBufferRef.current.push(payload.data);
        }
      } catch (e) {
        console.error('WS Parse Error', e);
      }
    };

    // 100ms throttled state flush to keep main thread at 60 FPS
    const intervalId = setInterval(() => {
      if (eventBufferRef.current.length > 0) {
        const newBatch = eventBufferRef.current.slice(0, 50);
        eventBufferRef.current = [];
        setEvents((prev) => [...newBatch, ...prev].slice(0, 100));
      }
      if (logBufferRef.current.length > 0) {
        const newLogs = logBufferRef.current.slice(0, 20);
        logBufferRef.current = [];
        setTerminalLogs((prev) => [...prev, ...newLogs].slice(-100));
      }
    }, 100);

    return () => {
      clearInterval(intervalId);
      ws.close();
    };
  }, [wsUrl]);

  return { isConnected, events, terminalLogs, metrics };
}
```

---

## 3. High-Density Slim Header HUD (`frontend/src/components/MetricsBar.tsx`)

```tsx
import React from 'react';
import { ShieldCheck, Cpu, Database, Activity } from 'lucide-react';
import { ReconMetric } from '../hooks/useReconStream';

interface MetricsBarProps {
  metrics: ReconMetric;
  nativeMatcher: boolean;
  edgeInference: boolean;
}

export const MetricsBar: React.FC<MetricsBarProps> = ({ metrics, nativeMatcher, edgeInference }) => {
  return (
    <header className="h-[44px] bg-[#080808] border-b border-[#181818] px-4 flex items-center justify-between select-none">
      {/* Brand & Engine Status Pills */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 rounded-full bg-[#00FF66] animate-pulse" />
          <span className="text-[13px] font-semibold tracking-wider text-[#EDEDED] uppercase">RECON-MESH</span>
        </div>
        <div className="h-3 w-[1px] bg-[#222222]" />
        
        {/* Status Pills */}
        <span className="px-2 py-0.5 text-[11px] font-mono rounded bg-[#111111] border border-[#222222] text-[#888888] flex items-center space-x-1">
          <Cpu className="w-3 h-3 text-[#0C8CE9]" />
          <span>{nativeMatcher ? 'C++ NATIVE' : 'PYTHON NUMBA'}</span>
        </span>
        <span className="px-2 py-0.5 text-[11px] font-mono rounded bg-[#111111] border border-[#222222] text-[#888888] flex items-center space-x-1">
          <ShieldCheck className="w-3 h-3 text-[#00FF66]" />
          <span>{edgeInference ? '0-EGRESS EDGE' : 'CLOUD EVAL'}</span>
        </span>
      </div>

      {/* Numerical Data HUD (Tabular Numbers, Zero Layout Shift) */}
      <div className="flex items-center space-x-6 text-[12px] font-mono">
        <div className="flex items-center space-x-1.5">
          <span className="text-[#4E4E4E]">PRECISION:</span>
          <span className="text-[#00FF66] tabular-nums font-semibold">{metrics.precision.toFixed(2)}%</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <span className="text-[#4E4E4E]">RECALL:</span>
          <span className="text-[#00FF66] tabular-nums font-semibold">{metrics.recall.toFixed(2)}%</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <span className="text-[#4E4E4E]">SETTLED:</span>
          <span className="text-[#EDEDED] tabular-nums font-semibold">₹{(metrics.totalSettledPaise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <span className="text-[#4E4E4E]">DISCREPANCY:</span>
          <span className="text-[#00FF66] tabular-nums font-semibold">₹{(metrics.discrepancyPaise / 100).toFixed(2)}</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <span className="text-[#4E4E4E]">MERKLE:</span>
          <span className="text-[#888888] tabular-nums">{metrics.merkleRoot.slice(0, 10)}...</span>
        </div>
      </div>
    </header>
  );
};
```

---

## 4. Standalone Verification Command
```bash
cd frontend && npm run build
```
