/**
 * RECON-MESH Domain Type Definitions
 * Unified Canonical Schemas for Frontend State & Telemetry Streaming.
 */

export type SourceType = 'RAZORPAY' | 'BANK' | 'ERP';

export type MatchStatus =
  | 'PENDING'
  | 'MATCHED'
  | 'SETTLED_PENDING_ERP'
  | 'DISCREPANCY'
  | 'ORPHAN';

export interface CanonicalTransaction {
  id: string;
  source: SourceType;
  original_id: string;
  order_id?: string | null;
  utr?: string | null;
  amount_gross_paise: number;
  fee_mdr_paise: number;
  fee_gst_paise: number;
  amount_net_paise: number;
  currency: string;
  timestamp_utc: string;
  raw_narration?: string | null;
  clean_narration_tokens: string[];
  metadata?: Record<string, any>;
}

export interface ReconciliationCluster {
  cluster_id: string;
  razorpay_txns: CanonicalTransaction[];
  bank_txns: CanonicalTransaction[];
  erp_txns: CanonicalTransaction[];
  sum_gross_paise: number;
  sum_net_expected_paise: number;
  sum_bank_credit_paise: number;
  discrepancy_paise: number;
  status: MatchStatus;
}

export interface DiscrepancyVoucher {
  voucher_id: string;
  cluster_id: string;
  discrepancy_type: string;
  variance_paise: number;
  proposed_adjustment_dsl: string;
  double_entry_balanced: boolean;
  audit_hash: string;
  created_at: string;
}

export interface ReconMetrics {
  precision: number;
  recall: number;
  throughput: number;
  totalSettledPaise: number;
  discrepancyPaise: number;
  merkleRoot: string;
  latencyMs: number;
  resolvedClusters: number;
  totalProcessed: number;
  pass1Clusters: number;
  pass2Clusters: number;
  orphanRazorpay: number;
  orphanBank: number;
}

export interface WebSocketMessage {
  event?: string;
  type?: string;
  data?: any;
  cluster?: any;
  voucher?: any;
  streamed_count?: number;
  matched_clusters_total?: number;
  status?: string;
  engine?: string;
  metrics?: Partial<ReconMetrics>;
  timestamp?: string | number;
  [key: string]: any;
}
