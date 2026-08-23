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
const MAX_VISIBLE_CLUSTERS = 25;

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

    // Limit to active clusters that contain transactions, eliminating blank vertical gaps
    const activeClusters = clusters
      .filter((c) => (c.razorpay_txns?.length || 0) + (c.bank_txns?.length || 0) + (c.erp_txns?.length || 0) > 0)
      .slice(0, MAX_VISIBLE_CLUSTERS);

    let currentRow = 0;

    activeClusters.forEach((cluster) => {
      const clusterHeight = Math.max(
        cluster.razorpay_txns?.length || 0,
        cluster.bank_txns?.length || 0,
        cluster.erp_txns?.length || 0,
        1
      );
      const baseY = currentRow * ROW_HEIGHT;
      currentRow += clusterHeight;

      const isDiscrepancy = cluster.discrepancy_paise !== 0 || cluster.status === 'DISCREPANCY';
      const isMatched = cluster.discrepancy_paise === 0 && cluster.status === 'MATCHED';
      const matchStatus = isDiscrepancy ? 'DISCREPANCY' : (isMatched ? 'MATCHED' : 'SETTLED_PENDING_ERP');
      const edgeColor = isDiscrepancy ? '#DC2626' : (isMatched ? '#059669' : '#D97706');
      const clusterKey = cluster.cluster_id;

      // Use a stable wrapper so node data.onSelect never changes between renders
      // (avoids React Flow diffing every node as "updated" on each cluster flush)
      const stableOnSelect = (id: string) => onNodeSelectRef.current(id);

      // ── 1. Razorpay nodes ───────────────────────────────────────────────────
      const rzpNodeIds: string[] = [];
      cluster.razorpay_txns.forEach((txn, i) => {
        const nodeId = `${clusterKey}|rzp|${txn.id}`;
        rzpNodeIds.push(nodeId);
        const y = baseY + i * ROW_HEIGHT;
        nodes.push({
          id: nodeId,
          type: 'transaction',
          position: { x: colX.RAZORPAY, y },
          data: {
            txnId: txn.id,
            source: txn.source,
            original_id: txn.original_id,
            order_id: txn.order_id,
            utr: txn.utr,
            amount_gross_paise: txn.amount_gross_paise,
            amount_net_paise: txn.amount_net_paise,
            fee_mdr_paise: txn.fee_mdr_paise,
            fee_gst_paise: txn.fee_gst_paise,
            raw_narration: txn.raw_narration,
            status: matchStatus,
            timestamp_utc: txn.timestamp_utc,
            onSelect: stableOnSelect,
          } as unknown as TransactionNodeData,
        });
      });

      // ── 2. Bank nodes ───────────────────────────────────────────────────────
      const bankNodeIds: string[] = [];
      cluster.bank_txns.forEach((txn, i) => {
        const nodeId = `${clusterKey}|bank|${txn.id}`;
        bankNodeIds.push(nodeId);
        const y = baseY + i * ROW_HEIGHT;
        nodes.push({
          id: nodeId,
          type: 'transaction',
          position: { x: colX.BANK, y },
          data: {
            txnId: txn.id,
            source: txn.source,
            original_id: txn.original_id,
            order_id: txn.order_id,
            utr: txn.utr,
            amount_gross_paise: txn.amount_gross_paise,
            amount_net_paise: txn.amount_net_paise,
            fee_mdr_paise: txn.fee_mdr_paise,
            fee_gst_paise: txn.fee_gst_paise,
            raw_narration: txn.raw_narration,
            status: matchStatus,
            timestamp_utc: txn.timestamp_utc,
            onSelect: stableOnSelect,
          } as unknown as TransactionNodeData,
        });
      });

      // ── 3. ERP nodes ────────────────────────────────────────────────────────
      const erpNodeIds: string[] = [];
      if (cluster.erp_txns.length > 0) {
        cluster.erp_txns.forEach((txn, i) => {
          const nodeId = `${clusterKey}|erp|${txn.id}`;
          erpNodeIds.push(nodeId);
          const y = baseY + i * ROW_HEIGHT;
          nodes.push({
            id: nodeId,
            type: 'transaction',
            position: { x: colX.ERP, y },
            data: {
              txnId: txn.id,
              source: txn.source,
              original_id: txn.original_id,
              order_id: txn.order_id,
              utr: txn.utr,
              amount_gross_paise: txn.amount_gross_paise,
              amount_net_paise: txn.amount_net_paise,
              fee_mdr_paise: txn.fee_mdr_paise,
              fee_gst_paise: txn.fee_gst_paise,
              raw_narration: txn.raw_narration,
              status: cluster.status,
              timestamp_utc: txn.timestamp_utc,
              onSelect: stableOnSelect,
            } as unknown as TransactionNodeData,
          });
        });
      } else if (bankNodeIds.length > 0) {
        // ERP Ledger entry placeholder for settlements awaiting direct dispatch
        const erpPlaceholderId = `${clusterKey}|erp|pending`;
        erpNodeIds.push(erpPlaceholderId);
        const rzpTxn = cluster.razorpay_txns[0];
        const bankTxn = cluster.bank_txns[0];

        const erpOriginalId = isDiscrepancy
          ? 'UNPOSTED · Discrepancy Hold'
          : (isMatched ? 'ERP · Direct Settlement' : 'UNPOSTED · Awaiting Invoice');

        nodes.push({
          id: erpPlaceholderId,
          type: 'transaction',
          position: { x: colX.ERP, y: baseY },
          data: {
            txnId: bankTxn ? bankTxn.id : 'pending_erp',
            source: 'ERP',
            original_id: erpOriginalId,
            order_id: rzpTxn?.order_id || 'SETTLED',
            utr: bankTxn?.utr || null,
            amount_gross_paise: cluster.sum_gross_paise || (bankTxn?.amount_net_paise ?? 0),
            amount_net_paise: cluster.sum_net_expected_paise || (bankTxn?.amount_net_paise ?? 0),
            fee_mdr_paise: 0,
            fee_gst_paise: 0,
            raw_narration: isDiscrepancy ? 'Awaiting AI voucher dispatch to Zoho Books' : 'Direct GL auto-settled',
            status: matchStatus,
            timestamp_utc: bankTxn?.timestamp_utc || new Date().toISOString(),
            onSelect: stableOnSelect,
          } as unknown as TransactionNodeData,
        });
      }

      // ── 4. Strictly Intra-Cluster Horizontal Edges ──────────────────────────
      // Razorpay → Bank edges (only between this row's nodes)
      rzpNodeIds.forEach((rzpId) => {
        bankNodeIds.forEach((bankId) => {
          edges.push({
            id: `edge|${rzpId}|${bankId}`,
            source: rzpId,
            target: bankId,
            animated: isDiscrepancy,
            style: { stroke: edgeColor, strokeWidth: 1.5, opacity: 0.6 },
          });
        });
      });

      // Bank → ERP edges (only between this row's nodes)
      const isPending = !isMatched && !isDiscrepancy;
      bankNodeIds.forEach((bankId) => {
        erpNodeIds.forEach((erpId) => {
          edges.push({
            id: `edge|${bankId}|${erpId}`,
            source: bankId,
            target: erpId,
            animated: isPending || isDiscrepancy,
            style: {
              stroke: edgeColor,
              strokeWidth: 1.5,
              strokeDasharray: isPending ? '4 4' : undefined,
              opacity: 0.6,
            },
          });
        });
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
