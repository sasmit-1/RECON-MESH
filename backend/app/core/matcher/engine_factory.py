"""
TRIDENT Matcher Engine Dynamic Factory (Step 04)
Implements a dual-mode factory pattern:
  - NATIVE_MATCHER=true  → attempts to load compiled C++ PyBind11 matcher_native module.
  - NATIVE_MATCHER=false → silently falls back to the Python GreedyHeuristicPruner (Step 03).

The NativeMatcher adapter wraps matcher_native results into the same
GreedyHeuristicPruner.prune() tuple contract so callers are fully agnostic
of which engine is active.
"""

import logging
import os
from typing import List, Protocol, Tuple
from uuid import uuid4

from backend.app.core.models import (
    CanonicalTransaction,
    MatchStatus,
    ReconciliationCluster,
)
from backend.app.core.matcher.greedy_pruner import GreedyHeuristicPruner

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MatcherEngine Protocol — structural interface both engines must satisfy
# ---------------------------------------------------------------------------

class MatcherEngine(Protocol):
    """
    Structural Protocol defining the contract for any matching engine variant.
    All callers depend only on this interface, not on a concrete implementation.
    """

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
        ...


# ---------------------------------------------------------------------------
# NativeMatcher — Adapter wrapping matcher_native C++ module results
# ---------------------------------------------------------------------------

class NativeMatcher:
    """
    Adapter that wraps the compiled C++ matcher_native PyBind11 module,
    translating NativeMatchResult objects into ReconciliationCluster instances
    and delegating Stage 2 ERP ledger join to GreedyHeuristicPruner logic.
    """

    def __init__(self, time_window_hours: int = 72) -> None:
        import matcher_native  # type: ignore  # guarded by caller's try/except
        self._lib = matcher_native
        self._time_window_sec = time_window_hours * 3600
        self._native_kernel = matcher_native.NativeHeuristicMatcher(
            int(self._time_window_sec)
        )
        # Stage 2 ERP join uses the Python pruner's cluster-building logic
        self._python_pruner = GreedyHeuristicPruner(time_window_hours)

    def _to_native_txn(self, txn: CanonicalTransaction):
        """Converts a CanonicalTransaction to matcher_native.NativeTransaction."""
        return self._lib.NativeTransaction(
            txn.id,
            txn.utr or "",
            int(txn.amount_net_paise),
            int(txn.timestamp_utc.timestamp()),
            str(txn.metadata.get("settlement_batch_id", "")),
        )

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
        Executes the C++ native 1:1 matching kernel for Stage 1A.
        Falls back to the Python pruner for Stage 1B (batch) and Stage 1C (amount/ts).
        All matched clusters receive Stage 2 ERP ledger join.
        """
        # Build index maps for fast lookup after native matching
        rzp_by_id = {r.id: r for r in rzp_txns}
        bank_by_id = {b.id: b for b in bank_txns}

        # ERP index for Stage 2 join
        erp_by_order: dict[str, List[CanonicalTransaction]] = {}
        for e in erp_txns:
            if e.order_id:
                erp_by_order.setdefault(e.order_id, []).append(e)

        # Convert to native structs
        native_rzp = [self._to_native_txn(r) for r in rzp_txns]
        native_bank = [self._to_native_txn(b) for b in bank_txns]

        # Stage 1A: C++ 1:1 UTR + amount + time window match
        raw_matches = self._native_kernel.match_1to1(native_rzp, native_bank)

        settled_clusters: List[ReconciliationCluster] = []
        used_rzp_ids: set[str] = set()
        used_bank_ids: set[str] = set()

        for match in raw_matches:
            r = rzp_by_id.get(match.rzp_id)
            b = bank_by_id.get(match.bank_id)
            if r is None or b is None:
                continue

            used_rzp_ids.add(r.id)
            used_bank_ids.add(b.id)

            # Stage 2: ERP ledger join
            matched_erp: List[CanonicalTransaction] = []
            all_erp_found = True
            if r.order_id:
                if r.order_id in erp_by_order:
                    matched_erp.extend(erp_by_order[r.order_id])
                else:
                    all_erp_found = False
            else:
                all_erp_found = False

            status = MatchStatus.MATCHED if all_erp_found else MatchStatus.SETTLED_PENDING_ERP
            discrepancy = r.amount_net_paise - b.amount_net_paise

            cluster = ReconciliationCluster(
                cluster_id=f"cluster_native_1to1_{uuid4().hex[:8]}",
                razorpay_txns=[r],
                bank_txns=[b],
                erp_txns=matched_erp,
                sum_gross_paise=r.amount_gross_paise,
                sum_net_expected_paise=r.amount_net_paise,
                sum_bank_credit_paise=b.amount_net_paise,
                discrepancy_paise=discrepancy,
                status=status,
            )
            settled_clusters.append(cluster)

        # Stage 1B: C++ 1:N batch settlement match
        matched_rzp_set: set[str] = set(used_rzp_ids)
        matched_bank_set: set[str] = set(used_bank_ids)
        try:
            batch_matches = self._native_kernel.match_1toN_batch(
                native_rzp, native_bank, matched_rzp_set, matched_bank_set
            )
            for b_match in batch_matches:
                batch_rzp = [rzp_by_id[rid] for rid in b_match.rzp_ids if rid in rzp_by_id]
                b = bank_by_id.get(b_match.bank_id)
                if not batch_rzp or b is None:
                    continue

                for r in batch_rzp:
                    used_rzp_ids.add(r.id)
                used_bank_ids.add(b.id)

                matched_erp = []
                all_erp_found = True
                for r in batch_rzp:
                    if r.order_id and r.order_id in erp_by_order:
                        matched_erp.extend(erp_by_order[r.order_id])
                    elif r.order_id:
                        all_erp_found = False
                    elif not r.order_id:
                        all_erp_found = False

                status = MatchStatus.MATCHED if all_erp_found else MatchStatus.SETTLED_PENDING_ERP
                sum_gross = sum(r.amount_gross_paise for r in batch_rzp)
                sum_net_expected = sum(r.amount_net_paise for r in batch_rzp)
                sum_bank_credit = b.amount_net_paise
                discrepancy = sum_net_expected - sum_bank_credit

                cluster = ReconciliationCluster(
                    cluster_id=f"cluster_native_1toN_{uuid4().hex[:8]}",
                    razorpay_txns=batch_rzp,
                    bank_txns=[b],
                    erp_txns=matched_erp,
                    sum_gross_paise=sum_gross,
                    sum_net_expected_paise=sum_net_expected,
                    sum_bank_credit_paise=sum_bank_credit,
                    discrepancy_paise=discrepancy,
                    status=status,
                )
                settled_clusters.append(cluster)
        except Exception as exc:
            logger.debug("Native 1:N batch matching delegated to Python fallback: %s", exc)

        # Delegate remaining unmatched transactions to Python pruner (Stage 1C amount/ts fallback)
        residual_rzp = [r for r in rzp_txns if r.id not in used_rzp_ids]
        residual_bank = [b for b in bank_txns if b.id not in used_bank_ids]

        if residual_rzp or residual_bank:
            py_settled, orphan_rzp, orphan_bank = self._python_pruner.prune(
                residual_rzp, residual_bank, erp_txns
            )
            settled_clusters.extend(py_settled)
            return settled_clusters, orphan_rzp, orphan_bank

        return settled_clusters, [], []


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_matcher_engine() -> MatcherEngine:
    """
    Dynamically resolves the active matcher engine based on the NATIVE_MATCHER env var.

    NATIVE_MATCHER=true  → attempts to load the compiled C++ matcher_native PyBind11 module.
                           Falls back silently to Python if the .so/.pyd is absent.
    NATIVE_MATCHER=false → (default) returns GreedyHeuristicPruner immediately.
    """
    use_native = os.getenv("NATIVE_MATCHER", "false").strip().lower() == "true"

    if use_native:
        try:
            # Trigger native module import inside NativeMatcher constructor
            engine = NativeMatcher()
            logger.info(
                "⚡ C++ Native Heuristic Matcher loaded successfully (matcher_native)."
            )
            return engine  # type: ignore[return-value]
        except ImportError as exc:
            logger.warning(
                f"⚠️  C++ native matcher unavailable ({exc}). "
                "Falling back to Python GreedyHeuristicPruner."
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"⚠️  Unexpected error loading native matcher ({exc}). "
                "Falling back to Python GreedyHeuristicPruner."
            )

    logger.debug("Python GreedyHeuristicPruner active (NATIVE_MATCHER=%s).", use_native)
    return GreedyHeuristicPruner()
