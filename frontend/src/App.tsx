/**
 * RECON-MESH: Full Workspace Assembly
 * =====================================
 * Razorpay-style clean professional layout.
 * Row 1 (52px):    ControlHeader
 * Row 2 (auto):    HUDMetricsBar
 * Row 3 (flex-1):  Column headers + ReconGraphCanvas
 * Row 4 (36-160px):LiveAuditTerminal (collapsible)
 * Overlay:         InvestigationDrawer (fixed slide-over)
 */

import { useCallback, useEffect, useState } from 'react';
import { ControlHeader }      from './components/ControlHeader';
import { HUDMetricsBar }      from './components/HUDMetricsBar';
import { ReconGraphCanvas }   from './components/ReconGraphCanvas';
import { InvestigationDrawer } from './components/InvestigationDrawer';
import { LiveAuditTerminal }  from './components/LiveAuditTerminal';
import { useReconStream }     from './hooks/useReconStream';
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
    <div className="w-screen h-screen bg-[#F4F6FA] text-[#111827] flex flex-col overflow-hidden select-none">

      {/* Row 1: Control Header */}
      <ControlHeader
        isConnected={isConnected}
        isStreaming={isStreaming}
        engineMode={engineMode}
        onStartStream={startStream}
        onStopStream={stopStream}
        onRunBatch={runBatchReconcile}
        onRefreshHealth={fetchHealth}
      />

      {/* Row 2: HUD Metrics Bar */}
      <HUDMetricsBar metrics={metrics} merkleRoot={merkleRoot} />

      {/* Row 3: Graph area */}
      <div className="relative flex-1 w-full min-h-0 overflow-hidden">

        {/* Column lane header strip */}
        <div className="absolute top-0 left-0 right-0 z-20 flex h-8 bg-white border-b border-[#E5E7EB] pointer-events-none">
          {[
            { label: 'Razorpay Feeds',   sub: 'Gross · MDR · GST · UTR',          border: 'border-r border-[#E5E7EB]', labelColor: 'text-[#2D65F8]' },
            { label: 'Bank Statements',  sub: 'Net Credit · Narration · Date',     border: 'border-r border-[#E5E7EB]', labelColor: 'text-[#374151]' },
            { label: 'ERP / GL Ledger', sub: 'Invoice · AR Account · Amount',     border: '',                          labelColor: 'text-[#374151]' },
          ].map((col) => (
            <div
              key={col.label}
              className={`flex-1 flex flex-col items-center justify-center ${col.border}`}
            >
              <span className={`text-[10px] font-semibold tracking-wide ${col.labelColor}`}>
                {col.label}
              </span>
              <span className="text-[9px] text-[#9CA3AF]">{col.sub}</span>
            </div>
          ))}
        </div>

        {/* React Flow canvas */}
        <div className="absolute inset-0 top-8">
          <ReconGraphCanvas clusters={clusters} onNodeSelect={handleNodeSelect} />
        </div>

        {/* Empty state */}
        {clusters.length === 0 && (
          <div className="absolute inset-0 top-8 flex flex-col items-center justify-center z-10 pointer-events-none gap-3">
            <div className="w-8 h-8 border-2 border-[#2D65F8] border-t-transparent rounded-full animate-spin" />
            <p className="text-[12px] text-[#9CA3AF]">
              Run a batch to start reconciliation — ⚡ 100 / 500 / 1,000
            </p>
          </div>
        )}
      </div>

      {/* Row 4: Audit terminal */}
      <LiveAuditTerminal
        clusters={clusters}
        merkleRoot={merkleRoot}
        isConnected={isConnected}
        latencyMs={metrics.latencyMs}
      />

      {/* Overlay: Investigation drawer */}
      {selectedCluster && (
        <InvestigationDrawer
          cluster={selectedCluster}
          merkleRoot={merkleRoot}
          onClose={handleCloseDrawer}
        />
      )}
    </div>
  );
}

export default App;
