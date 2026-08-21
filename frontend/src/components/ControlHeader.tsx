/**
 * RECON-MESH Step 11: Control Header Component
 * ============================================
 * Compact 44px AMOLED top bar containing engine status badges, live stream controls,
 * batch ingestion triggers (100, 500, 1000 txns), and WebSocket connection indicators.
 */

import React, { useState } from 'react';
import {
  Activity,
  Cpu,
  Play,
  RefreshCw,
  ShieldCheck,
  Square,
  Zap,
} from 'lucide-react';

interface ControlHeaderProps {
  isConnected: boolean;
  isStreaming: boolean;
  engineMode: string;
  onStartStream: () => void;
  onStopStream: () => void;
  onRunBatch: (count: number) => Promise<void>;
  onRefreshHealth: () => void;
}

export const ControlHeader: React.FC<ControlHeaderProps> = ({
  isConnected,
  isStreaming,
  engineMode,
  onStartStream,
  onStopStream,
  onRunBatch,
  onRefreshHealth,
}) => {
  const [isProcessingBatch, setIsProcessingBatch] = useState<boolean>(false);
  const [activeBatchSize, setActiveBatchSize] = useState<number | null>(null);

  const handleBatchClick = async (count: number) => {
    setIsProcessingBatch(true);
    setActiveBatchSize(count);
    try {
      await onRunBatch(count);
    } finally {
      setIsProcessingBatch(false);
      setActiveBatchSize(null);
    }
  };

  const isNative = engineMode.toLowerCase().includes('native') || engineMode.toLowerCase().includes('c++');

  return (
    <header className="flex items-center justify-between px-4 py-2.5 bg-black border-b border-[#27272a] select-none flex-shrink-0 h-[48px]">
      {/* Left: Brand logo & Engine Status Badges */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2">
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              isConnected ? 'bg-[#00FF66] animate-pulse' : 'bg-[#FF3366]'
            }`}
          />
          <span className="text-[13px] font-semibold tracking-wider text-[#EDEDED] uppercase font-mono">
            RECON-MESH
          </span>
          <span className="text-[10px] font-mono text-[#888888] bg-[#111111] border border-[#222222] px-1.5 py-0.5 rounded">
            v2.1
          </span>
        </div>

        <div className="h-3.5 w-[1px] bg-[#222222]" />

        {/* Engine Mode Pill */}
        <div
          onClick={onRefreshHealth}
          className="cursor-pointer px-2 py-0.5 text-[11px] font-mono rounded bg-[#0A0A0A] hover:bg-[#121212] border border-[#222222] text-[#888888] hover:text-[#EDEDED] flex items-center space-x-1.5 transition-colors"
          title="Click to refresh engine health check"
        >
          <Cpu className={`w-3.5 h-3.5 ${isNative ? 'text-[#00FF66]' : 'text-[#0C8CE9]'}`} />
          <span>{isNative ? 'C++ NATIVE (SIMD)' : 'PYTHON NUMBA (JIT)'}</span>
        </div>

        {/* Zero-Egress Invariant Pill */}
        <div className="hidden sm:flex items-center space-x-1 px-2 py-0.5 text-[11px] font-mono rounded bg-[#0A0A0A] border border-[#222222] text-[#888888]">
          <ShieldCheck className="w-3.5 h-3.5 text-[#00FF66]" />
          <span>0-EGRESS EDGE INVARIANTS</span>
        </div>
      </div>

      {/* Right: Controls - Stream Toggle & Batch Runners */}
      <div className="flex items-center space-x-3">

        {/* Batch Ingestion Runner Buttons */}
        <div className="flex items-center bg-[#0D0D0D] border border-[#222222] rounded p-0.5">
          <span className="text-[10px] font-mono text-[#888888] px-2 hidden md:inline">
            RUN BENCHMARK:
          </span>
          {[100, 500, 1000].map((count) => {
            const isLoading = isProcessingBatch && activeBatchSize === count;
            return (
              <button
                key={count}
                disabled={isProcessingBatch}
                onClick={() => handleBatchClick(count)}
                className={`px-2 py-1 text-[11px] font-mono rounded transition-colors flex items-center space-x-1 ${
                  isLoading
                    ? 'bg-[#00FF66] text-[#000000] font-semibold'
                    : 'text-[#888888] hover:text-[#EDEDED] hover:bg-[#1A1A1A]'
                }`}
              >
                {isLoading ? (
                  <RefreshCw className="w-3 h-3 animate-spin" />
                ) : (
                  <Zap className="w-3 h-3 text-[#FFB800]" />
                )}
                <span>{count}</span>
              </button>
            );
          })}
        </div>

        {/* WebSocket Stream Toggle */}
        <button
          onClick={isStreaming ? onStopStream : onStartStream}
          className={`px-3 py-1 text-[11px] font-mono rounded border flex items-center space-x-1.5 transition-colors font-semibold ${
            isStreaming
              ? 'bg-[rgba(255,51,102,0.1)] text-[#FF3366] border-[rgba(255,51,102,0.3)] hover:bg-[rgba(255,51,102,0.2)]'
              : 'bg-[rgba(0,255,102,0.1)] text-[#00FF66] border-[rgba(0,255,102,0.3)] hover:bg-[rgba(0,255,102,0.2)]'
          }`}
        >
          {isStreaming ? (
            <>
              <Square className="w-3 h-3 fill-current" />
              <span>STOP STREAM</span>
            </>
          ) : (
            <>
              <Play className="w-3 h-3 fill-current" />
              <span>START STREAM</span>
            </>
          )}
        </button>

        {/* Connection Status Pill */}
        <div
          className={`px-2 py-1 text-[10px] font-mono rounded border flex items-center space-x-1 ${
            isConnected
              ? 'bg-[rgba(0,255,102,0.05)] text-[#00FF66] border-[rgba(0,255,102,0.2)]'
              : 'bg-[rgba(255,51,102,0.05)] text-[#FF3366] border-[rgba(255,51,102,0.2)]'
          }`}
        >
          <Activity className="w-3 h-3" />
          <span>{isConnected ? 'LIVE WS' : 'OFFLINE'}</span>
        </div>

      </div>
    </header>
  );
};
