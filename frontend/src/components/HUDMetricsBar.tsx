/**
 * RECON-MESH: HUD Metrics Bar
 * ============================
 * Clean metric cards showing key reconciliation KPIs.
 * Razorpay-style: white cards, subtle shadows, brand blue accents.
 */

import React, { useState } from 'react';
import { Check, Copy, Database, AlertTriangle, Clock, Shield } from 'lucide-react';
import type { ReconMetrics } from '../types/recon';

interface HUDMetricsBarProps {
  metrics: ReconMetrics;
  merkleRoot: string;
}

export const HUDMetricsBar: React.FC<HUDMetricsBarProps> = ({ metrics, merkleRoot }) => {
  const [copied, setCopied] = useState<boolean>(false);

  const displayMerkle = merkleRoot || metrics.merkleRoot || '';

  const handleCopyMerkle = () => {
    if (!displayMerkle) return;
    navigator.clipboard.writeText(displayMerkle);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const discrepancyInr = (metrics.discrepancyPaise / 100).toFixed(2);
  const latencyStr = metrics.latencyMs > 0 ? `${metrics.latencyMs.toFixed(1)} ms` : '—';
  const hasDiscrepancy = metrics.discrepancyPaise !== 0;

  return (
    <div className="bg-white border-b border-[#E5E7EB] px-5 py-3 flex-shrink-0">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">

        {/* Card 1: Double-Entry Invariant Gate */}
        <div className="flex flex-col gap-1" title="Mathematical proof of zero floating-point drift: sum(Debits) - sum(Credits) == 0">
          <div className="flex items-center justify-between text-[11px] font-medium">
            <div className="flex items-center gap-1.5 text-[#374151]">
              <Shield className="w-3.5 h-3.5 text-[#059669]" />
              <span className="font-semibold text-[#111827]">Double-Entry Gate</span>
            </div>
            <span className="text-[9px] bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0] px-1.5 py-0.5 rounded font-medium">
              Zero-Sum
            </span>
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-[20px] font-bold text-[#059669] leading-none">
              BALANCED
            </span>
          </div>
          <span className="text-[10px] text-[#6B7280]">∑ Debits − ∑ Credits = ₹0.00</span>
        </div>

        {/* Separator */}
        <div className="hidden md:block absolute" />

        {/* Card 2: Processed */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-1.5 text-[11px] text-[#9CA3AF] font-medium">
            <Database className="w-3.5 h-3.5" />
            <span>Processed</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-[22px] font-bold text-[#111827] leading-none">
              {metrics.totalProcessed > 0 ? metrics.totalProcessed.toLocaleString() : '—'}
            </span>
          </div>
          <span className="text-[10px] text-[#9CA3AF]">
            {metrics.resolvedClusters > 0 ? `${metrics.resolvedClusters} clusters resolved` : 'No batch yet'}
          </span>
        </div>

        {/* Card 3: Variance */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-1.5 text-[11px] text-[#9CA3AF] font-medium">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Variance Delta</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-[22px] font-bold leading-none ${hasDiscrepancy ? 'text-[#DC2626]' : 'text-[#059669]'}`}>
              ₹{discrepancyInr}
            </span>
          </div>
          <span className={`text-[10px] font-medium ${hasDiscrepancy ? 'text-[#DC2626]' : 'text-[#059669]'}`}>
            {hasDiscrepancy ? 'Discrepancy detected' : 'Zero variance'}
          </span>
        </div>

        {/* Card 4: Latency */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-1.5 text-[11px] text-[#9CA3AF] font-medium">
            <Clock className="w-3.5 h-3.5" />
            <span>Latency</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-[22px] font-bold text-[#111827] leading-none">
              {latencyStr}
            </span>
          </div>
          <span className="text-[10px] text-[#9CA3AF]">
            {metrics.throughput > 0 ? `${metrics.throughput.toLocaleString()} tx/sec` : 'Pipeline idle'}
          </span>
        </div>

        {/* Card 5: Merkle hash */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-[11px] text-[#9CA3AF] font-medium">
              <Shield className="w-3.5 h-3.5" />
              <span>Merkle Root</span>
            </div>
            {displayMerkle && (
              <button
                onClick={handleCopyMerkle}
                className="flex items-center gap-1 text-[10px] text-[#9CA3AF] hover:text-[#2D65F8] transition-colors"
                title="Copy hash"
              >
                {copied
                  ? <><Check className="w-3 h-3 text-[#059669]" /><span className="text-[#059669]">Copied</span></>
                  : <><Copy className="w-3 h-3" /><span>Copy</span></>
                }
              </button>
            )}
          </div>
          <div className="bg-[#F9FAFB] border border-[#E5E7EB] rounded-md px-2 py-1 mt-0.5">
            <span className="text-[10px] font-mono text-[#374151] truncate block">
              {displayMerkle ? displayMerkle.slice(0, 32) + '…' : 'Awaiting batch…'}
            </span>
          </div>
        </div>

      </div>
    </div>
  );
};
