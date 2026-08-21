# STEP 05: Bounded DP Subset-Sum Solver (`dp_solver.py`)

**Model Recommendation:** Heavier Model (e.g., Sonnet 3.7 / Gemini 1.5 Pro / GPT-4o)  
**Target Files:**  
- `backend/app/core/matcher/dp_solver.py`  
**Dependencies:** Python 3.10+, standard library / `numpy`

---

## 1. Domain Context & Objective
While Pass 1 (C++ / Heuristic Pruner) settles 85–92% of standard 1:1 and metadata-tagged batches, FinOps systems routinely encounter **unindexed 1-to-N settlements with concurrent refunds**. For example:
- A bank deposit of ₹4,85,200 arrives with no clear batch tag.
- It represents the net settlement of 52 specific order payments minus 3 customer refund debits from a pool of leftover orphan transactions.

The objective of Step 05 is to implement **Pass 2: Bounded DP Subset-Sum Matcher** (`dp_solver.py`). By constraining the search to temporal windows of size $K \le 25$ orphan candidates, it achieves exact mathematical subset-sum resolution in $<15\text{ms}$ per window.

---

## 2. Dynamic Programming Formulation & Critical Invariant

Given:
- Target Bank Credit $T$ (in paise)
- Candidate set of $N$ Razorpay transactions: amounts $A = [a_1, a_2, \dots, a_n]$ where $a_i = \text{net\_paise}$ (which **can include negative values for customer refunds**).

### ⚠️ Critical Implementation Rule: Negative Paise Handling
> [!IMPORTANT]
> **DO NOT convert the DP table into a contiguous `numpy.ndarray` or flat list!**  
> Because customer refunds and chargeback debits introduce negative integer paise (e.g. `-10000`), a 1D array DP indexed by `dp[current_sum]` will raise `IndexError` or wrap incorrectly around Python negative indices.  
> You **MUST** use a hash-map `dict[int, list[int]]` where keys are signed 64-bit integer paise sums and values are candidate index paths.

```
┌──────────────────────────────────────────────────────────────┐
│ DP State Formulation:                                        │
│ dp: dict[int, list[int]] = {0: []}                           │
│   • Key: signed integer sum in paise (supports negative sums)│
│   • Value: list of transaction indices forming that sum      │
│                                                              │
│ Optimization & Pruning:                                      │
│ 1. Prefix-sum bounds: if max_possible_sum < T or             │
│    min_possible_sum > T, prune window immediately.           │
│ 2. Max subset size constraint (|S| <= max_cluster_size)      │
│ 3. State memory limit (prune if len(dp) > 50,000 states).    │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Implementation Specification (`backend/app/core/matcher/dp_solver.py`)

```python
from typing import List, Optional, Tuple, Dict
from backend.app.core.models import CanonicalTransaction, ReconciliationCluster, MatchStatus

class BoundedDPSolver:
    def __init__(self, max_cluster_size: int = 25, max_time_window_days: int = 7):
        self.max_cluster_size = max_cluster_size
        self.max_time_window_sec = max_time_window_days * 86400

    def solve_exact_subset_sum(
        self,
        target_net_paise: int,
        candidates: List[CanonicalTransaction]
    ) -> Optional[List[CanonicalTransaction]]:
        """
        Solves bounded subset sum supporting BOTH positive payments and negative refunds.
        Uses a dict-based DP table to safely accommodate negative integer keys without array out-of-bounds.
        """
        if not candidates:
            return None
            
        amounts = [c.amount_net_paise for c in candidates]
        
        # Base state: sum 0 achieved with 0 items
        # Key: signed paise sum (int) -> Value: list of candidate indices
        dp: Dict[int, List[int]] = {0: []}
        
        for idx, amt in enumerate(amounts):
            new_dp: Dict[int, List[int]] = {}
            for current_sum, path in dp.items():
                new_sum = current_sum + amt
                if new_sum == target_net_paise:
                    # Found exact zero-variance match!
                    matched_indices = path + [idx]
                    return [candidates[i] for i in matched_indices]
                
                # Bounded state size to prevent combinatorial explosion
                if len(path) + 1 <= self.max_cluster_size:
                    if new_sum not in dp and new_sum not in new_dp:
                        new_dp[new_sum] = path + [idx]
            
            dp.update(new_dp)
            if len(dp) > 50000:  # Safeguard state memory limit
                break
                
        return None

    def match_residual_orphans(
        self,
        orphan_rzp: List[CanonicalTransaction],
        orphan_bank: List[CanonicalTransaction]
    ) -> Tuple[List[ReconciliationCluster], List[CanonicalTransaction], List[CanonicalTransaction]]:
        """
        Matches leftover orphan bank deposits against combinations of orphan RZP transactions
        within a bounded temporal window.
        """
        matched_clusters: List[ReconciliationCluster] = []
        remaining_rzp = list(orphan_rzp)
        remaining_bank: List[CanonicalTransaction] = []

        for bank_item in orphan_bank:
            # Window filtering: find RZP candidates within timestamp range
            candidates = [
                r for r in remaining_rzp
                if abs((bank_item.timestamp_utc - r.timestamp_utc).total_seconds()) <= self.max_time_window_sec
            ][:self.max_cluster_size]

            solution = self.solve_exact_subset_sum(bank_item.amount_net_paise, candidates)
            if solution:
                cluster = ReconciliationCluster(
                    cluster_id=f"dp_cluster_{bank_item.id}",
                    razorpay_txns=solution,
                    bank_txns=[bank_item],
                    sum_gross_paise=sum(r.amount_gross_paise for r in solution),
                    sum_net_expected_paise=sum(r.amount_net_paise for r in solution),
                    sum_bank_credit_paise=bank_item.amount_net_paise,
                    discrepancy_paise=0,
                    status=MatchStatus.MATCHED
                )
                matched_clusters.append(cluster)
                # Remove matched items from remaining pool
                for r in solution:
                    remaining_rzp.remove(r)
            else:
                remaining_bank.append(bank_item)

        return matched_clusters, remaining_rzp, remaining_bank
```

---

## 4. Standalone Verification Command
```bash
python -c "
from datetime import datetime, timezone
from backend.app.core.models import CanonicalTransaction, SourceType
from backend.app.core.matcher.dp_solver import BoundedDPSolver

# 3 orders with negative refund: 50,000 + 30,000 + (-10,000) = 70,000
r1 = CanonicalTransaction(id='r1', source=SourceType.RAZORPAY, original_id='p1', amount_gross_paise=51000, amount_net_paise=50000, timestamp_utc=datetime.now(timezone.utc))
r2 = CanonicalTransaction(id='r2', source=SourceType.RAZORPAY, original_id='p2', amount_gross_paise=31000, amount_net_paise=30000, timestamp_utc=datetime.now(timezone.utc))
r3 = CanonicalTransaction(id='r3', source=SourceType.RAZORPAY, original_id='p3', amount_gross_paise=-10000, amount_net_paise=-10000, timestamp_utc=datetime.now(timezone.utc))
b1 = CanonicalTransaction(id='b1', source=SourceType.BANK, original_id='b1', amount_gross_paise=70000, amount_net_paise=70000, timestamp_utc=datetime.now(timezone.utc))

solver = BoundedDPSolver()
clusters, rem_r, rem_b = solver.match_residual_orphans([r1, r2, r3], [b1])

assert len(clusters) == 1
assert clusters[0].sum_net_expected_paise == 70000
assert len(rem_r) == 0
assert len(rem_b) == 0
print('✅ Step 05 Bounded DP Solver with Negative Paise Verified Successfully!')
"
```
