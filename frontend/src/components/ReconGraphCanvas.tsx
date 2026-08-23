/**
 * RECON-MESH Step 12: Interactive 3-Column Bipartite DAG Canvas
 * =============================================================
 * Renders a high-density React Flow bipartite board with 3 columnar lanes:
 *   Column A: Razorpay Captured Feeds (Gross ₹, MDR, GST, UTR)
 *   Column B: Core Bank Deposits (Net Credit ₹, Narration, Value Date)
 *   Column C: ERP Invoices & GL Ledgers (Invoice ID, AR, Amount ₹)
 *
 * A synchronized Three.js WebGL overlay draws razor-sharp bezier laser arcs
 * between matched node coordinates, tied to the React Flow viewport transform.
 */

import React, { useCallback, useEffect, useMemo, useRef } from 'react';
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
import { ThreeLaserArcOverlay, type LaserLine } from './ThreeLaserArcOverlay';

// Cast to NodeTypes to satisfy @xyflow/react strict signature
const NODE_TYPES: NodeTypes = {
  transaction: CustomTransactionNode as NodeTypes[string],
};

// Fixed column X positions (React Flow coordinate space)
// Node width 240px; 320px column intervals = 80px gutters
const COL_X = { RAZORPAY: 0, BANK: 320, ERP: 640 };
const ROW_HEIGHT = 140;

interface ReconGraphCanvasProps {
  clusters: ReconciliationCluster[];
  onNodeSelect: (nodeId: string) => void;
}

// Inner component inside ReactFlowProvider — calls useViewport() and useReactFlow()
const FlowInner: React.FC<{
  nodes: Node<TransactionNodeData>[];
  edges: Edge[];
  lasers: LaserLine[];
  onNodeSelect: (id: string) => void;
}> = ({ nodes, edges, lasers, onNodeSelect }) => {
  const viewport = useViewport();
  const { fitView } = useReactFlow();
  const prevCountRef = useRef<number>(0);

  // Auto-fit viewport whenever nodes load or expand
  useEffect(() => {
    if (nodes.length > 0 && nodes.length !== prevCountRef.current) {
      prevCountRef.current = nodes.length;
      const timer = setTimeout(() => {
        fitView({ padding: 0.2, duration: 300 });
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [nodes.length, fitView]);

  return (
    <div className="relative w-full h-full bg-[#F4F6FA] overflow-hidden">
      {/* Layer 0: WebGL Laser Arc Overlay */}
      <ThreeLaserArcOverlay lasers={lasers} viewport={viewport} />

      {/* Layer 1: React Flow Canvas */}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        onNodeClick={(_, node) => onNodeSelect(node.id)}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2.5}
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
  const { nodes, edges, lasers } = useMemo(() => {
    const nodes: Node<TransactionNodeData>[] = [];
    const edges: Edge[] = [];
    const lasers: LaserLine[] = [];

    clusters.forEach((cluster, clusterIdx) => {
      const baseY = clusterIdx * ROW_HEIGHT * 1.2;
      const matchStatus = cluster.discrepancy_paise === 0 ? 'MATCHED' : 'DISCREPANCY';
      // Muted professional edge colors — no neon
      const laserColor = cluster.discrepancy_paise === 0 ? '#059669' : '#DC2626';

      // Razorpay nodes
      cluster.razorpay_txns.forEach((txn, i) => {
        const nodeId = `rzp-${txn.id}`;
        const y = baseY + i * ROW_HEIGHT;
        nodes.push({
          id: nodeId,
          type: 'transaction',
          position: { x: COL_X.RAZORPAY, y },
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

        // RZP → Bank edges + laser arcs
        cluster.bank_txns.forEach((bank) => {
          const bankNodeId = `bank-${bank.id}`;
          const edgeId = `e-${nodeId}-${bankNodeId}`;
          edges.push({
            id: edgeId,
            source: nodeId,
            target: bankNodeId,
            animated: matchStatus === 'DISCREPANCY',
            style: { stroke: laserColor, strokeWidth: 1.5, opacity: 0.5 },
          });
          lasers.push({
            id: edgeId,
            sourceX: COL_X.RAZORPAY + 240,
            sourceY: y + 50,
            targetX: COL_X.BANK,
            targetY: baseY + 50,
            color: laserColor,
          });
        });
      });

      // Bank nodes
      cluster.bank_txns.forEach((txn, i) => {
        const nodeId = `bank-${txn.id}`;
        const y = baseY + i * ROW_HEIGHT;
        nodes.push({
          id: nodeId,
          type: 'transaction',
          position: { x: COL_X.BANK, y },
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

        // Bank → ERP edges + laser arcs
        const bankLaserColor =
          cluster.status === 'SETTLED_PENDING_ERP' ? '#D97706' : laserColor;
        cluster.erp_txns.forEach((erp) => {
          const erpNodeId = `erp-${erp.id}`;
          const edgeId2 = `e-${nodeId}-${erpNodeId}`;
          edges.push({
            id: edgeId2,
            source: nodeId,
            target: erpNodeId,
            animated: cluster.status === 'SETTLED_PENDING_ERP',
            style: { stroke: bankLaserColor, strokeWidth: 1.5, opacity: 0.5 },
          });
          lasers.push({
            id: edgeId2 + '-laser',
            sourceX: COL_X.BANK + 240,
            sourceY: y + 50,
            targetX: COL_X.ERP,
            targetY: baseY + 50,
            color: bankLaserColor,
          });
        });
      });

      // ERP nodes
      cluster.erp_txns.forEach((txn, i) => {
        const nodeId = `erp-${txn.id}`;
        const y = baseY + i * ROW_HEIGHT;
        nodes.push({
          id: nodeId,
          type: 'transaction',
          position: { x: COL_X.ERP, y },
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
    });

    return { nodes, edges, lasers };
  }, [clusters, onNodeSelect]);

  const handleNodeSelect = useCallback((id: string) => onNodeSelect(id), [onNodeSelect]);

  return (
    <ReactFlowProvider>
      <FlowInner
        nodes={nodes}
        edges={edges}
        lasers={lasers}
        onNodeSelect={handleNodeSelect}
      />
    </ReactFlowProvider>
  );
};
