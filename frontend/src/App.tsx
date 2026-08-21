/**
 * RECON-MESH Step 12: Full Workspace Assembly
 * ============================================
 * Assembles: ControlHeader, HUDMetricsBar, ReconGraphCanvas + ThreeLaserArcOverlay,
 * LiveAuditTerminal, and InvestigationDrawer into a single AMOLED FinOps workspace.
 */

import { useCallback, useEffect, useState } from 'react';
import { ControlHeader } from './components/ControlHeader';
import { HUDMetricsBar } from './components/HUDMetricsBar';
import { ReconGraphCanvas } from './components/ReconGraphCanvas';
import { InvestigationDrawer } from './components/InvestigationDrawer';
import { LiveAuditTerminal } from './components/LiveAuditTerminal';
import { useReconStream } from './hooks/useReconStream';
import type { ReconciliationCluster } from './types/recon';

export function App() {
  const {
    isConnected,
    isStreaming,
    metrics,
    clusters,
    merkleRoot,
    engineMode,
    startStream,
    stopStream,
    runBatchReconcile,
    fetchHealth,
  } = useReconStream();

  const [selectedCluster, setSelectedCluster] = useState<ReconciliationCluster | null>(null);

  // Trigger initial batch evaluation on mount
  useEffect(() => {
    runBatchReconcile(100);
  }, [runBatchReconcile]);

  // Resolve selected cluster from node ID
  const handleNodeSelect = useCallback(
    (nodeId: string) => {
      // Node IDs are prefixed with 'rzp-', 'bank-', 'erp-'
      const txnId = nodeId.replace(/^(rzp-|bank-|erp-)/, '');
      const found = clusters.find(
        (cl) =>
          cl.razorpay_txns.some((t) => t.id === txnId) ||
          cl.bank_txns.some((t) => t.id === txnId) ||
          cl.erp_txns.some((t) => t.id === txnId)
      );
      setSelectedCluster(found ?? null);
    },
    [clusters]
  );

  const handleCloseDrawer = useCallback(() => setSelectedCluster(null), []);

  return (
    <div className="w-screen h-screen bg-[#000000] text-[#EDEDED] flex flex-col overflow-hidden antialiased select-none">
      {/* Row 1: Control Header (48px) */}
      <ControlHeader
        isConnected={isConnected}
        isStreaming={isStreaming}
        engineMode={engineMode}
        onStartStream={startStream}
        onStopStream={stopStream}
        onRunBatch={runBatchReconcile}
        onRefreshHealth={fetchHealth}
      />

      {/* Row 2: HUD Telemetry Metrics Bar */}
      <HUDMetricsBar metrics={metrics} merkleRoot={merkleRoot} />

      {/* Row 3: Main Graph Canvas (flex-1, fills remaining height) */}
      <div className="flex-1 relative overflow-hidden">
        {/* 3-Column Bipartite DAG + Three.js Laser Arcs */}
        <ReconGraphCanvas
          clusters={clusters}
          onNodeSelect={handleNodeSelect}
        />

        {/* Column Lane Labels (float above graph) */}
        <div className="absolute top-3 left-0 right-0 pointer-events-none z-20 flex px-4">
          {[
            { label: 'RAZORPAY FEEDS', sub: 'Gross • MDR • GST • UTR', color: 'text-[#0C8CE9]' },
            { label: 'BANK STATEMENTS', sub: 'Net Credit • Narration • Value Date', color: 'text-[#00FF66]' },
            { label: 'ERP INVOICES / GL', sub: 'Invoice ID • AR Account • Amount', color: 'text-[#FFB800]' },
          ].map((col) => (
            <div key={col.label} className="flex-1 flex flex-col items-center space-y-0.5 px-4">
              <span className={`text-[10px] font-mono font-semibold tracking-wider ${col.color}`}>
                {col.label}
              </span>
              <span className="text-[9px] font-mono text-[#333333]">{col.sub}</span>
            </div>
          ))}
        </div>

        {/* Empty state overlay if no clusters loaded yet */}
        {clusters.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center z-10 pointer-events-none space-y-3">
            <div className="w-8 h-8 border-2 border-[#00FF66] border-t-transparent rounded-full animate-spin" />
            <p className="text-[12px] font-mono text-[#888888]">
              Loading reconciliation graph...
            </p>
            <p className="text-[10px] font-mono text-[#4E4E4E]">
              Click a batch size in the header to trigger evaluation.
            </p>
          </div>
        )}

        {/* Investigation Drawer (slide-over, absolute right) */}
        {selectedCluster && (
          <InvestigationDrawer
            cluster={selectedCluster}
            merkleRoot={merkleRoot}
            onClose={handleCloseDrawer}
          />
        )}
      </div>

      {/* Row 4: Live Audit Terminal (collapsible, ~180px open) */}
      <LiveAuditTerminal
        clusters={clusters}
        merkleRoot={merkleRoot}
        isConnected={isConnected}
        latencyMs={metrics.latencyMs}
      />
    </div>
  );
}

export default App;
