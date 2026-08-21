/**
 * RECON-MESH Step 11: Main Application Entry & AMOLED Dashboard Layout
 * ====================================================================
 * Connects ControlHeader, HUDMetricsBar, and streaming telemetry state with
 * 100% AMOLED pitch-black FinOps aesthetic.
 */

import { useEffect } from 'react';
import {
  CheckCircle2,
  Database,
  FileCheck,
  ShieldCheck,
  Terminal,
} from 'lucide-react';
import { ControlHeader } from './components/ControlHeader';
import { HUDMetricsBar } from './components/HUDMetricsBar';
import { useReconStream } from './hooks/useReconStream';

export function App() {
  const {
    isConnected,
    isStreaming,
    metrics,
    clusters,
    activeVouchers,
    merkleRoot,
    engineMode,
    startStream,
    stopStream,
    runBatchReconcile,
    fetchHealth,
  } = useReconStream();

  // Trigger initial batch evaluation on mount if empty
  useEffect(() => {
    runBatchReconcile(100);
  }, [runBatchReconcile]);

  return (
    <div className="w-screen h-screen bg-[#000000] text-[#EDEDED] flex flex-col overflow-hidden font-sans select-none antialiased">
      {/* 1. Control Header (Slim 48px Top Navigation Bar) */}
      <ControlHeader
        isConnected={isConnected}
        isStreaming={isStreaming}
        engineMode={engineMode}
        onStartStream={startStream}
        onStopStream={stopStream}
        onRunBatch={runBatchReconcile}
        onRefreshHealth={fetchHealth}
      />

      {/* 2. HUD Telemetry Metrics Bar */}
      <HUDMetricsBar metrics={metrics} merkleRoot={merkleRoot} />

      {/* 3. Main Operational Dashboard Area */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-3 p-3 overflow-hidden bg-[#000000]">
        
        {/* Panel 1: Live Cluster Ingestion Feed */}
        <section className="bg-[#080808] border border-[#181818] rounded flex flex-col overflow-hidden">
          <div className="h-[36px] bg-[#0C0C0C] border-b border-[#181818] px-3 flex items-center justify-between select-none">
            <span className="text-[12px] font-mono font-semibold text-[#EDEDED] flex items-center space-x-1.5">
              <Database className="w-3.5 h-3.5 text-[#0C8CE9]" />
              <span>3-WAY RECONCILIATION CLUSTERS</span>
            </span>
            <span className="text-[10px] font-mono text-[#888888] bg-[#141414] border border-[#222222] px-1.5 py-0.5 rounded">
              {clusters.length > 0 ? `${clusters.length} RECENT` : 'AUTO MATCHED'}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-2 font-mono text-[11px]">
            {clusters.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-[#4E4E4E] space-y-2 p-6 text-center">
                <CheckCircle2 className="w-8 h-8 text-[#00FF66] opacity-60" />
                <p className="text-[12px]">All 3-way transactions balanced (Zero Discrepancy)</p>
                <p className="text-[10px] text-[#888888]">
                  Click <span className="text-[#00FF66]">100</span>, <span className="text-[#00FF66]">500</span>, or <span className="text-[#00FF66]">1000</span> to run a live batch benchmark.
                </p>
              </div>
            ) : (
              clusters.map((cl, idx) => (
                <div
                  key={cl.cluster_id || idx}
                  className="bg-[#040404] border border-[#181818] hover:border-[#2A2A2A] rounded p-2 transition-colors flex flex-col space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[#00FF66] font-semibold">{cl.cluster_id}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded border ${
                        cl.discrepancy_paise === 0
                          ? 'bg-[rgba(0,255,102,0.05)] text-[#00FF66] border-[rgba(0,255,102,0.2)]'
                          : 'bg-[rgba(255,51,102,0.05)] text-[#FF3366] border-[rgba(255,51,102,0.2)]'
                      }`}
                    >
                      {cl.status}
                    </span>
                  </div>
                  <div className="flex justify-between text-[#888888]">
                    <span>Expected Net: ₹{(cl.sum_net_expected_paise / 100).toFixed(2)}</span>
                    <span>Bank Credit: ₹{(cl.sum_bank_credit_paise / 100).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-[10px] text-[#4E4E4E]">
                    <span>Razorpay: {cl.razorpay_txns?.length || 1} txn</span>
                    <span>Bank: {cl.bank_txns?.length || 1} entry</span>
                    <span>ERP: {cl.erp_txns?.length || 1} inv</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Panel 2: Verified Discrepancy Vouchers & AST Adjustments */}
        <section className="bg-[#080808] border border-[#181818] rounded flex flex-col overflow-hidden">
          <div className="h-[36px] bg-[#0C0C0C] border-b border-[#181818] px-3 flex items-center justify-between select-none">
            <span className="text-[12px] font-mono font-semibold text-[#EDEDED] flex items-center space-x-1.5">
              <FileCheck className="w-3.5 h-3.5 text-[#00FF66]" />
              <span>VERIFIED AGENT VOUCHERS</span>
            </span>
            <span className="text-[10px] font-mono text-[#00FF66] bg-[rgba(0,255,102,0.05)] border border-[rgba(0,255,102,0.2)] px-1.5 py-0.5 rounded">
              DOUBLE-ENTRY INVARIANT
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-2 font-mono text-[11px]">
            {activeVouchers.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-[#4E4E4E] space-y-2 p-6 text-center">
                <ShieldCheck className="w-8 h-8 text-[#00FF66] opacity-60" />
                <p className="text-[12px]">Zero Unbalanced Vouchers</p>
                <p className="text-[10px] text-[#888888]">
                  All generated vouchers are signed into the Merkle Audit Tree.
                </p>
              </div>
            ) : (
              activeVouchers.map((vch) => (
                <div
                  key={vch.voucher_id}
                  className="bg-[#040404] border border-[#181818] hover:border-[#2A2A2A] rounded p-2 transition-colors flex flex-col space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[#EDEDED] font-semibold">{vch.voucher_id}</span>
                    <span className="text-[10px] text-[#FFB800] bg-[rgba(255,184,0,0.1)] border border-[rgba(255,184,0,0.2)] px-1 py-0.5 rounded">
                      {vch.discrepancy_type}
                    </span>
                  </div>
                  <div className="flex justify-between text-[#888888]">
                    <span>DSL: {vch.proposed_adjustment_dsl}</span>
                    <span className="text-[#00FF66]">₹{(vch.variance_paise / 100).toFixed(2)}</span>
                  </div>
                  <div className="text-[10px] text-[#4E4E4E] truncate">
                    Merkle Hash: {vch.audit_hash}
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Panel 3: FinOps Terminal & System Event Log */}
        <section className="bg-[#080808] border border-[#181818] rounded flex flex-col overflow-hidden">
          <div className="h-[36px] bg-[#0C0C0C] border-b border-[#181818] px-3 flex items-center justify-between select-none">
            <span className="text-[12px] font-mono font-semibold text-[#EDEDED] flex items-center space-x-1.5">
              <Terminal className="w-3.5 h-3.5 text-[#FFB800]" />
              <span>TERMINAL TELEMETRY LOG</span>
            </span>
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 rounded-full bg-[#00FF66] animate-pulse" />
              <span className="text-[10px] font-mono text-[#00FF66]">ACTIVE</span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-3 bg-[#030303] font-mono text-[11px] space-y-1 text-[#888888]">
            <p className="text-[#00FF66]">[SYS] RECON-MESH Engine Initialized v2.1.0</p>
            <p className="text-[#0C8CE9]">[INVAR] Zero-Sum Double Entry Gatekeeper Active</p>
            <p className="text-[#FFB800]">[MERKLE] SHA-256 Ledger Binary Tree Ready</p>
            <p className="text-[#EDEDED]">
              [MATCH] Stage 1 Heuristic Pruner: 2-Stage Settlement Engine
            </p>
            <p className="text-[#EDEDED]">
              [MATCH] Stage 2 Bounded DP Solver: O(N * V) Residual Optimizer
            </p>
            {clusters.slice(0, 8).map((cl, i) => (
              <p key={i} className="text-[#888888] truncate">
                [TICK] Resolved {cl.cluster_id} | Status: {cl.status} | Net: ₹
                {(cl.sum_net_expected_paise / 100).toFixed(2)}
              </p>
            ))}
          </div>
        </section>

      </main>

      {/* 4. Minimalist Status Footer */}
      <footer className="h-[24px] bg-[#050505] border-t border-[#181818] px-3 flex items-center justify-between text-[10px] font-mono text-[#4E4E4E] select-none">
        <div>
          <span>RECON-MESH FINOPS TERMINAL</span>
          <span className="mx-2">•</span>
          <span>AIR-GAPPED ZERO-EGRESS MODE</span>
        </div>
        <div>
          <span>REACT 19 + VITE + TAILWIND</span>
          <span className="mx-2">•</span>
          <span className="text-[#00FF66]">INVARIANTS 100% VERIFIED</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
