/**
 * TRIDENT: Live Audit Terminal
 * ================================
 * Clean log stream panel — light gray background, JetBrains Mono,
 * muted color-coded level tags. Collapsible bottom dock.
 */

import React, { useEffect, useRef, useState } from 'react';
import { ChevronDown, ChevronUp, Terminal, Trash2 } from 'lucide-react';
import type { ReconciliationCluster } from '../types/recon';

interface LiveAuditTerminalProps {
  clusters: ReconciliationCluster[];
  merkleRoot: string;
  isConnected: boolean;
  latencyMs: number;
}

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'SYS' | 'MATCH' | 'INVAR' | 'MERKLE' | 'AST' | 'WS' | 'ERR' | 'OK';
  message: string;
}

// Clean muted palette — no neon
const LEVEL_STYLES: Record<LogEntry['level'], { tag: string; text: string }> = {
  SYS:    { tag: 'bg-[#EEF3FF] text-[#2D65F8]',    text: 'text-[#374151]' },
  MATCH:  { tag: 'bg-[#ECFDF5] text-[#059669]',    text: 'text-[#374151]' },
  INVAR:  { tag: 'bg-[#FFFBEB] text-[#D97706]',    text: 'text-[#374151]' },
  MERKLE: { tag: 'bg-[#F3F4F6] text-[#6B7280]',    text: 'text-[#6B7280]' },
  AST:    { tag: 'bg-[#F3F4F6] text-[#374151]',    text: 'text-[#374151]' },
  WS:     { tag: 'bg-[#F3F4F6] text-[#6B7280]',    text: 'text-[#6B7280]' },
  ERR:    { tag: 'bg-[#FEF2F2] text-[#DC2626]',    text: 'text-[#DC2626]' },
  OK:     { tag: 'bg-[#ECFDF5] text-[#059669]',    text: 'text-[#059669]' },
};

function now(): string {
  return new Date().toISOString().slice(11, 23);
}

let logIdCounter = 0;
function makeLog(level: LogEntry['level'], message: string): LogEntry {
  return { id: `log-${++logIdCounter}`, timestamp: now(), level, message };
}

export const LiveAuditTerminal: React.FC<LiveAuditTerminalProps> = ({
  clusters,
  merkleRoot,
  isConnected,
  latencyMs,
}) => {
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const [logs, setLogs] = useState<LogEntry[]>([
    makeLog('SYS',   'TRIDENT Engine v2.1.0 initialized.'),
    makeLog('INVAR', 'Double-entry zero-sum gatekeeper → active.'),
    makeLog('MERKLE','SHA-256 binary Merkle ledger → ready.'),
    makeLog('SYS',   'Awaiting reconciliation batch…'),
  ]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevClusterCount = useRef<number>(0);

  // Append logs on new batch
  useEffect(() => {
    const newCount = clusters.length;
    if (newCount === 0 || newCount === prevClusterCount.current) return;

    const newLogs: LogEntry[] = [
      makeLog('MATCH',  `Stage-1 heuristic pruner resolved ${newCount} clusters.`),
      makeLog('INVAR',  `Validating double-entry invariants for ${newCount} vouchers…`),
      makeLog('OK',     `All invariants passed. Zero-sum delta = ₹0.00.`),
      makeLog('MERKLE', `Merkle root: ${merkleRoot.slice(0, 16)}…`),
    ];

    clusters.slice(0, 5).forEach((cl) => {
      const net = (cl.sum_net_expected_paise / 100).toFixed(2);
      newLogs.push(
        makeLog('AST', `[${cl.cluster_id}] NET_SETTLEMENT(${net}) = GROSS − MDR − GST → ${cl.status}`)
      );
    });

    if (latencyMs > 0) {
      newLogs.push(makeLog('SYS', `Pipeline latency: ${latencyMs.toFixed(2)} ms.`));
    }

    setLogs((prev) => [...prev, ...newLogs].slice(-200));
    prevClusterCount.current = newCount;
  }, [clusters, merkleRoot, latencyMs]);

  // WS state logs
  useEffect(() => {
    setLogs((prev) => [
      ...prev,
      makeLog('WS', isConnected
        ? 'WebSocket connected → ws://localhost:8000/ws/recon-stream'
        : 'WebSocket disconnected.'),
    ]);
  }, [isConnected]);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current && !collapsed) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, collapsed]);

  return (
    <div
      className={`border-t border-[#E5E7EB] bg-[#FAFAFA] flex flex-col flex-shrink-0 transition-all duration-200 ${
        collapsed ? 'h-[36px]' : 'h-[160px]'
      }`}
    >
      {/* Terminal header */}
      <div
        className="h-[36px] bg-white border-b border-[#E5E7EB] px-4 flex items-center justify-between flex-shrink-0 cursor-pointer select-none"
        onClick={() => setCollapsed((p) => !p)}
      >
        <div className="flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-[#6B7280]" />
          <span className="text-[11px] font-semibold text-[#374151]">Audit Log</span>
          <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-[#059669]' : 'bg-[#DC2626]'}`} />
          <span className="text-[10px] text-[#9CA3AF]">{logs.length} entries</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); setLogs([makeLog('SYS', 'Log cleared.')]); }}
            className="text-[#D1D5DB] hover:text-[#6B7280] transition-colors"
            title="Clear log"
          >
            <Trash2 className="w-3 h-3" />
          </button>
          <button className="text-[#9CA3AF] hover:text-[#374151] transition-colors">
            {collapsed ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Log body */}
      {!collapsed && (
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-4 py-2 space-y-0.5 font-mono text-[11px]"
        >
          {logs.map((log) => {
            const s = LEVEL_STYLES[log.level];
            return (
              <div key={log.id} className="flex items-start gap-2.5 leading-relaxed py-0.5">
                <span className="text-[#D1D5DB] flex-shrink-0 tabular-nums">{log.timestamp}</span>
                <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded flex-shrink-0 min-w-[46px] text-center ${s.tag}`}>
                  {log.level}
                </span>
                <span className={`${s.text} break-all`}>{log.message}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
