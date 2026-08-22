/**
 * RECON-MESH Step 12: Custom Transaction Node for React Flow
 * ==========================================================
 * Renders a dense, compact, AMOLED-dark financial transaction card inside React Flow.
 * Color-coded by MatchStatus: Green = MATCHED, Amber = SETTLED_PENDING_ERP, Red = DISCREPANCY.
 * Compatible with @xyflow/react v12 NodeProps API.
 *
 * FIX LOG (v2.2):
 *  - Enforced min-w-[280px] to prevent text overlap on MDR/GST/UTR/amount fields.
 *  - Added gap-2 vertical rhythm between financial rows.
 *  - Increased font contrast: MDR/GST/UTR upgraded from text-[#4E4E4E] to text-[#888888].
 *  - Padded card to p-3 (was p-2) for better breathing room.
 *  - Status badge wrapping: status text uses truncate + max-w to avoid overlap.
 *  - Gross amount font size lifted to text-[15px] for readability.
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

const STATUS_CONFIG: Record<MatchStatus, { border: string; text: string; badge: string; dot: string; glow: string }> = {
  MATCHED: {
    border: 'border-[rgba(0,255,102,0.4)]',
    text: 'text-[#00FF66]',
    badge: 'bg-[rgba(0,255,102,0.1)] text-[#00FF66] border-[rgba(0,255,102,0.3)]',
    dot: 'bg-[#00FF66]',
    glow: 'shadow-[0_0_8px_rgba(0,255,102,0.12)]',
  },
  SETTLED_PENDING_ERP: {
    border: 'border-[rgba(255,184,0,0.4)]',
    text: 'text-[#FFB800]',
    badge: 'bg-[rgba(255,184,0,0.1)] text-[#FFB800] border-[rgba(255,184,0,0.3)]',
    dot: 'bg-[#FFB800]',
    glow: 'shadow-[0_0_8px_rgba(255,184,0,0.12)]',
  },
  DISCREPANCY: {
    border: 'border-[rgba(255,51,102,0.4)]',
    text: 'text-[#FF3366]',
    badge: 'bg-[rgba(255,51,102,0.1)] text-[#FF3366] border-[rgba(255,51,102,0.3)]',
    dot: 'bg-[#FF3366]',
    glow: 'shadow-[0_0_8px_rgba(255,51,102,0.12)]',
  },
  PENDING: {
    border: 'border-[#252525]',
    text: 'text-[#888888]',
    badge: 'bg-[#111111] text-[#888888] border-[#252525]',
    dot: 'bg-[#888888]',
    glow: '',
  },
  ORPHAN: {
    border: 'border-[rgba(255,51,102,0.25)]',
    text: 'text-[#FF3366]',
    badge: 'bg-[rgba(255,51,102,0.06)] text-[#FF3366] border-[rgba(255,51,102,0.18)]',
    dot: 'bg-[#FF3366] opacity-50',
    glow: '',
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
  const mdrInr = (d.fee_mdr_paise / 100).toFixed(2);
  const gstInr = (d.fee_gst_paise / 100).toFixed(2);

  const handleClick = () => {
    if (d.onSelect) d.onSelect(d.txnId);
  };

  return (
    <div
      onClick={handleClick}
      className={`bg-[#080808] border ${cfg.border} ${cfg.glow} rounded p-3 min-w-[280px] w-[280px] cursor-pointer hover:bg-[#0E0E0E] transition-all duration-150 select-none flex flex-col gap-2`}
    >
      {/* Row 1: Source badge + Status indicator */}
      <div className="flex items-center justify-between gap-2">
        <span
          className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border tracking-wider flex-shrink-0 ${cfg.badge}`}
        >
          {SOURCE_LABEL[d.source]}
        </span>
        <div className="flex items-center gap-1 min-w-0 overflow-hidden">
          <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${cfg.dot}`} />
          <span className={`text-[8px] font-mono font-semibold truncate ${cfg.text}`}>
            {d.status}
          </span>
        </div>
      </div>

      {/* Row 2: Transaction ID (full display, monospace) */}
      <p
        className="text-[9px] font-mono text-[#AAAAAA] font-medium truncate leading-tight"
        title={d.original_id}
      >
        {d.original_id}
      </p>

      {/* Row 3: Gross Amount — primary financial figure */}
      <p className={`text-[15px] font-mono font-bold tabular-nums leading-none ${cfg.text}`}>
        ₹{grossInr}
      </p>

      {/* Row 4: Per-source financial detail rows */}
      {d.source === 'RAZORPAY' && (
        <div className="grid grid-cols-2 gap-1 pt-1 border-t border-[#1A1A1A]">
          <div className="flex flex-col gap-0.5">
            <span className="text-[8px] font-mono text-[#555555] uppercase tracking-wider">MDR</span>
            <span className="text-[10px] font-mono text-[#888888] tabular-nums">₹{mdrInr}</span>
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-[8px] font-mono text-[#555555] uppercase tracking-wider">GST</span>
            <span className="text-[10px] font-mono text-[#888888] tabular-nums">₹{gstInr}</span>
          </div>
        </div>
      )}

      {d.source === 'BANK' && (
        <div className="pt-1 border-t border-[#1A1A1A]">
          <div className="flex items-center justify-between gap-1">
            <span className="text-[8px] font-mono text-[#555555] uppercase tracking-wider flex-shrink-0">NET CREDIT</span>
            <span className="text-[10px] font-mono text-[#00FF66] tabular-nums">₹{netInr}</span>
          </div>
        </div>
      )}

      {d.source === 'ERP' && (
        <div className="pt-1 border-t border-[#1A1A1A]">
          <div className="flex items-center justify-between gap-1">
            <span className="text-[8px] font-mono text-[#555555] uppercase tracking-wider flex-shrink-0">GL AMOUNT</span>
            <span className="text-[10px] font-mono text-[#FFB800] tabular-nums">₹{grossInr}</span>
          </div>
        </div>
      )}

      {/* Row 5: UTR reference (if present) */}
      {d.utr && (
        <div className="flex items-center gap-1 overflow-hidden">
          <span className="text-[8px] font-mono text-[#444444] uppercase tracking-wider flex-shrink-0">UTR</span>
          <span
            className="text-[9px] font-mono text-[#666666] truncate"
            title={d.utr}
          >
            {d.utr}
          </span>
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="!w-2 !h-2 !bg-[#1A1A1A] !border !border-[#333333] !rounded-full"
      />
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2 !h-2 !bg-[#1A1A1A] !border !border-[#333333] !rounded-full"
      />
    </div>
  );
};
