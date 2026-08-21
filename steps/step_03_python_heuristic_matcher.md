# STEP 03: Python Heuristic Fallback Matcher (`numba_fallback.py`, `greedy_pruner.py`)

**Model Recommendation:** Heavier Model (e.g., Sonnet 3.7 / Gemini 1.5 Pro / GPT-4o)  
**Target Files:**  
- `backend/app/core/matcher/numba_fallback.py`  
- `backend/app/core/matcher/greedy_pruner.py`  
**Dependencies:** Python 3.10+, `numpy`, `numba>=0.58` (optional with graceful pure-Python fallback)

---

## 1. Domain Context & Objective
Reconciliation datasets at scale contain thousands of daily transactions. Running an exhaustive combinatorial search across 3 streams simultaneously has $O(2^N)$ computational complexity. 

Furthermore, **ERP invoice feeds and Bank statement credits are asynchronous**:
- For 1:N batch payouts (Pass 1B) and delayed bank settlements (Edge Case 3), an ERP record might arrive with an invoice ID before the bank statement appears, or bank deposits might settle before ERP invoices are fully posted.
- **Tripartite ERP Hazard**: If a matching engine requires all 3 streams simultaneously in Pass 1A, legitimate settlement matches will be mistakenly dropped into the orphan exception queue.

The objective of Step 03 is to build **Pass 1 of the Dual-Pass High-Throughput Kernel** using a **2-Stage Matching Architecture**:
1. **Stage 1 (Settlement Layer)**: Match `Razorpay <-> Bank` (by UTR, amount, and settlement batch).
2. **Stage 2 (Ledger Layer)**: Join `RZP.order_id <-> ERP.order_id`. If the ERP invoice is temporarily delayed, set status to `SETTLED_PENDING_ERP` rather than flagging an orphan/discrepancy.

---

## 2. 2-Stage Matching Pipeline

```
Input: [Razorpay Transactions], [Bank Statements], [ERP Invoices]
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1: SETTLEMENT LAYER (Razorpay <-> Bank)               │
│                                                             │
│ • Pass 1A: 1:1 Strict Settlement Match                      │
│   - RZP.utr == Bank.utr AND                                 │
│   - RZP.net_paise == Bank.credit_paise AND                  │
│   - |Timestamp Delta| <= 72 hours                           │
│                                                             │
│ • Pass 1B: Metadata-Guided 1:N Batch Settlement             │
│   - Group RZP orders by settlement_batch_id                 │
│   - Check SUM(RZP.net_paise) == Bank.credit_paise           │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 2: LEDGER ATTACHMENT (ERP Invoices)                   │
│                                                             │
│ • Index ERP invoices by order_id.                           │
│ • For each settled Razorpay/Bank cluster:                   │
│   - If ALL corresponding ERP invoices found:                │
│       cluster.status = MATCHED                              │
│   - If ERP invoice is missing/delayed:                      │
│       cluster.status = SETTLED_PENDING_ERP                  │
│       (Prevents false orphan alert fatigue)                 │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
Output: (Settled_Clusters, Residual_Orphan_Razorpay, Residual_Orphan_Bank)
```

---

## 3. Implementation Details

### A. Numba Acceleration Layer (`backend/app/core/matcher/numba_fallback.py`)
- Vectorizes amounts and timestamps into 1D 64-bit integer NumPy arrays:
  - `rzp_amounts = np.array([...], dtype=np.int64)`
  - `rzp_timestamps = np.array([...], dtype=np.int64)` (Unix seconds)
  - `bank_amounts = np.array([...], dtype=np.int64)`
  - `bank_timestamps = np.array([...], dtype=np.int64)`
- Implements a `@numba.jit(nopython=True, fastmath=True)` greedy linear scan:
  ```python
  @njit(fastmath=True)
  def numba_greedy_1to1_match(
      rzp_amounts: np.ndarray,
      rzp_timestamps: np.ndarray,
      bank_amounts: np.ndarray,
      bank_timestamps: np.ndarray,
      max_time_diff_sec: int = 259200 # 72 hours
  ) -> np.ndarray:
      # Returns paired index matrix: shape (M, 2)
  ```
- If Numba fails to import or compile on target architecture, falls back cleanly to a pure Python / NumPy vectorized implementation without raising exceptions.

### B. 2-Stage Heuristic Pruner Wrapper (`backend/app/core/matcher/greedy_pruner.py`)
- Provides the class:
  ```python
  from typing import List, Dict
  from backend.app.core.models import CanonicalTransaction, ReconciliationCluster, MatchStatus

  class GreedyHeuristicPruner:
      def __init__(self, time_window_hours: int = 72):
          self.time_window_sec = time_window_hours * 3600

      def prune(
          self,
          rzp_txns: List[CanonicalTransaction],
          bank_txns: List[CanonicalTransaction],
          erp_txns: List[CanonicalTransaction]
      ) -> tuple[List[ReconciliationCluster], List[CanonicalTransaction], List[CanonicalTransaction]]:
          """
          Executes 2-Stage matching:
          Stage 1: Settlement match (RZP <-> Bank)
          Stage 2: Ledger join (RZP <-> ERP) with SETTLED_PENDING_ERP support.
          """
          # 1. Index ERP by order_id
          erp_by_order: Dict[str, CanonicalTransaction] = {
              e.order_id: e for e in erp_txns if e.order_id
          }

          settled_clusters: List[ReconciliationCluster] = []
          used_rzp_ids = set()
          used_bank_ids = set()

          # Build UTR index on bank entries
          bank_by_utr: Dict[str, List[CanonicalTransaction]] = {}
          for b in bank_txns:
              if b.utr:
                  bank_by_utr.setdefault(b.utr, []).append(b)

          # Stage 1A: 1:1 UTR & Amount Match
          for r in rzp_txns:
              if r.id in used_rzp_ids or not r.utr:
                  continue

              candidates = bank_by_utr.get(r.utr, [])
              for b in candidates:
                  if b.id in used_bank_ids:
                      continue
                  if b.amount_net_paise == r.amount_net_paise:
                      time_delta = abs((r.timestamp_utc - b.timestamp_utc).total_seconds())
                      if time_delta <= self.time_window_sec:
                          used_rzp_ids.add(r.id)
                          used_bank_ids.add(b.id)

                          # Stage 2: ERP Join
                          matched_erp: List[CanonicalTransaction] = []
                          status = MatchStatus.SETTLED_PENDING_ERP
                          if r.order_id and r.order_id in erp_by_order:
                              matched_erp.append(erp_by_order[r.order_id])
                              status = MatchStatus.MATCHED

                          cluster = ReconciliationCluster(
                              cluster_id=f"cluster_1to1_{r.id}",
                              razorpay_txns=[r],
                              bank_txns=[b],
                              erp_txns=matched_erp,
                              sum_gross_paise=r.amount_gross_paise,
                              sum_net_expected_paise=r.amount_net_paise,
                              sum_bank_credit_paise=b.amount_net_paise,
                              discrepancy_paise=0,
                              status=status
                          )
                          settled_clusters.append(cluster)
                          break

          # Stage 1B: Batch settlement grouping (by settlement_batch_id)
          # ... (Batch grouping logic)

          orphan_rzp = [r for r in rzp_txns if r.id not in used_rzp_ids]
          orphan_bank = [b for b in bank_txns if b.id not in used_bank_ids]

          return settled_clusters, orphan_rzp, orphan_bank
  ```

---

## 4. Standalone Verification Command
```bash
python -c "
from datetime import datetime, timezone
from backend.app.core.models import CanonicalTransaction, SourceType, MatchStatus
from backend.app.core.matcher.greedy_pruner import GreedyHeuristicPruner

# Case 1: RZP + Bank match, ERP present -> MATCHED
t1 = CanonicalTransaction(id='rzp_1', source=SourceType.RAZORPAY, original_id='pay_1', order_id='ord_1', utr='UTR100', amount_gross_paise=100000, amount_net_paise=97640, timestamp_utc=datetime.now(timezone.utc))
b1 = CanonicalTransaction(id='bnk_1', source=SourceType.BANK, original_id='stmt_1', utr='UTR100', amount_gross_paise=97640, amount_net_paise=97640, timestamp_utc=datetime.now(timezone.utc))
e1 = CanonicalTransaction(id='erp_1', source=SourceType.ERP, original_id='inv_1', order_id='ord_1', amount_gross_paise=100000, amount_net_paise=97640, timestamp_utc=datetime.now(timezone.utc))

# Case 2: RZP + Bank match, ERP delayed -> SETTLED_PENDING_ERP
t2 = CanonicalTransaction(id='rzp_2', source=SourceType.RAZORPAY, original_id='pay_2', order_id='ord_2', utr='UTR200', amount_gross_paise=200000, amount_net_paise=195280, timestamp_utc=datetime.now(timezone.utc))
b2 = CanonicalTransaction(id='bnk_2', source=SourceType.BANK, original_id='stmt_2', utr='UTR200', amount_gross_paise=195280, amount_net_paise=195280, timestamp_utc=datetime.now(timezone.utc))

pruner = GreedyHeuristicPruner()
settled, r_orphans, b_orphans = pruner.prune([t1, t2], [b1, b2], [e1])

assert len(settled) == 2
assert settled[0].status == MatchStatus.MATCHED
assert settled[1].status == MatchStatus.SETTLED_PENDING_ERP
assert len(r_orphans) == 0
assert len(b_orphans) == 0
print('✅ Step 03 2-Stage Python Heuristic Matcher Verified Successfully!')
"
```
