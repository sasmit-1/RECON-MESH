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
const ROW_HEIGHT = 160;
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

  // Lock viewport to readable zoom on first node load
  useEffect(() => {
    if (!initializedRef.current && nodes.length > 0) {
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

    // Track globally seen txn IDs to skip any duplicates across clusters
    const seenNodeIds = new Set<string>();
    let currentRow = 0;

    activeClusters.forEach((cluster) => {
      const baseY = currentRow * ROW_HEIGHT;
      currentRow += 1;

      const matchStatus = cluster.discrepancy_paise === 0 ? 'MATCHED' : 'DISCREPANCY';
      const edgeColor = cluster.discrepancy_paise === 0 ? '#059669' : '#DC2626';
      // Scope every node ID to its cluster to prevent React Flow duplicate-ID crashes
      const clusterKey = cluster.cluster_id;

      // ── Razorpay nodes ──────────────────────────────────────────────────────
      cluster.razorpay_txns.forEach((txn, i) => {
        const nodeId = `${clusterKey}|rzp|${txn.id}`;
        if (seenNodeIds.has(nodeId)) return;
        seenNodeIds.add(nodeId);
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
            onSelect: onNodeSelect,
          } as unknown as TransactionNodeData,
        });

        // RZP → Bank edges
        cluster.bank_txns.forEach((bank) => {
          const bankNodeId = `${clusterKey}|bank|${bank.id}`;
          const edgeId = `edge|${nodeId}|${bankNodeId}`;
          edges.push({
            id: edgeId,
            source: nodeId,
            target: bankNodeId,
            animated: matchStatus === 'DISCREPANCY',
            style: { stroke: edgeColor, strokeWidth: 1.5, opacity: 0.6 },
          });
        });
      });

      // ── Bank nodes ──────────────────────────────────────────────────────────
      cluster.bank_txns.forEach((txn, i) => {
        const nodeId = `${clusterKey}|bank|${txn.id}`;
        if (seenNodeIds.has(nodeId)) return;
        seenNodeIds.add(nodeId);
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
            onSelect: onNodeSelect,
          } as unknown as TransactionNodeData,
        });

        // Bank → ERP edges
        const bankEdgeColor = cluster.status === 'SETTLED_PENDING_ERP' ? '#D97706' : edgeColor;
        cluster.erp_txns.forEach((erp) => {
          const erpNodeId = `${clusterKey}|erp|${erp.id}`;
          const edgeId = `edge|${nodeId}|${erpNodeId}`;
          edges.push({
            id: edgeId,
            source: nodeId,
            target: erpNodeId,
            animated: cluster.status === 'SETTLED_PENDING_ERP',
            style: { stroke: bankEdgeColor, strokeWidth: 1.5, opacity: 0.6 },
          });
        });
      });

      // ── ERP nodes ───────────────────────────────────────────────────────────
      if (cluster.erp_txns.length > 0) {
        cluster.erp_txns.forEach((txn, i) => {
          const nodeId = `${clusterKey}|erp|${txn.id}`;
          if (seenNodeIds.has(nodeId)) return;
          seenNodeIds.add(nodeId);
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
              onSelect: onNodeSelect,
            } as unknown as TransactionNodeData,
          });
        });
      } else if (cluster.bank_txns.length > 0) {
        // Pending ERP Ledger entry placeholder for unposted / discrepancy settlements
        const erpPlaceholderId = `${clusterKey}|erp|pending`;
        const rzpTxn = cluster.razorpay_txns[0];
        const bankTxn = cluster.bank_txns[0];
        const isDiscrepancy = cluster.discrepancy_paise !== 0;

        nodes.push({
          id: erpPlaceholderId,
          type: 'transaction',
          position: { x: colX.ERP, y: baseY },
          data: {
            txnId: bankTxn.id,
            source: 'ERP',
            original_id: isDiscrepancy ? 'UNPOSTED · Discrepancy Hold' : 'UNPOSTED · Awaiting Invoice',
            order_id: rzpTxn?.order_id || 'PENDING',
            utr: bankTxn.utr,
            amount_gross_paise: cluster.sum_gross_paise || bankTxn.amount_net_paise,
            amount_net_paise: cluster.sum_net_expected_paise || bankTxn.amount_net_paise,
            fee_mdr_paise: 0,
            fee_gst_paise: 0,
            raw_narration: 'Awaiting AI voucher dispatch to Zoho Books',
            status: isDiscrepancy ? 'DISCREPANCY' : 'SETTLED_PENDING_ERP',
            timestamp_utc: bankTxn.timestamp_utc,
            onSelect: onNodeSelect,
          } as unknown as TransactionNodeData,
        });

        // Bank → ERP placeholder dashed edge
        const bankNodeId = `${clusterKey}|bank|${bankTxn.id}`;
        const edgeId = `edge|${bankNodeId}|${erpPlaceholderId}`;
        edges.push({
          id: edgeId,
          source: bankNodeId,
          target: erpPlaceholderId,
          animated: true,
          style: {
            stroke: isDiscrepancy ? '#DC2626' : '#D97706',
            strokeWidth: 1.5,
            strokeDasharray: '4 4',
            opacity: 0.6,
          },
        });
      }
    });

    return { nodes, edges };
  }, [clusters, containerWidth, onNodeSelect]);

  const handleNodeSelect = useCallback((id: string) => onNodeSelect(id), [onNodeSelect]);

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
