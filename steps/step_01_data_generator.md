# STEP 01: Ground-Truth Synthetic Data Generator (`generator.py`)

**Model Recommendation:** Lighter Model (e.g., Flash / Claude 3.5 Haiku / GPT-4o-mini)  
**Target Files:**  
- `backend/app/benchmark/generator.py`  
- `benchmark_results/ground_truth_100.json` (auto-generated output)  
**Dependencies:** Python 3.10+, `pydantic`, `pytest` (standard library only for generator)

---

## 1. Domain Context & Objective
In 3-way financial reconciliation, modern FinOps teams reconcile transactions across three disparate sources:
1. **Razorpay Webhooks Feed** (gross order captures, refund line-items, merchant discount rate [MDR] fee deductions, 18% GST).
2. **Bank Feeds (CAMT.053 / MT940)** (net lump-sum settlement credits, processing deductions, truncated UTRs, banking holiday lag).
3. **ERP / General Ledger Invoices (Zoho Books / Tally Prime)** (accounts receivable, invoices raised, customer payment intents).

The objective of Step 01 is to build a standalone, deterministic synthetic dataset generator (`generator.py`) that produces a realistic 100-record benchmark dataset (`ground_truth_100.json` and optionally CSV exports). This dataset is the foundational ground truth for the entire system and tests all 5 enterprise edge cases specified in the RECON-MESH architecture.

---

## 2. The 5 Enterprise Edge Cases to Generate

1. **MDR Fee Split & 18% GST Drift (1:1 with Fee Extraction)**:
   - Order Gross: ₹1,00,000 (10,000,000 paise).
   - Razorpay fee: 2.0% MDR (₹2,000 = 200,000 paise) + 18% GST on MDR (₹360 = 36,000 paise). Total deduction = ₹2,360 (236,000 paise).
   - Net Bank Credit: ₹97,640 (9,764,000 paise).
   - Bank Narration: `CMS/RZP/PAY_1001/MUMBAI`.

2. **1-to-N Batching with Concurrent Partial Refunds (1:N Settlement)**:
   - A single lump-sum bank deposit (e.g., ₹4,85,200) settling 52 distinct payments minus 3 customer refund debits and aggregate MDR/GST.
   - Bank Narration: `NEFT-RZP-SETTLE-BATCH-8902-HDFC`.

3. **Multi-Day Bank Holiday Timing Lag (Temporal Desynchronization)**:
   - Friday 23:58 IST payment captures settling on Tuesday 10:15 IST due to 2nd Saturday / Sunday / RBI holiday.
   - Timestamps reflect 3-4 days difference while referencing identical settlement cycle IDs.

4. **Chargeback Hold & Escrow Variance (Discrepancy Exception)**:
   - Order ₹12,000; Customer refunded ₹4,000; Bank credit is ₹7,600 with ₹400 held in dispute escrow reserve.
   - Anomaly flag that tests the AI Agent & AST evaluator.

5. **Fuzzy & Truncated Bank UTRs (Narration Noise)**:
   - Razorpay Transaction ID: `RZP_TXN_9876543210`.
   - Bank UTR truncated: `987654321` or formatted as `UPI/9876543210/PAY/RZP`.

---

## 3. Data Schema & Exact Structure

The generator must output a single JSON document with three lists representing the three sources, plus a ground-truth mapping key:

```json
{
  "benchmark_metadata": {
    "version": "2.1",
    "record_count": 100,
    "seed": 42,
    "total_gross_paise": 58920400,
    "total_net_paise": 57534720,
    "total_mdr_paise": 1178400,
    "total_gst_paise": 212280
  },
  "razorpay_events": [
    {
      "event_id": "evt_rzp_001",
      "order_id": "order_Hk928a",
      "payment_id": "pay_9876543210",
      "amount_gross_paise": 10000000,
      "fee_mdr_paise": 200000,
      "fee_gst_paise": 36000,
      "amount_net_paise": 9764000,
      "currency": "INR",
      "status": "captured",
      "timestamp": "2026-08-21T10:30:00Z",
      "utr": "9876543210",
      "metadata": {"customer_email": "user1@enterprise.in", "settlement_batch_id": "batch_001"}
    }
  ],
  "bank_statements": [
    {
      "bank_entry_id": "bnk_stmt_001",
      "account_number": "XXXXXX4590",
      "credit_amount_paise": 9764000,
      "debit_amount_paise": 0,
      "value_date": "2026-08-21",
      "timestamp": "2026-08-21T15:45:00Z",
      "narration": "CMS/RZP/9876543210/MUM",
      "extracted_utr": "9876543210",
      "bank_code": "HDFC"
    }
  ],
  "erp_invoices": [
    {
      "invoice_id": "INV-2026-001",
      "order_id": "order_Hk928a",
      "customer_id": "cust_901",
      "invoice_amount_paise": 10000000,
      "status": "PAID",
      "issue_date": "2026-08-21T09:00:00Z",
      "gl_account": "Accounts Receivable - Razorpay"
    }
  ],
  "ground_truth_matches": [
    {
      "match_id": "match_001",
      "type": "ONE_TO_ONE",
      "razorpay_event_ids": ["evt_rzp_001"],
      "bank_entry_ids": ["bnk_stmt_001"],
      "erp_invoice_ids": ["INV-2026-001"],
      "edge_case_type": "MDR_GST_SPLIT",
      "discrepancy_paise": 0,
      "expected_status": "MATCHED"
    }
  ]
}
```

---

## 4. Implementation Requirements for `generator.py`

1. **Deterministic Random Seed**: Fix `random.seed(42)` and generate reproducible data so every run produces byte-identical outputs.
2. **Strict Integer Paise Precision**: All currency amounts must be stored as 64-bit integers (`int` in paise). ₹1.00 = 100 paise. Never use floating-point types (`float`) for currency amounts.
3. **5 Edge-Case Distribution**:
   - 60% Standard 1:1 matches with MDR (2.0%) + GST (18% of MDR).
   - 20% 1:N Batch Settlements (batch deposits aggregating 3 to 10 orders each).
   - 10% Bank Holiday / Weekend Temporal Lag (capture on Friday/Saturday, settled 3-4 days later).
   - 5% Partial Refunds & Chargeback Hold anomalies.
   - 5% Fuzzy / Truncated Bank UTRs.
4. **Export Formats**:
   - Save JSON benchmark to `benchmark_results/ground_truth_100.json`.
   - Implement `stream_synthetic_events(rate_hz=1.0)` generator yielding live events with simulated timestamp intervals.
5. **Standalone Execution CLI**:
   ```bash
   python -m app.benchmark.generator --count 100 --out benchmark_results/ground_truth_100.json
   ```

---

## 5. Standalone Verification Command
```bash
python -c "
import json
from backend.app.benchmark.generator import generate_ground_truth_dataset
data = generate_ground_truth_dataset(count=100, seed=42)
assert len(data['razorpay_events']) >= 100
assert len(data['bank_statements']) >= 20
assert len(data['erp_invoices']) >= 100
assert len(data['ground_truth_matches']) > 0
print('✅ Step 01 Synthetic Generator Verified Successfully!')
"
```
