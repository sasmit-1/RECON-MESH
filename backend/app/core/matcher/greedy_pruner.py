"""
RECON-MESH 2-Stage Greedy Heuristic Pruner (Step 03)
Implements Pass 1 of the Dual-Pass Recon Kernel using a 2-Stage Matching Architecture:
  Stage 1 (Settlement Layer): Match Razorpay <-> Bank by UTR, net paise, and time window.
  Stage 2 (Ledger Layer):     Join RZP.order_id <-> ERP.order_id, applying SETTLED_PENDING_ERP
                               when the ERP invoice has not yet arrived rather than misflagging orphans.
"""

from collections import defaultdict
from typing import Dict, List, Set, Tuple
from uuid import uuid4

from backend.app.core.models import (
    CanonicalTransaction,
    MatchStatus,
    ReconciliationCluster,
    SourceType,
)
from backend.app.core.matcher.numba_fallback import (
    build_amount_timestamp_arrays,
    numba_greedy_1to1_match,
)


class GreedyHeuristicPruner:
    """
    Pass 1 heuristic pruner for the RECON-MESH Dual-Pass Reconciliation Kernel.

    Architecture:
    - Stage 1A: Strict 1:1 settlement match (UTR + net paise + 72h window).
    - Stage 1B: Metadata-guided 1:N batch settlement match (settlement_batch_id grouping).
    - Stage 2:  ERP ledger join with SETTLED_PENDING_ERP fallback to prevent orphan alert fatigue.
    """

    def __init__(self, time_window_hours: int = 72) -> None:
        self.time_window_sec: int = time_window_hours * 3600

    def prune(
        self,
        rzp_txns: List[CanonicalTransaction],
        bank_txns: List[CanonicalTransaction],
        erp_txns: List[CanonicalTransaction],
    ) -> Tuple[
        List[ReconciliationCluster],
        List[CanonicalTransaction],
        List[CanonicalTransaction],
    ]:
        """
        Executes 2-Stage matching returning:
          - settled_clusters: All resolved reconciliation clusters.
          - orphan_rzp: Razorpay transactions not matched to any bank entry.
          - orphan_bank: Bank entries not matched to any Razorpay transaction.
        """
        # Build ERP index by order_id for O(1) lookup in Stage 2
        erp_by_order: Dict[str, List[CanonicalTransaction]] = defaultdict(list)
        for e in erp_txns:
            if e.order_id:
                erp_by_order[e.order_id].append(e)

        settled_clusters: List[ReconciliationCluster] = []
        used_rzp_ids: Set[str] = set()
        used_bank_ids: Set[str] = set()

        # Build bank indexes for Stage 1A and 1B
        bank_by_utr: Dict[str, List[CanonicalTransaction]] = defaultdict(list)
        for b in bank_txns:
            if b.utr:
                bank_by_utr[b.utr].append(b)

        # ------------------------------------------------------------------ #
        # STAGE 1A: Strict 1:1 UTR + Net Paise + Time Window Match           #
        # ------------------------------------------------------------------ #
        for r in rzp_txns:
            if r.id in used_rzp_ids:
                continue

            # Primary path: UTR-based lookup (sub-millisecond indexed)
            if r.utr and r.utr in bank_by_utr:
                matched_bank: CanonicalTransaction | None = None
                for b in bank_by_utr[r.utr]:
                    if b.id in used_bank_ids:
                        continue
                    if b.amount_net_paise != r.amount_net_paise:
                        continue
                    t_delta = abs(
                        (r.timestamp_utc - b.timestamp_utc).total_seconds()
                    )
                    if t_delta <= self.time_window_sec:
                        matched_bank = b
                        break

                if matched_bank is not None:
                    used_rzp_ids.add(r.id)
                    used_bank_ids.add(matched_bank.id)
                    cluster = self._build_cluster(
                        rzp_txns=[r],
                        bank_txns=[matched_bank],
                        erp_by_order=erp_by_order,
                        cluster_type="1to1",
                    )
                    settled_clusters.append(cluster)

        # ------------------------------------------------------------------ #
        # STAGE 1B: 1:N Batch Settlement via settlement_batch_id grouping    #
        # ------------------------------------------------------------------ #
        # Group unmatched Razorpay transactions by their settlement_batch_id metadata field
        batch_groups: Dict[str, List[CanonicalTransaction]] = defaultdict(list)
        for r in rzp_txns:
            if r.id in used_rzp_ids:
                continue
            batch_id = r.metadata.get("settlement_batch_id")
            if batch_id:
                batch_groups[batch_id].append(r)

        for batch_id, batch_rzp in batch_groups.items():
            # Compute expected net sum for this batch
            batch_net_sum = sum(r.amount_net_paise for r in batch_rzp)

            # Find the single bank credit entry whose amount equals the batch net sum
            matched_bank_entry: CanonicalTransaction | None = None
            for b in bank_txns:
                if b.id in used_bank_ids:
                    continue
                if b.amount_net_paise != batch_net_sum:
                    continue
                # Verify time window against the latest RZP transaction in the batch
                latest_rzp_ts = max(r.timestamp_utc for r in batch_rzp)
                t_delta = abs(
                    (latest_rzp_ts - b.timestamp_utc).total_seconds()
                )
                if t_delta <= self.time_window_sec:
                    matched_bank_entry = b
                    break

            if matched_bank_entry is not None:
                for r in batch_rzp:
                    used_rzp_ids.add(r.id)
                used_bank_ids.add(matched_bank_entry.id)
                cluster = self._build_cluster(
                    rzp_txns=batch_rzp,
                    bank_txns=[matched_bank_entry],
                    erp_by_order=erp_by_order,
                    cluster_type="1toN_batch",
                )
                settled_clusters.append(cluster)

        # ------------------------------------------------------------------ #
        # STAGE 1C: Amount + Timestamp Fallback (no UTR, no batch metadata)  #
        # Uses Numba JIT (or NumPy fallback) for vectorized greedy scan.     #
        # ------------------------------------------------------------------ #
        unmatched_rzp = [r for r in rzp_txns if r.id not in used_rzp_ids]
        unmatched_bank = [b for b in bank_txns if b.id not in used_bank_ids]

        if unmatched_rzp and unmatched_bank:
            rzp_amounts, rzp_timestamps = build_amount_timestamp_arrays(unmatched_rzp)
            bank_amounts, bank_timestamps = build_amount_timestamp_arrays(unmatched_bank)

            pairs = numba_greedy_1to1_match(
                rzp_amounts,
                rzp_timestamps,
                bank_amounts,
                bank_timestamps,
                self.time_window_sec,
            )

            for pair in pairs:
                ri, bi = int(pair[0]), int(pair[1])
                r = unmatched_rzp[ri]
                b = unmatched_bank[bi]
                if r.id in used_rzp_ids or b.id in used_bank_ids:
                    continue
                used_rzp_ids.add(r.id)
                used_bank_ids.add(b.id)
                cluster = self._build_cluster(
                    rzp_txns=[r],
                    bank_txns=[b],
                    erp_by_order=erp_by_order,
                    cluster_type="amount_ts_fallback",
                )
                settled_clusters.append(cluster)

        # Collect residual unmatched items
        orphan_rzp = [r for r in rzp_txns if r.id not in used_rzp_ids]
        orphan_bank = [b for b in bank_txns if b.id not in used_bank_ids]

        return settled_clusters, orphan_rzp, orphan_bank

    def _build_cluster(
        self,
        rzp_txns: List[CanonicalTransaction],
        bank_txns: List[CanonicalTransaction],
        erp_by_order: Dict[str, List[CanonicalTransaction]],
        cluster_type: str,
    ) -> ReconciliationCluster:
        """
        Constructs a ReconciliationCluster and performs Stage 2 ERP ledger join.
        Sets status to MATCHED when all ERP invoices are present, or
        SETTLED_PENDING_ERP when the ERP invoice is temporarily delayed.
        """
        # Stage 2: ERP Ledger Attachment — join on order_id
        matched_erp: List[CanonicalTransaction] = []
        all_erp_found = True

        for r in rzp_txns:
            if r.order_id and r.order_id in erp_by_order:
                matched_erp.extend(erp_by_order[r.order_id])
            elif r.order_id:
                # This RZP order has no ERP invoice yet — ERP is delayed
                all_erp_found = False
            # If no order_id at all, treat as pending ERP (can't join without key)
            elif not r.order_id:
                all_erp_found = False

        status = MatchStatus.MATCHED if all_erp_found else MatchStatus.SETTLED_PENDING_ERP

        sum_gross = sum(r.amount_gross_paise for r in rzp_txns)
        sum_net_expected = sum(r.amount_net_paise for r in rzp_txns)
        sum_bank_credit = sum(b.amount_net_paise for b in bank_txns)
        discrepancy = sum_net_expected - sum_bank_credit

        cluster_id = f"cluster_{cluster_type}_{uuid4().hex[:8]}"

        return ReconciliationCluster(
            cluster_id=cluster_id,
            razorpay_txns=rzp_txns,
            bank_txns=bank_txns,
            erp_txns=matched_erp,
            sum_gross_paise=sum_gross,
            sum_net_expected_paise=sum_net_expected,
            sum_bank_credit_paise=sum_bank_credit,
            discrepancy_paise=discrepancy,
            status=status,
        )
