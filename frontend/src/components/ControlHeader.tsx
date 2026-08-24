/**
 * TRIDENT: Control Header
 * ===========================
 * Razorpay-style top navigation bar — clean white surface,
 * brand blue accents, minimal iconography.
 */

import React, { useState } from 'react';
import { Play, Square, RefreshCw, Zap, Wifi, WifiOff } from 'lucide-react';

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

  return (
    <header className="h-[52px] bg-white border-b border-[#E5E7EB] flex items-center justify-between px-5 flex-shrink-0 select-none">

      {/* Left: Brand */}
      <div className="flex items-center gap-3">
        {/* Razorpay-style wordmark */}
        <div className="flex items-center gap-2">
          {/* Simple brand mark */}
          <div className="w-7 h-7 rounded-md bg-[#2D65F8] flex items-center justify-center flex-shrink-0">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M2 11L6 3h2l2 5h-3l-1 3H2z" fill="white" opacity="0.9"/>
              <path d="M7 8l2-5h3l-2 8h-2L7 8z" fill="white"/>
            </svg>
          </div>
          <div className="flex flex-col leading-none">
            <span className="text-[13px] font-semibold text-[#111827] tracking-tight">
              Trident
            </span>
            <span className="text-[10px] text-[#9CA3AF] font-medium">
              Financial Reconciliation Engine
            </span>
          </div>
        </div>

        {/* Divider */}
        <div className="h-5 w-px bg-[#E5E7EB] mx-1" />

        {/* Engine health indicator */}
        <button
          onClick={onRefreshHealth}
          title="Refresh engine health"
          className="flex items-center gap-1.5 text-[11px] text-[#6B7280] hover:text-[#111827] transition-colors"
        >
          <div className="w-1.5 h-1.5 rounded-full bg-[#059669]" />
          <span className="font-medium">Engine Live</span>
        </button>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">

        {/* Batch runner */}
        <div className="flex items-center gap-1 bg-[#F9FAFB] border border-[#E5E7EB] rounded-lg p-1">
          <span className="text-[10px] text-[#9CA3AF] font-medium px-1.5 hidden md:block">Ingest</span>
          {[100, 500, 1000].map((count) => {
            const isLoading = isProcessingBatch && activeBatchSize === count;
            return (
              <button
                key={count}
                disabled={isProcessingBatch}
                onClick={() => handleBatchClick(count)}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium transition-all duration-150 ${
                  isLoading
                    ? 'bg-[#2D65F8] text-white shadow-sm'
                    : 'text-[#374151] hover:bg-white hover:shadow-sm hover:text-[#2D65F8]'
                }`}
              >
                {isLoading
                  ? <RefreshCw className="w-3 h-3 animate-spin" />
                  : <Zap className="w-3 h-3 opacity-50" />
                }
                <span>{count.toLocaleString()}</span>
              </button>
            );
          })}
        </div>

        {/* Stream toggle */}
        <button
          onClick={isStreaming ? onStopStream : onStartStream}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-[12px] font-semibold transition-all duration-150 border ${
            isStreaming
              ? 'bg-[#FEF2F2] text-[#DC2626] border-[#FECACA] hover:bg-[#FEE2E2]'
              : 'bg-[#2D65F8] text-white border-transparent hover:bg-[#2458DC] shadow-sm'
          }`}
        >
          {isStreaming
            ? <><Square className="w-3 h-3 fill-current" /><span>Stop</span></>
            : <><Play className="w-3 h-3 fill-current" /><span>Start Stream</span></>
          }
        </button>

        {/* Connection pill */}
        <div
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium border ${
            isConnected
              ? 'bg-[#ECFDF5] text-[#059669] border-[#A7F3D0]'
              : 'bg-[#FEF2F2] text-[#DC2626] border-[#FECACA]'
          }`}
        >
          {isConnected
            ? <Wifi className="w-3.5 h-3.5" />
            : <WifiOff className="w-3.5 h-3.5" />
          }
          <span>{isConnected ? 'Connected' : 'Offline'}</span>
        </div>

      </div>
    </header>
  );
};
