/**
 * RECON-MESH Step 12: Custom Transaction Node for React Flow
 * ==========================================================
 * Renders a dense, compact, AMOLED-dark financial transaction card inside React Flow.
 * Color-coded by MatchStatus: Green = MATCHED, Amber = SETTLED_PENDING_ERP, Red = DISCREPANCY.
 * Compatible with @xyflow/react v12 NodeProps API.
 */

import React from 'react';
import { Handle, Position } from '@xyflow/react';
import type { MatchStatus, SourceType } from '../types/recon';

export interface TransactionNodeData extends Record<string, unknown> {
  txnId: string;
  source: SourceType;
  original_id: string;
  order_id?: string | null;
  utr?: string | null;
  amount_gross_paise: number;
  amount_net_paise: number;
  fee_mdr_paise: number;
  fee_gst_paise: number;
  raw_narration?: string | null;
  status: MatchStatus;
  timestamp_utc: string;
  onSelect?: (id: string) => void;
}

const STATUS_CONFIG: Record<MatchStatus, { border: string; text: string; badge: string; dot: string }> = {
  MATCHED: {
    border: 'border-[rgba(0,255,102,0.35)]',
    text: 'text-[#00FF66]',
    badge: 'bg-[rgba(0,255,102,0.08)] text-[#00FF66] border-[rgba(0,255,102,0.25)]',
    dot: 'bg-[#00FF66]',
  },
  SETTLED_PENDING_ERP: {
    border: 'border-[rgba(255,184,0,0.35)]',
    text: 'text-[#FFB800]',
    badge: 'bg-[rgba(255,184,0,0.08)] text-[#FFB800] border-[rgba(255,184,0,0.25)]',
    dot: 'bg-[#FFB800]',
  },
  DISCREPANCY: {
    border: 'border-[rgba(255,51,102,0.35)]',
    text: 'text-[#FF3366]',
    badge: 'bg-[rgba(255,51,102,0.08)] text-[#FF3366] border-[rgba(255,51,102,0.25)]',
    dot: 'bg-[#FF3366]',
  },
  PENDING: {
    border: 'border-[#222222]',
    text: 'text-[#888888]',
    badge: 'bg-[#111111] text-[#888888] border-[#222222]',
    dot: 'bg-[#888888]',
  },
  ORPHAN: {
    border: 'border-[rgba(255,51,102,0.2)]',
    text: 'text-[#FF3366]',
    badge: 'bg-[rgba(255,51,102,0.05)] text-[#FF3366] border-[rgba(255,51,102,0.15)]',
    dot: 'bg-[#FF3366] opacity-50',
  },
};

const SOURCE_LABEL: Record<SourceType, string> = {
  RAZORPAY: 'RZP',
  BANK: 'BANK',
  ERP: 'ERP',
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const CustomTransactionNode: React.FC<any> = ({ data }: { data: TransactionNodeData }) => {
  const d = data as TransactionNodeData;
  const cfg = STATUS_CONFIG[d.status] ?? STATUS_CONFIG.PENDING;

  const grossInr = (d.amount_gross_paise / 100).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const netInr = (d.amount_net_paise / 100).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const handleClick = () => {
    if (d.onSelect) d.onSelect(d.txnId);
  };

  return (
    <div
      onClick={handleClick}
      className={`bg-[#090909] border ${cfg.border} rounded-sm p-2 w-[180px] cursor-pointer hover:bg-[#0D0D0D] transition-colors select-none`}
    >
      {/* Source badge and status dot */}
      <div className="flex items-center justify-between mb-1.5">
        <span className={`text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded border ${cfg.badge}`}>
          {SOURCE_LABEL[d.source]}
        </span>
        <div className="flex items-center space-x-1">
          <div className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
          <span className={`text-[9px] font-mono ${cfg.text}`}>{d.status}</span>
        </div>
      </div>

      {/* Transaction ID */}
      <p className="text-[10px] font-mono text-[#EDEDED] font-semibold truncate mb-0.5" title={d.original_id}>
        {d.original_id}
      </p>

      {/* Gross Amount */}
      <p className={`text-[13px] font-mono font-semibold tabular-nums ${cfg.text}`}>
        ₹{grossInr}
      </p>

      {/* Per-source additional rows */}
      {d.source === 'RAZORPAY' && (
        <div className="flex justify-between text-[9px] font-mono text-[#4E4E4E] mt-1">
          <span>MDR ₹{(d.fee_mdr_paise / 100).toFixed(2)}</span>
          <span>GST ₹{(d.fee_gst_paise / 100).toFixed(2)}</span>
        </div>
      )}
      {d.source === 'BANK' && (
        <p className="text-[9px] font-mono text-[#888888] mt-1 truncate">
          Net ₹{netInr}
        </p>
      )}
      {d.utr && (
        <p className="text-[9px] font-mono text-[#4E4E4E] truncate mt-0.5" title={d.utr}>
          UTR: {d.utr}
        </p>
      )}

      <Handle type="source" position={Position.Right} className="!w-1.5 !h-1.5 !bg-[#222222] !border-[#333333]" />
      <Handle type="target" position={Position.Left} className="!w-1.5 !h-1.5 !bg-[#222222] !border-[#333333]" />
    </div>
  );
};
