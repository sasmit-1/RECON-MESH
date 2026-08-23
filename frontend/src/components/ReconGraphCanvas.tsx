/**
 * RECON-MESH Step 12: Interactive 3-Column Bipartite DAG Canvas
 * =============================================================
 * Renders a high-density React Flow bipartite board with 3 columnar lanes:
 *   Column A: Razorpay Captured Feeds (Gross ₹, MDR, GST, UTR)
 *   Column B: Core Bank Deposits (Net Credit ₹, Narration, Value Date)
 *   Column C: ERP Invoices & GL Ledgers (Invoice ID, AR, Amount ₹)
 *
 * Node IDs are scoped per cluster to prevent React Flow duplicate-ID collisions.
 * Column positions are computed from actual container width to align with lane headers.
 */

import React, { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import {
  Background,
  Controls,
  type Edge,
  type Node,
  type NodeTypes,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  useViewport,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { ReconciliationCluster } from '../types/recon';
import { CustomTransactionNode, type TransactionNodeData } from './CustomTransactionNode';

// Cast to NodeTypes to satisfy @xyflow/react strict signature
const NODE_TYPES: NodeTypes = {
  transaction: CustomTransactionNode as NodeTypes[string],
};

// Fractional offsets within each 1/3-width column
// Node card is 240px wide. Each column occupies 33.33% of container.
// We position nodes at a fixed pixel offset from each column's left edge.
const COL_FRACTIONS = { RAZORPAY: 0.02, BANK: 0.355, ERP: 0.69 };
const ROW_HEIGHT = 175;
const MAX_VISIBLE_CLUSTERS = 80;

interface ReconGraphCanvasProps {
  clusters: ReconciliationCluster[];
  onNodeSelect: (clusterScopedNodeId: string) => void;
}

// Inner component inside ReactFlowProvider — calls useViewport() and useReactFlow()
const FlowInner: React.FC<{
  nodes: Node<TransactionNodeData>[];
  edges: Edge[];
  onNodeSelect: (id: string) => void;
}> = ({ nodes, edges, onNodeSelect }) => {
  useViewport(); // keep subscribed so Three.js overlay syncs if re-added later
  const { setViewport } = useReactFlow();
  const initializedRef = useRef<boolean>(false);

  const resetToTop = useCallback(() => {
    setViewport({ x: 20, y: 20, zoom: 0.9 }, { duration: 250 });
  }, [setViewport]);

  // Lock viewport to readable zoom on first node load, and re-lock whenever
  // nodes are cleared and re-populated (e.g. after stream start).
  useEffect(() => {
    if (nodes.length === 0) {
      // Reset the initialized flag so we re-lock viewport on the next batch
      initializedRef.current = false;
      return;
    }
    if (!initializedRef.current) {
      initializedRef.current = true;
      const timer = setTimeout(() => {
        setViewport({ x: 20, y: 20, zoom: 0.9 }, { duration: 0 });
      }, 40);
      return () => clearTimeout(timer);
    }
  }, [nodes.length, setViewport]);

  return (
    <div className="relative w-full h-full bg-[#F4F6FA] overflow-hidden">
      {/* Floating reset button */}
      <button
        onClick={resetToTop}
        title="Reset view to top"
        className="absolute top-3 right-4 z-20 bg-white/90 backdrop-blur-sm border border-[#E5E7EB] hover:bg-white text-[#374151] hover:text-[#2D65F8] text-[11px] font-medium px-2.5 py-1 rounded-md shadow-sm transition-all flex items-center gap-1.5 cursor-pointer"
      >
        <span>↑ Reset to Top</span>
      </button>

      {/* React Flow Canvas — SVG edges provide the connection lines */}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        onNodeClick={(_, node) => onNodeSelect(node.id)}
        defaultViewport={{ x: 20, y: 20, zoom: 0.9 }}
        minZoom={0.4}
        maxZoom={1.5}
        panOnScroll={true}
        zoomOnScroll={false}
        zoomOnPinch={true}
        panOnDrag={true}
        className="z-10"
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#E5E7EB" gap={24} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
};

export const ReconGraphCanvas: React.FC<ReconGraphCanvasProps> = ({ clusters, onNodeSelect }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(1200);
  // Stable ref for onNodeSelect so it never appears in useMemo deps.
  // Without this, every cluster update recreates handleNodeSelect (because it
  // closes over `clusters`), which invalidates the memo and rebuilds all
  // React Flow nodes — causing the flicker/disappear glitch.
  const onNodeSelectRef = useRef(onNodeSelect);
  useEffect(() => { onNodeSelectRef.current = onNodeSelect; }, [onNodeSelect]);

  // Measure actual rendered container width so columns align with flex-1 lane headers
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w && w > 100) setContainerWidth(w);
    });
    obs.observe(el);
    setContainerWidth(el.clientWidth || 1200);
    return () => obs.disconnect();
  }, []);

  const { nodes, edges } = useMemo(() => {
    const nodes: Node<TransactionNodeData>[] = [];
    const edges: Edge[] = [];

    // Compute column X in React Flow world coords from actual container pixel width
    const colX = {
      RAZORPAY: Math.round(containerWidth * COL_FRACTIONS.RAZORPAY),
      BANK:     Math.round(containerWidth * COL_FRACTIONS.BANK),
      ERP:      Math.round(containerWidth * COL_FRACTIONS.ERP),
    };

    // Deduplicate and filter active clusters that contain transactions
    const seenClusterIds = new Set<string>();
    const activeClusters = clusters
      .filter((c) => {
        if (!c.cluster_id || seenClusterIds.has(c.cluster_id)) return false;
        seenClusterIds.add(c.cluster_id);
        return (c.razorpay_txns?.length || 0) + (c.bank_txns?.length || 0) + (c.erp_txns?.length || 0) > 0;
      })
      .slice(0, MAX_VISIBLE_CLUSTERS);

    // Guaranteed 1 Cluster = 1 Row (1:1:1 Layout)
    // Every cluster occupies exactly 1 horizontal row at y = rowIndex * ROW_HEIGHT (175px)
    activeClusters.forEach((cluster, rowIndex) => {
      const y = rowIndex * ROW_HEIGHT;
      const isDiscrepancy = cluster.discrepancy_paise !== 0 || cluster.status === 'DISCREPANCY';
      const isMatched = cluster.discrepancy_paise === 0 && cluster.status === 'MATCHED';
      const matchStatus = isDiscrepancy ? 'DISCREPANCY' : (isMatched ? 'MATCHED' : 'SETTLED_PENDING_ERP');
      const edgeColor = isDiscrepancy ? '#DC2626' : (isMatched ? '#059669' : '#D97706');
      const clusterKey = cluster.cluster_id;

      // Use a stable wrapper so node data.onSelect never changes between renders
      const stableOnSelect = (id: string) => onNodeSelectRef.current(id);

      const rzpCount = cluster.razorpay_txns?.length || 0;
      const isMultiRzp = rzpCount > 1;
      const primaryRzp = cluster.razorpay_txns?.[0];
      const primaryBank = cluster.bank_txns?.[0];
      const primaryErp = cluster.erp_txns?.[0];
      const hasErp = (cluster.erp_txns?.length || 0) > 0;

      const rzpTotalMdr = (cluster.razorpay_txns || []).reduce((acc, t) => acc + (t.fee_mdr_paise || 0), 0);
      const rzpTotalGst = (cluster.razorpay_txns || []).reduce((acc, t) => acc + (t.fee_gst_paise || 0), 0);

      const rzpNodeId = `${clusterKey}|rzp`;
      const bankNodeId = `${clusterKey}|bank`;
      const erpNodeId = `${clusterKey}|erp`;

      // ── 1. Column 1: Razorpay Consolidated Card (1:1:1 mapping) ─────────────
      nodes.push({
        id: rzpNodeId,
        type: 'transaction',
        position: { x: colX.RAZORPAY, y },
        data: {
          txnId: primaryRzp?.id || `${clusterKey}-rzp`,
          source: 'RAZORPAY',
          original_id: isMultiRzp
            ? `Batch (${rzpCount} Payments)`
            : (primaryRzp?.original_id || primaryRzp?.id || 'RZP-PAY'),
          order_id: primaryRzp?.order_id || null,
          utr: primaryRzp?.utr || primaryBank?.utr || null,
          amount_gross_paise: cluster.sum_gross_paise || (primaryRzp?.amount_gross_paise ?? 0),
          amount_net_paise: cluster.sum_net_expected_paise || (primaryRzp?.amount_net_paise ?? 0),
          fee_mdr_paise: rzpTotalMdr,
          fee_gst_paise: rzpTotalGst,
          raw_narration: primaryRzp?.raw_narration,
          status: matchStatus,
          timestamp_utc: primaryRzp?.timestamp_utc || new Date().toISOString(),
          batchCount: isMultiRzp ? rzpCount : undefined,
          onSelect: () => stableOnSelect(rzpNodeId),
        } as unknown as TransactionNodeData,
      });

      // ── 2. Column 2: Bank Statement Net Credit Card ─────────────────────────
      nodes.push({
        id: bankNodeId,
        type: 'transaction',
        position: { x: colX.BANK, y },
        data: {
          txnId: primaryBank?.id || `${clusterKey}-bank`,
          source: 'BANK',
          original_id: primaryBank?.original_id || primaryBank?.id || 'BANK-DEPOSIT',
          order_id: primaryRzp?.order_id || null,
          utr: primaryBank?.utr || primaryRzp?.utr || null,
          amount_gross_paise: cluster.sum_bank_credit_paise || (primaryBank?.amount_net_paise ?? 0),
          amount_net_paise: cluster.sum_bank_credit_paise || (primaryBank?.amount_net_paise ?? 0),
          fee_mdr_paise: 0,
          fee_gst_paise: 0,
          raw_narration: primaryBank?.raw_narration || 'Settlement Net Credit',
          status: matchStatus,
          timestamp_utc: primaryBank?.timestamp_utc || primaryRzp?.timestamp_utc || new Date().toISOString(),
          onSelect: () => stableOnSelect(bankNodeId),
        } as unknown as TransactionNodeData,
      });

      // ── 3. Column 3: ERP Invoices & GL Ledger Card ─────────────────────────
      const erpOriginalId = hasErp
        ? (primaryErp?.original_id || primaryErp?.id || 'ERP-INV')
        : (isDiscrepancy
            ? 'UNPOSTED · Discrepancy Hold'
            : (isMatched ? 'ERP · Direct Settlement' : 'UNPOSTED · Awaiting Invoice'));

      const erpNarration = hasErp
        ? (primaryErp?.raw_narration || 'ERP Ledger Post')
        : (isDiscrepancy ? 'Awaiting AI voucher dispatch to Zoho Books' : 'Direct GL auto-settled');

      nodes.push({
        id: erpNodeId,
        type: 'transaction',
        position: { x: colX.ERP, y },
        data: {
          txnId: primaryErp?.id || (primaryBank ? primaryBank.id : `${clusterKey}-erp`),
          source: 'ERP',
          original_id: erpOriginalId,
          order_id: primaryErp?.order_id || primaryRzp?.order_id || 'SETTLED',
          utr: primaryErp?.utr || primaryBank?.utr || null,
          amount_gross_paise: hasErp
            ? (primaryErp?.amount_gross_paise || primaryErp?.amount_net_paise || 0)
            : (cluster.sum_bank_credit_paise || cluster.sum_gross_paise),
          amount_net_paise: hasErp
            ? (primaryErp?.amount_net_paise || 0)
            : (cluster.sum_bank_credit_paise || cluster.sum_net_expected_paise),
          fee_mdr_paise: 0,
          fee_gst_paise: 0,
          raw_narration: erpNarration,
          status: matchStatus,
          timestamp_utc: primaryErp?.timestamp_utc || primaryBank?.timestamp_utc || new Date().toISOString(),
          onSelect: () => stableOnSelect(erpNodeId),
        } as unknown as TransactionNodeData,
      });

      // ── 4. Pure Horizontal Edges (Left Handle → Right Handle at identical Y) ──
      // Razorpay → Bank direct horizontal edge
      edges.push({
        id: `edge|${clusterKey}|rzp|bank`,
        source: rzpNodeId,
        target: bankNodeId,
        type: 'straight',
        animated: isDiscrepancy,
        style: {
          stroke: edgeColor,
          strokeWidth: 2,
          opacity: 0.85,
        },
      });

      // Bank → ERP direct horizontal edge
      const isPending = !isMatched && !isDiscrepancy;
      edges.push({
        id: `edge|${clusterKey}|bank|erp`,
        source: bankNodeId,
        target: erpNodeId,
        type: 'straight',
        animated: isPending || isDiscrepancy,
        style: {
          stroke: edgeColor,
          strokeWidth: 2,
          strokeDasharray: isPending ? '4 4' : undefined,
          opacity: 0.85,
        },
      });
    });

    return { nodes, edges };
  // onNodeSelect is intentionally omitted from useMemo deps — it's accessed via
  // onNodeSelectRef so changes never invalidate the memo (avoids node flicker).
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clusters, containerWidth]);

  const handleNodeSelect = useCallback((id: string) => onNodeSelectRef.current(id), []);

  return (
    <div ref={containerRef} className="w-full h-full">
      <ReactFlowProvider>
        <FlowInner
          nodes={nodes}
          edges={edges}
          onNodeSelect={handleNodeSelect}
        />
      </ReactFlowProvider>
    </div>
  );
};
