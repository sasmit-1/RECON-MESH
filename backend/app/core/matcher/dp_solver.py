"""
RECON-MESH Bounded DP Subset-Sum Solver (Step 05)
Implements Pass 2 of the Dual-Pass Reconciliation Kernel.

Resolves unindexed 1-to-N bank deposits with concurrent customer refunds against
a pool of orphan Razorpay transactions using an exact bounded knapsack DP.

CRITICAL INVARIANT — Negative Paise Handling:
  The DP table is a hash-map `dict[int, list[int]]` with SIGNED integer paise keys.
  A flat list / numpy array MUST NOT be used — customer refund/chargeback debits
  produce negative net_paise values that would trigger IndexError or silent
  negative-index wrapping in any contiguous array structure.
"""

from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from backend.app.core.models import (
    CanonicalTransaction,
    MatchStatus,
    ReconciliationCluster,
)

# Maximum DP state count before abandoning the current window to avoid OOM
_MAX_DP_STATES = 50_000


class BoundedDPSolver:
    """
    Pass 2 exact subset-sum solver for residual orphan reconciliation.

    Processes orphan bank deposits that Pass 1 (heuristic pruner) could not
    resolve — typically untagged 1:N lump-sum credits that aggregate net payments
    minus concurrent customer refund debits.

    Design:
    - dict[int, list[int]] DP table handles signed paise sums safely.
    - max_cluster_size limits combinatorial depth to K ≤ 25.
    - max_time_window_days filters candidates to a temporal neighbourhood.
    - State count guard prunes the search if > 50,000 states accumulate.
    """

    def __init__(
        self,
        max_cluster_size: int = 25,
        max_time_window_days: int = 7,
    ) -> None:
        self.max_cluster_size: int = max_cluster_size
        self.max_time_window_sec: int = max_time_window_days * 86_400

    # ------------------------------------------------------------------
    # Core DP Solver
    # ------------------------------------------------------------------

    def solve_exact_subset_sum(
        self,
        target_net_paise: int,
        candidates: List[CanonicalTransaction],
    ) -> Optional[List[CanonicalTransaction]]:
        """
        Finds the minimal-index subset of `candidates` whose net_paise values
        sum to exactly `target_net_paise`.

        Algorithm:
        - Forward-pass item-by-item DP over a hash-map.
        - New states generated each round are merged into the live table after
          full enumeration of existing states (avoids using the same item twice).
        - Returns the first exact match found, or None if none exists.

        Signed paise invariant:
        - dict keys are arbitrary signed int64 — no array bounds apply.
        - Negative refund amounts (e.g. -10_000 paise) shift keys left and
          are handled identically to positive amounts.
        """
        if not candidates:
            return None

        n = len(candidates)
        amounts = [c.amount_net_paise for c in candidates]

        # Quick feasibility pruning: compute prefix-sum bounds.
        pos_sum = sum(a for a in amounts if a > 0)
        neg_sum = sum(a for a in amounts if a < 0)
        if pos_sum + neg_sum > target_net_paise or pos_sum < target_net_paise - max(0, -neg_sum):
            # Only prune when the target is provably unreachable — otherwise fall through.
            # Restate: if the maximum achievable sum < target OR minimum achievable sum > target, bail.
            max_achievable = pos_sum
            min_achievable = neg_sum
            if max_achievable < target_net_paise or min_achievable > target_net_paise:
                return None

        # DP table: signed paise sum → list of contributing candidate indices
        # Base state: sum of 0 paise achieved with no items selected
        dp: Dict[int, List[int]] = {0: []}

        for idx in range(n):
            amt = amounts[idx]
            # Snapshot current states to avoid using item idx twice in one round
            current_states = list(dp.items())
            new_dp: Dict[int, List[int]] = {}

            for current_sum, path in current_states:
                # Guard: never exceed max_cluster_size items in a subset
                if len(path) >= self.max_cluster_size:
                    continue

                new_sum = current_sum + amt

                # Early-exit: exact match discovered
                if new_sum == target_net_paise:
                    return [candidates[i] for i in (path + [idx])]

                # Only record state if not already reachable by a shorter / earlier path
                if new_sum not in dp and new_sum not in new_dp:
                    new_dp[new_sum] = path + [idx]

            dp.update(new_dp)

            # State memory guard — abandon window if combinatorial explosion occurs
            if len(dp) > _MAX_DP_STATES:
                break

        return None

    # ------------------------------------------------------------------
    # Orphan Resolution Entry Point
    # ------------------------------------------------------------------

    def match_residual_orphans(
        self,
        orphan_rzp: List[CanonicalTransaction],
        orphan_bank: List[CanonicalTransaction],
        erp_invoices: Optional[List[CanonicalTransaction]] = None,
    ) -> Tuple[
        List[ReconciliationCluster],
        List[CanonicalTransaction],
        List[CanonicalTransaction],
    ]:
        """
        Iterates over every orphan bank entry and attempts to find an exact-sum
        subset of orphan Razorpay transactions within the temporal window.

        Matching criteria:
        - |bank.timestamp_utc - rzp.timestamp_utc| ≤ max_time_window_sec
        - SUM(rzp.amount_net_paise for rzp in subset) == bank.amount_net_paise exactly
        - len(subset) ≤ max_cluster_size

        Matched clusters receive:
        - status = MatchStatus.MATCHED
        - discrepancy_paise = 0

        Unresolved bank entries are returned in `remaining_bank` for escalation
        to the AI Agent / Investigator (Step 07).
        """
        matched_clusters: List[ReconciliationCluster] = []
        remaining_rzp: List[CanonicalTransaction] = list(orphan_rzp)
        remaining_bank: List[CanonicalTransaction] = []

        erp_by_order: Dict[str, List[CanonicalTransaction]] = {}
        if erp_invoices:
            from collections import defaultdict
            erp_map = defaultdict(list)
            for e in erp_invoices:
                if e.order_id:
                    erp_map[e.order_id].append(e)
            erp_by_order = erp_map

        for bank_item in orphan_bank:
            # Filter candidates by temporal proximity window ONLY.
            # Do NOT truncate with [: max_cluster_size] here — that would drop valid subset members.
            # Depth-bounding is enforced inside solve_exact_subset_sum() via _MAX_DP_STATES.
            candidates: List[CanonicalTransaction] = [
                r for r in remaining_rzp
                if abs(
                    (bank_item.timestamp_utc - r.timestamp_utc).total_seconds()
                ) <= self.max_time_window_sec
            ]

            if not candidates:
                remaining_bank.append(bank_item)
                continue

            solution = self.solve_exact_subset_sum(
                target_net_paise=bank_item.amount_net_paise,
                candidates=candidates,
            )

            if solution is not None:
                matched_erp: List[CanonicalTransaction] = []
                for r in solution:
                    if r.order_id and r.order_id in erp_by_order:
                        matched_erp.extend(erp_by_order[r.order_id])

                cluster = ReconciliationCluster(
                    cluster_id=f"dp_cluster_{bank_item.id}_{uuid4().hex[:6]}",
                    razorpay_txns=solution,
                    bank_txns=[bank_item],
                    erp_txns=matched_erp,
                    sum_gross_paise=sum(r.amount_gross_paise for r in solution),
                    sum_net_expected_paise=sum(r.amount_net_paise for r in solution),
                    sum_bank_credit_paise=bank_item.amount_net_paise,
                    discrepancy_paise=0,
                    status=MatchStatus.MATCHED,
                )
                matched_clusters.append(cluster)

                # Remove matched RZP items from the candidate pool for subsequent bank items
                matched_ids = {r.id for r in solution}
                remaining_rzp = [r for r in remaining_rzp if r.id not in matched_ids]
            else:
                remaining_bank.append(bank_item)

        return matched_clusters, remaining_rzp, remaining_bank
