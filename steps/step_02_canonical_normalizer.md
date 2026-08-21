# STEP 02: Canonical Normalizer & Data Models (`models.py`, `normalizer.py`)

**Model Recommendation:** Lighter Model (e.g., Flash / Claude 3.5 Haiku / GPT-4o-mini)  
**Target Files:**  
- `backend/app/core/models.py`  
- `backend/app/core/normalizer.py`  
**Dependencies:** Python 3.10+, `pydantic>=2.0`, `python-dateutil`

---

## 1. Domain Context & Objective
Financial telemetry from Razorpay webhooks, core banking switches (MT940/CAMT.053), and ERP systems arrives in heterogeneous formats:
- Timestamps arrive as Unix epochs, ISO-8601 strings with offsets, or IST local dates (`DD/MM/YYYY hh:mm:ss`).
- Bank narrations contain noisy, truncated strings (e.g., `CMS/RZP/PAY_9876543210/MUM/0012` or `NEFT-987654321-INFOSYS`).
- Currency values are frequently provided as floating-point numbers subject to IEEE-754 rounding corruption (e.g., `976.3999999999999`).

The objective of Step 02 is to:
1. Define strict **Pydantic v2 domain models** representing raw events and normalized canonical transactions.
2. Support multi-stage lifecycle statuses: `MATCHED`, `SETTLED_PENDING_ERP` (settlement layer matched, awaiting delayed invoice), `DISCREPANCY`, `ORPHAN`.
3. Build **sanitization & normalization functions** that clean timestamps into standard UTC ISO-8601, extract UTR tokens using regex/token parsing, and compute exact integer paise breakdowns ($\text{Gross} = \text{Net} + \text{MDR} + \text{GST}$).

---

## 2. Pydantic Models Specification (`backend/app/core/models.py`)

```python
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class SourceType(str, Enum):
    RAZORPAY = "RAZORPAY"
    BANK = "BANK"
    ERP = "ERP"

class MatchStatus(str, Enum):
    PENDING = "PENDING"
    MATCHED = "MATCHED"
    SETTLED_PENDING_ERP = "SETTLED_PENDING_ERP"
    DISCREPANCY = "DISCREPANCY"
    ORPHAN = "ORPHAN"

class CanonicalTransaction(BaseModel):
    id: str = Field(..., description="Unique internal canonical UUID")
    source: SourceType
    original_id: str = Field(..., description="Raw source ID (payment_id, bank_entry_id, or invoice_id)")
    order_id: Optional[str] = None
    utr: Optional[str] = None
    amount_gross_paise: int = Field(..., description="Gross amount in exact integer paise")
    fee_mdr_paise: int = Field(default=0, description="MDR fee in paise")
    fee_gst_paise: int = Field(default=0, description="18% GST on MDR in paise")
    amount_net_paise: int = Field(..., description="Net expected bank credit in paise")
    currency: str = "INR"
    timestamp_utc: datetime
    raw_narration: Optional[str] = None
    clean_narration_tokens: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ReconciliationCluster(BaseModel):
    cluster_id: str
    razorpay_txns: List[CanonicalTransaction] = Field(default_factory=list)
    bank_txns: List[CanonicalTransaction] = Field(default_factory=list)
    erp_txns: List[CanonicalTransaction] = Field(default_factory=list)
    sum_gross_paise: int = 0
    sum_net_expected_paise: int = 0
    sum_bank_credit_paise: int = 0
    discrepancy_paise: int = 0
    status: MatchStatus = MatchStatus.PENDING

class DiscrepancyVoucher(BaseModel):
    voucher_id: str
    cluster_id: str
    discrepancy_type: str  # e.g., "MDR_DRIFT", "CHARGEBACK_HOLD", "TIMING_LAG", "PARTIAL_REFUND"
    variance_paise: int
    proposed_adjustment_dsl: str
    double_entry_balanced: bool
    audit_hash: str
    created_at: datetime
```

---

## 3. Normalizer Logic & Requirements (`backend/app/core/normalizer.py`)

1. **`to_paise(amount: float | str | int) -> int`**:
   - Converts standard INR rupee representations into exact integer paise.
   - Example: `976.40` $\rightarrow$ `97640`, `"1,00,000.50"` $\rightarrow$ `10000050`.
   - Uses `decimal.Decimal` with round-half-up quantization to avoid IEEE-754 floating point inaccuracies.

2. **`calculate_mdr_and_gst(gross_paise: int, mdr_rate_bps: int = 200) -> tuple[int, int, int]`**:
   - Returns `(mdr_paise, gst_paise, net_paise)`.
   - `mdr_paise = round(gross_paise * (mdr_rate_bps / 10000))`
   - `gst_paise = round(mdr_paise * 0.18)`
   - `net_paise = gross_paise - mdr_paise - gst_paise`
   - Invariant: `gross_paise - (mdr_paise + gst_paise + net_paise) == 0`.

3. **`parse_iso_utc(date_input: str | int | float | datetime) -> datetime`**:
   - Handles epoch timestamps, IST ISO strings (`+05:30`), and standard banking date formats (`%Y-%m-%d`, `%d/%m/%Y`).
   - Standardizes everything to timezone-aware UTC `datetime` objects.

4. **`extract_clean_utr(narration: str) -> Optional[str]`**:
   - Strips common Indian banking prefixes: `CMS/`, `NEFT/`, `RTGS/`, `IMPS/`, `UPI/`, `INFOSYS/`, `MUM/`.
   - Extracts numeric or alphanumeric UTR tokens (9 to 22 characters).

5. **`normalize_event(raw_event: dict, source: SourceType) -> CanonicalTransaction`**:
   - Complete pipeline function converting any incoming raw payload from Razorpay, Bank, or ERP into a validated `CanonicalTransaction`.

---

## 4. Standalone Verification Command
```bash
python -c "
from backend.app.core.normalizer import to_paise, calculate_mdr_and_gst, extract_clean_utr, parse_iso_utc
from backend.app.core.models import MatchStatus
assert MatchStatus.SETTLED_PENDING_ERP == 'SETTLED_PENDING_ERP'
assert to_paise('1,00,000.50') == 10000050
mdr, gst, net = calculate_mdr_and_gst(10000000, 200) # 2.0% on 1 Lakh
assert mdr == 200000
assert gst == 36000
assert net == 9764000
assert extract_clean_utr('CMS/RZP/PAY9876543210/BLR') == 'PAY9876543210'
print('✅ Step 02 Canonical Normalizer Verified Successfully!')
"
```
