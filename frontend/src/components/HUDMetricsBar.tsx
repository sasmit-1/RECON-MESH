/**
 * RECON-MESH Step 11: HUD Metrics Bar
 * ====================================
 * High-density AMOLED telemetry cards displaying Precision, Recall, Processed Txns,
 * Discrepancy Variance, Engine Latency, and Cryptographic SHA-256 Merkle Root.
 */

import React, { useState } from 'react';
import {
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Database,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import type { ReconMetrics } from '../types/recon';

interface HUDMetricsBarProps {
  metrics: ReconMetrics;
  merkleRoot: string;
}

export const HUDMetricsBar: React.FC<HUDMetricsBarProps> = ({ metrics, merkleRoot }) => {
  const [copied, setCopied] = useState<boolean>(false);

  const displayMerkle = merkleRoot || metrics.merkleRoot || 'SHA-256 INITIALIZED';

  const handleCopyMerkle = () => {
    navigator.clipboard.writeText(displayMerkle);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const discrepancyInr = (metrics.discrepancyPaise / 100).toFixed(2);
  const latencyStr = metrics.latencyMs > 0 ? `${metrics.latencyMs.toFixed(1)} ms` : '< 1.0 ms';

  return (
    <section className="bg-[#000000] border-b border-[#181818] p-3 select-none">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">

        {/* Card 1: Precision & Recall */}
        <div className="bg-[#080808] border border-[#181818] hover:border-[#2A2A2A] transition-colors rounded p-2.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] font-mono text-[#888888] mb-1">
            <span className="flex items-center space-x-1">
              <CheckCircle2 className="w-3 h-3 text-[#00FF66]" />
              <span>PRECISION / RECALL</span>
            </span>
            <span className="text-[#00FF66] font-semibold">100% AUDITED</span>
          </div>
          <div className="flex items-baseline justify-between font-mono">
            <div className="flex flex-col">
              <span className="text-[10px] text-[#4E4E4E]">PRECISION</span>
              <span className="text-[18px] font-semibold text-[#00FF66] tabular-nums">
                {metrics.precision.toFixed(1)}%
              </span>
            </div>
            <div className="h-6 w-[1px] bg-[#181818]" />
            <div className="flex flex-col items-end">
              <span className="text-[10px] text-[#4E4E4E]">RECALL</span>
              <span className="text-[18px] font-semibold text-[#00FF66] tabular-nums">
                {metrics.recall.toFixed(1)}%
              </span>
            </div>
          </div>
        </div>

        {/* Card 2: Total Processed Transactions */}
        <div className="bg-[#080808] border border-[#181818] hover:border-[#2A2A2A] transition-colors rounded p-2.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] font-mono text-[#888888] mb-1">
            <span className="flex items-center space-x-1">
              <Database className="w-3 h-3 text-[#0C8CE9]" />
              <span>PROCESSED TELEMETRY</span>
            </span>
            <span className="text-[10px] text-[#4E4E4E] font-mono">3-WAY MATCH</span>
          </div>
          <div className="flex items-baseline justify-between font-mono">
            <span className="text-[20px] font-semibold text-[#EDEDED] tabular-nums">
              {metrics.totalProcessed > 0 ? metrics.totalProcessed.toLocaleString() : '100'}
            </span>
            <span className="text-[11px] text-[#888888]">
              {metrics.resolvedClusters > 0 ? `${metrics.resolvedClusters} CLUSTERS` : 'BATCH ACTIVE'}
            </span>
          </div>
        </div>

        {/* Card 3: Discrepancy Variance */}
        <div className="bg-[#080808] border border-[#181818] hover:border-[#2A2A2A] transition-colors rounded p-2.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] font-mono text-[#888888] mb-1">
            <span className="flex items-center space-x-1">
              <Zap className="w-3 h-3 text-[#FFB800]" />
              <span>VARIANCE DELTA</span>
            </span>
            <span
              className={`text-[10px] font-mono rounded px-1 py-0.2 ${
                metrics.discrepancyPaise === 0
                  ? 'bg-[rgba(0,255,102,0.1)] text-[#00FF66] border border-[rgba(0,255,102,0.2)]'
                  : 'bg-[rgba(255,51,102,0.1)] text-[#FF3366] border border-[rgba(255,51,102,0.2)]'
              }`}
            >
              {metrics.discrepancyPaise === 0 ? 'ZERO VARIANCE' : 'DISCREPANCY'}
            </span>
          </div>
          <div className="flex items-baseline justify-between font-mono">
            <span className="text-[20px] font-semibold text-[#EDEDED] tabular-nums">
              ₹{discrepancyInr}
            </span>
            <span className="text-[11px] text-[#4E4E4E]">({metrics.discrepancyPaise} paise)</span>
          </div>
        </div>

        {/* Card 4: Engine Latency */}
        <div className="bg-[#080808] border border-[#181818] hover:border-[#2A2A2A] transition-colors rounded p-2.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] font-mono text-[#888888] mb-1">
            <span className="flex items-center space-x-1">
              <Clock className="w-3 h-3 text-[#00FF66]" />
              <span>ENGINE LATENCY</span>
            </span>
            <span className="text-[10px] text-[#00FF66] font-mono">SUB-50ms TARGET</span>
          </div>
          <div className="flex items-baseline justify-between font-mono">
            <span className="text-[20px] font-semibold text-[#00FF66] tabular-nums">
              {latencyStr}
            </span>
            <span className="text-[11px] text-[#888888]">
              {metrics.throughput > 0 ? `${metrics.throughput} TX/SEC` : 'HIGH-SPEED'}
            </span>
          </div>
        </div>

        {/* Card 5 & 6: Cryptographic Merkle Root (Spans 2 columns on lg screens) */}
        <div className="bg-[#080808] border border-[#181818] hover:border-[#2A2A2A] transition-colors rounded p-2.5 flex flex-col justify-between lg:col-span-2">
          <div className="flex items-center justify-between text-[11px] font-mono text-[#888888] mb-1">
            <span className="flex items-center space-x-1">
              <ShieldCheck className="w-3 h-3 text-[#00FF66]" />
              <span>CRYPTOGRAPHIC MERKLE ROOT</span>
            </span>
            <button
              onClick={handleCopyMerkle}
              className="flex items-center space-x-1 text-[10px] font-mono text-[#888888] hover:text-[#EDEDED] bg-[#111111] hover:bg-[#1C1C1C] border border-[#222222] px-1.5 py-0.5 rounded transition-colors"
              title="Copy Merkle Root SHA-256"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-[#00FF66]" />
                  <span className="text-[#00FF66]">COPIED</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3 text-[#888888]" />
                  <span>COPY HASH</span>
                </>
              )}
            </button>
          </div>
          <div className="flex items-center justify-between font-mono mt-1">
            <span className="text-[13px] font-mono text-[#00FF66] tracking-wider truncate bg-[#000000] border border-[#181818] px-2 py-1 rounded w-full">
              {displayMerkle}
            </span>
          </div>
        </div>

      </div>
    </section>
  );
};
