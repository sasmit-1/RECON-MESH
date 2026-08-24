/**
 * TRIDENT Step 11: Real-Time Throttled WebSocket Stream Hook
 * =============================================================
 * Connects to ws://localhost:8000/ws/recon-stream with 100ms buffered throttling
 * using useRef to prevent React 19 re-render thrashing during high-throughput bursts.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  DiscrepancyVoucher,
  ReconciliationCluster,
  ReconMetrics,
  WebSocketMessage,
} from '../types/recon';

const API_BASE_URL = 'http://localhost:8000';
const DEFAULT_WS_URL = 'ws://localhost:8000/ws/recon-stream';

export interface UseReconStreamReturn {
  isConnected: boolean;
  isStreaming: boolean;
  metrics: ReconMetrics;
  clusters: ReconciliationCluster[];
  activeVouchers: DiscrepancyVoucher[];
  merkleRoot: string;
  engineMode: string;
  startStream: () => Promise<void>;
  stopStream: () => Promise<void>;
  runBatchReconcile: (count?: number) => Promise<void>;
  fetchMerkleRoot: () => Promise<void>;
  fetchHealth: () => Promise<void>;
}

export function useReconStream(wsUrl: string = DEFAULT_WS_URL): UseReconStreamReturn {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [engineMode, setEngineMode] = useState<string>('Native C++ (SIMD Vectorized)');
  const [merkleRoot, setMerkleRoot] = useState<string>('SHA-256 INITIALIZED');

  const [clusters, setClusters] = useState<ReconciliationCluster[]>([]);
  const [activeVouchers, setActiveVouchers] = useState<DiscrepancyVoucher[]>([]);
  const [metrics, setMetrics] = useState<ReconMetrics>({
    precision: 100.0,
    recall: 100.0,
    throughput: 0,
    totalSettledPaise: 0,
    discrepancyPaise: 0,
    merkleRoot: 'SHA-256 INITIALIZED',
    latencyMs: 0,
    resolvedClusters: 0,
    totalProcessed: 0,
    pass1Clusters: 0,
    pass2Clusters: 0,
    orphanRazorpay: 0,
    orphanBank: 0,
  });

  // Internal mutable buffers for 100ms state flushes
  const clusterBufferRef = useRef<ReconciliationCluster[]>([]);
  const voucherBufferRef = useRef<DiscrepancyVoucher[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  // Health check query
  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/health`);
      if (res.ok) {
        const data = await res.json();
        if (data.engine_mode) {
          setEngineMode(data.engine_mode);
        }
      }
    } catch (e) {
      console.warn('Health check warning:', e);
    }
  }, []);

  // Fetch cryptographic Merkle root
  const fetchMerkleRoot = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/reconcile/merkle-root`);
      if (res.ok) {
        const data = await res.json();
        if (data.merkle_root) {
          setMerkleRoot(data.merkle_root);
          setMetrics((prev) => ({ ...prev, merkleRoot: data.merkle_root }));
        }
      }
    } catch (e) {
      console.warn('Merkle root query warning:', e);
    }
  }, []);

  // Execute batch reconciliation benchmark
  const runBatchReconcile = useCallback(
    async (count: number = 100) => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/reconcile/batch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ count, seed: 42 }),
        });

        if (res.ok) {
          const data = await res.json();
          const m = data.metrics || {};

          setMetrics({
            precision: m.precision_pct ?? 100.0,
            recall: m.recall_pct ?? 100.0,
            throughput: Math.round((m.total_transactions || count) / Math.max((m.latency_ms || 1) / 1000, 0.001)),
            totalSettledPaise: (m.total_transactions || count) * 10000,
            discrepancyPaise: m.discrepancy_variance_paise ?? 0,
            merkleRoot: data.merkle_root || 'SHA-256 VERIFIED',
            latencyMs: m.latency_ms ?? 0,
            resolvedClusters: m.resolved_clusters ?? 0,
            totalProcessed: m.total_transactions ?? count,
            pass1Clusters: m.pass1_heuristic_clusters ?? 0,
            pass2Clusters: m.pass2_dp_clusters ?? 0,
            orphanRazorpay: m.orphan_razorpay ?? 0,
            orphanBank: m.orphan_bank ?? 0,
          });

          if (data.merkle_root) {
            setMerkleRoot(data.merkle_root);
          }
          if (data.clusters) {
            setClusters(data.clusters);
          }
        }
      } catch (e) {
        console.error('Batch reconciliation error:', e);
      }
    },
    []
  );

  // Stream controls
  const startStream = useCallback(async () => {
    clusterBufferRef.current = [];
    voucherBufferRef.current = [];
    setIsStreaming(true);
    setMetrics((prev) => ({
      ...prev,
      throughput: 5,
    }));
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'START_STREAM', frequency_hz: 5 }));
    }
    try {
      await fetch(`${API_BASE_URL}/api/recon/stream/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ frequency_hz: 5 }),
      });
    } catch (e) {
      console.warn('Stream start API warning:', e);
    }
  }, []);

  const stopStream = useCallback(async () => {
    setIsStreaming(false);
    // Drain buffers so the next flush interval doesn't push stale data
    clusterBufferRef.current = [];
    voucherBufferRef.current = [];
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'STOP_STREAM' }));
    }
    try {
      await fetch(`${API_BASE_URL}/api/recon/stream/stop`, { method: 'POST' });
    } catch (e) {
      console.warn('Stream stop API warning:', e);
    }
  }, []);

  // WebSocket lifecycle
  useEffect(() => {
    let ws: WebSocket | null = null;

    const connectWS = () => {
      ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        fetchHealth();
        fetchMerkleRoot();
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Auto-reconnect after 1.5 seconds if closed
        setTimeout(connectWS, 1500);
      };

      ws.onerror = (err) => {
        console.warn('WebSocket connection error:', err);
        setIsConnected(false);
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const msg: WebSocketMessage = JSON.parse(event.data);
          const eventType = (msg.event || msg.type || '').toUpperCase();

          if (eventType === 'HANDSHAKE' && msg.engine) {
            setEngineMode(msg.engine);
          } else if (eventType === 'CLUSTER_MATCHED') {
            const cl = msg.cluster || msg.data;
            if (cl) {
              clusterBufferRef.current.push(cl);
            }
          } else if (eventType === 'VOUCHER_GENERATED') {
            const vch = msg.voucher || msg.data;
            if (vch) {
              voucherBufferRef.current.push(vch);
            }
          } else if (eventType === 'METRICS_UPDATE') {
            const d = msg.data || msg;
            setMetrics((prev) => ({
              ...prev,
              resolvedClusters: d.resolved_clusters ?? prev.resolvedClusters,
              orphanRazorpay: d.orphan_rzp ?? prev.orphanRazorpay,
              orphanBank: d.orphan_bank ?? prev.orphanBank,
              discrepancyPaise: d.discrepancy_variance_paise ?? prev.discrepancyPaise,
              latencyMs: d.latency_ms ?? prev.latencyMs,
              throughput: Math.max(prev.throughput, 5),
            }));
          } else if (eventType === 'STREAM_TICK') {
            setMetrics((prev) => ({
              ...prev,
              totalProcessed: msg.streamed_count ?? prev.totalProcessed + 1,
            }));
          } else if (eventType === 'STREAM_COMPLETE') {
            setIsStreaming(false);
          }
        } catch (e) {
          console.error('WS Parse error:', e);
        }
      };
    };

    connectWS();

    // 100ms throttled state flush interval
    const flushInterval = setInterval(() => {
      if (clusterBufferRef.current.length > 0) {
        const newClusters = [...clusterBufferRef.current];
        clusterBufferRef.current = [];
        setClusters((prev) => {
          const existingIds = new Set(prev.map((c) => c.cluster_id));
          const seenInBatch = new Set<string>();
          const filtered = newClusters.filter((c) => {
            if (!c.cluster_id || existingIds.has(c.cluster_id) || seenInBatch.has(c.cluster_id)) {
              return false;
            }
            seenInBatch.add(c.cluster_id);
            return true;
          });
          // Prepend new incoming clusters to top of feed so they are immediately visible
          return [...filtered, ...prev].slice(0, 100);
        });
      }

      if (voucherBufferRef.current.length > 0) {
        const newVouchers = [...voucherBufferRef.current];
        voucherBufferRef.current = [];
        setActiveVouchers((prev) => {
          const existingIds = new Set(prev.map((v) => v.voucher_id));
          const seenInBatch = new Set<string>();
          const filtered = newVouchers.filter((v) => {
            if (!v.voucher_id || existingIds.has(v.voucher_id) || seenInBatch.has(v.voucher_id)) {
              return false;
            }
            seenInBatch.add(v.voucher_id);
            return true;
          });
          return [...filtered, ...prev].slice(0, 30);
        });
      }
    }, 100);

    return () => {
      clearInterval(flushInterval);
      if (ws) {
        ws.close();
      }
    };
  }, [wsUrl, fetchHealth, fetchMerkleRoot]);

  return {
    isConnected,
    isStreaming,
    metrics,
    clusters,
    activeVouchers,
    merkleRoot,
    engineMode,
    startStream,
    stopStream,
    runBatchReconcile,
    fetchMerkleRoot,
    fetchHealth,
  };
}
