/**
 * RECON-MESH: Custom Transaction Node
 * =====================================
 * Clean, professional node card for React Flow.
 * White surface, subtle colored left-border by status, readable typography.
 * No neon — uses muted semantic colors (emerald / amber / rose).
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

interface StatusStyle {
  accent: string;   // left border color
  badge: string;    // badge classes
  label: string;    // display label
  amount: string;   // amount text color
}

const STATUS_STYLES: Record<MatchStatus, StatusStyle> = {
  MATCHED: {
    accent: 'border-l-[#059669]',
    badge: 'bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]',
    label: 'Matched',
    amount: 'text-[#059669]',
  },
  SETTLED_PENDING_ERP: {
    accent: 'border-l-[#D97706]',
    badge: 'bg-[#FFFBEB] text-[#D97706] border border-[#FDE68A]',
    label: 'Pending ERP',
    amount: 'text-[#D97706]',
  },
  DISCREPANCY: {
    accent: 'border-l-[#DC2626]',
    badge: 'bg-[#FEF2F2] text-[#DC2626] border border-[#FECACA]',
    label: 'Discrepancy',
    amount: 'text-[#DC2626]',
  },
  PENDING: {
    accent: 'border-l-[#D1D5DB]',
    badge: 'bg-[#F9FAFB] text-[#6B7280] border border-[#E5E7EB]',
    label: 'Pending',
    amount: 'text-[#6B7280]',
  },
  ORPHAN: {
    accent: 'border-l-[#EF4444]',
    badge: 'bg-[#FEF2F2] text-[#EF4444] border border-[#FECACA]',
    label: 'Orphan',
    amount: 'text-[#EF4444]',
  },
};

const SOURCE_CONFIG: Record<SourceType, { label: string; color: string }> = {
  RAZORPAY: { label: 'Razorpay', color: 'text-[#2D65F8]' },
  BANK:     { label: 'Bank',     color: 'text-[#374151]' },
  ERP:      { label: 'ERP/GL',   color: 'text-[#374151]' },
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const CustomTransactionNode: React.FC<any> = ({ data }: { data: TransactionNodeData }) => {
  const d = data as TransactionNodeData;
  const style = STATUS_STYLES[d.status] ?? STATUS_STYLES.PENDING;
  const src   = SOURCE_CONFIG[d.source];

  const fmtInr = (paise: number) =>
    (paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  return (
    <div
      onClick={() => d.onSelect?.(d.txnId)}
      className={`
        bg-white border border-[#E5E7EB] border-l-[3px] ${style.accent}
        rounded-lg shadow-card
        min-w-[240px] w-[240px] min-h-[146px] h-[146px]
        cursor-pointer select-none
        hover:shadow-panel hover:-translate-y-px
        transition-all duration-150
        flex flex-col justify-between p-3
      `}
    >
      {/* Row 1: Source label + status badge */}
      <div className="flex items-center justify-between gap-2">
        <span className={`text-[11px] font-semibold ${src.color}`}>
          {src.label}
        </span>
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-md ${style.badge}`}>
          {style.label}
        </span>
      </div>

      {/* Row 2: Transaction ID */}
      <p
        className="text-[11px] font-mono text-[#374151] truncate leading-none"
        title={d.original_id}
      >
        {d.original_id}
      </p>

      {/* Row 3: Gross Amount */}
      <p className={`text-[17px] font-bold tabular-nums leading-none ${style.amount}`}>
        ₹{fmtInr(d.amount_gross_paise)}
      </p>

      {/* Row 4: Source-specific detail */}
      {d.source === 'RAZORPAY' && (
        <div className="grid grid-cols-2 gap-1.5 pt-2 border-t border-[#F3F4F6]">
          <div>
            <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wide font-medium">MDR</p>
            <p className="text-[11px] font-mono text-[#374151]">₹{fmtInr(d.fee_mdr_paise)}</p>
          </div>
          <div>
            <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wide font-medium">GST</p>
            <p className="text-[11px] font-mono text-[#374151]">₹{fmtInr(d.fee_gst_paise)}</p>
          </div>
        </div>
      )}

      {d.source === 'BANK' && (
        <div className="pt-2 border-t border-[#F3F4F6]">
          <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wide font-medium">Net Credit</p>
          <p className="text-[11px] font-mono text-[#374151]">₹{fmtInr(d.amount_net_paise)}</p>
        </div>
      )}

      {d.source === 'ERP' && (
        <div className="pt-2 border-t border-[#F3F4F6]">
          <p className="text-[9px] text-[#9CA3AF] uppercase tracking-wide font-medium">GL Amount</p>
          <p className="text-[11px] font-mono text-[#374151]">₹{fmtInr(d.amount_gross_paise)}</p>
        </div>
      )}

      {/* UTR reference */}
      {d.utr && (
        <div className="flex items-center gap-1.5 overflow-hidden">
          <span className="text-[9px] text-[#9CA3AF] uppercase tracking-wide font-medium flex-shrink-0">UTR</span>
          <span className="text-[10px] font-mono text-[#6B7280] truncate" title={d.utr}>
            {d.utr}
          </span>
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="!w-2.5 !h-2.5 !bg-white !border !border-[#D1D5DB] !rounded-full"
      />
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2.5 !h-2.5 !bg-white !border !border-[#D1D5DB] !rounded-full"
      />
    </div>
  );
};
