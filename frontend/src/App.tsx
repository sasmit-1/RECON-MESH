/**
 * RECON-MESH: Full Workspace Assembly
 * =====================================
 * Layout:
 *   Row 1 (fixed 48px): ControlHeader
 *   Row 2 (auto):       HUDMetricsBar
 *   Row 3 (flex-1):     ReconGraphCanvas + ThreeLaserArcOverlay (fills remaining space)
 *   Row 4 (fixed 40px): LiveAuditTerminal (collapsible to 160px open)
 *   Overlay:            InvestigationDrawer (slide-over, right)
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

  useEffect(() => {
    runBatchReconcile(100);
  }, [runBatchReconcile]);

  const handleNodeSelect = useCallback(
    (nodeId: string) => {
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
    <div className="w-screen h-screen bg-black text-[#EDEDED] flex flex-col overflow-hidden font-mono select-none">
      {/* Row 1: Control Header — fixed height */}
      <ControlHeader
        isConnected={isConnected}
        isStreaming={isStreaming}
        engineMode={engineMode}
        onStartStream={startStream}
        onStopStream={stopStream}
        onRunBatch={runBatchReconcile}
        onRefreshHealth={fetchHealth}
      />

      {/* Row 2: HUD Metrics Bar — auto height */}
      <HUDMetricsBar metrics={metrics} merkleRoot={merkleRoot} />

      {/* Row 3: Main Graph Canvas — fills all remaining vertical space */}
      <div className="relative flex-1 w-full min-h-0 overflow-hidden bg-black">
        {/* Column lane labels floating above graph */}
        <div className="absolute top-2 left-0 right-0 pointer-events-none z-20 flex">
          {[
            { label: 'RAZORPAY FEEDS', sub: 'Gross · MDR · GST · UTR', color: 'text-[#0C8CE9]' },
            { label: 'BANK STATEMENTS', sub: 'Net Credit · Narration · Date', color: 'text-[#00FF66]' },
            { label: 'ERP / GL LEDGER', sub: 'Invoice · AR Account · Amount', color: 'text-[#FFB800]' },
          ].map((col) => (
            <div key={col.label} className="flex-1 flex flex-col items-center gap-0.5">
              <span className={`text-[9px] font-mono font-semibold tracking-widest uppercase ${col.color}`}>
                {col.label}
              </span>
              <span className="text-[8px] font-mono text-[#2a2a2a]">{col.sub}</span>
            </div>
          ))}
        </div>

        {/* React Flow graph canvas — absolutely fills the container */}
        <div className="absolute inset-0 w-full h-full">
          <ReconGraphCanvas clusters={clusters} onNodeSelect={handleNodeSelect} />
        </div>

        {/* Empty state shown before first batch */}
        {clusters.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center z-10 pointer-events-none gap-3">
            <div className="w-7 h-7 border-2 border-[#00FF66] border-t-transparent rounded-full animate-spin" />
            <p className="text-[11px] font-mono text-[#555555]">
              Awaiting reconciliation batch — click 100 / 500 / 1000 above
            </p>
          </div>
        )}

        {/* Investigation slide-over drawer (right side) */}
        {selectedCluster && (
          <InvestigationDrawer
            cluster={selectedCluster}
            merkleRoot={merkleRoot}
            onClose={handleCloseDrawer}
          />
        )}
      </div>

      {/* Row 4: Live Audit Terminal — collapsible bottom dock */}
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
