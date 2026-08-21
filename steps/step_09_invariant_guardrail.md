# STEP 09: Deterministic Invariant Gatekeeper, Merkle Audit & Dispatcher (`invariant_gate.py`, `merkle_audit.py`, `dispatcher.py`)

**Model Recommendation:** Lighter Model (e.g., Flash / Claude 3.5 Haiku / GPT-4o-mini)  
**Target Files:**  
- `backend/app/guardrails/invariant_gate.py`  
- `backend/app/guardrails/merkle_audit.py`  
- `backend/app/core/dispatcher.py`  
**Dependencies:** Python 3.10+, `hashlib`, `pydantic`

---

## 1. Domain Context & Objective
In enterprise FinOps, **probabilistic AI outputs can never be trusted blindly with general ledger modifications**. If an LLM makes a math hallucination of even ₹1 (100 paise), the entire company's end-of-year statutory balance sheet will fail an audit. Furthermore, generating static markdown summaries leaves the loop open; human accountants still have to manually key vouchers into ERPs.

The objective of Step 09 is to build:
1. **Deterministic Invariant Gatekeeper (`invariant_gate.py`)**: Enforces strict mathematical zero-sum double-entry accounting ($\sum \text{Debits} - \sum \text{Credits} = 0$) and tax invariant ($\text{GST} = \lfloor \text{MDR} \times 0.18 \rceil$).
2. **Cryptographic Merkle Audit Tree (`merkle_audit.py`)**: Computes SHA-256 tamper-proof Merkle roots across all matched clusters and agent proofs.
3. **Closed-Loop Executable Dispatcher (`dispatcher.py`)**: Transforms verified vouchers into production-ready API payloads for Zoho Books, Tally Prime (XML), and Razorpay Route.

---

## 2. Invariant Math & Gatekeeper (`backend/app/guardrails/invariant_gate.py`)

```python
from typing import List, Dict, Any, Tuple

class InvariantViolationError(Exception):
    pass

class DoubleEntryInvariantGate:
    @staticmethod
    def verify_journal_voucher(journal_entries: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Validates double-entry accounting invariant:
        SUM(Debits) - SUM(Credits) == 0 (down to exact 0 paise).
        """
        total_debits = sum(entry.get("debit_paise", 0) for entry in journal_entries)
        total_credits = sum(entry.get("credit_paise", 0) for entry in journal_entries)

        if total_debits != total_credits:
            diff = total_debits - total_credits
            return False, f"Double-entry violation! Debits ({total_debits}) != Credits ({total_credits}), Discrepancy: {diff} paise"

        if total_debits <= 0:
            return False, "Journal entry cannot have zero or negative total values"

        return True, "ZERO_SUM_INVARIANT_PASSED"

    @staticmethod
    def verify_tax_formula(mdr_paise: int, gst_paise: int) -> bool:
        """
        Validates 18% GST statutory audit invariant:
        GST == round(MDR * 0.18)
        """
        expected_gst = int(round(mdr_paise * 0.18))
        return abs(gst_paise - expected_gst) <= 1  # Allows max 1 paise rounding tolerance
```

---

## 3. Cryptographic Merkle Audit Tree (`backend/app/guardrails/merkle_audit.py`)

```python
import hashlib
from typing import List

class MerkleAuditLedger:
    def __init__(self):
        self.leaf_hashes: List[str] = []

    def add_audit_event(self, event_type: str, payload_str: str) -> str:
        h = hashlib.sha256(f"{event_type}:{payload_str}".encode('utf-8')).hexdigest()
        self.leaf_hashes.append(h)
        return h

    def get_merkle_root(self) -> str:
        if not self.leaf_hashes:
            return hashlib.sha256(b"EMPTY_LEDGER").hexdigest()

        current_level = self.leaf_hashes[:]
        while len(current_level) > 1:
            if len(current_level) % 2 == 1:
                current_level.append(current_level[-1])  # Duplicate odd leaf
            next_level = []
            for i in range(0, len(current_level), 2):
                combined = current_level[i] + current_level[i + 1]
                parent_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
                next_level.append(parent_hash)
            current_level = next_level
        return current_level[0]
```

---

## 4. Closed-Loop Executable Dispatcher (`backend/app/core/dispatcher.py`)

```python
from typing import Dict, Any, List
import json

class ExecutablePayloadDispatcher:
    @staticmethod
    def generate_zoho_payload(voucher_id: str, journal_entries: List[Dict[str, Any]], narration: str) -> Dict[str, Any]:
        """Formats ready-to-execute Zoho Books POST /api/v3/journalentries JSON."""
        return {
            "journal_date": "2026-08-21",
            "reference_number": f"RECON-{voucher_id}",
            "notes": narration,
            "line_items": [
                {
                    "account_name": item["account"],
                    "debit_or_credit": "debit" if item["debit_paise"] > 0 else "credit",
                    "amount": (item["debit_paise"] or item["credit_paise"]) / 100.0
                }
                for item in journal_entries
            ]
        }

    @staticmethod
    def generate_tally_xml(voucher_id: str, journal_entries: List[Dict[str, Any]], narration: str) -> str:
        """Formats standard Tally Prime TALLYMESSAGE XML voucher payload."""
        lines = []
        for item in journal_entries:
            is_debit = item["debit_paise"] > 0
            amt = (item["debit_paise"] if is_debit else item["credit_paise"]) / 100.0
            sign_amt = -amt if is_debit else amt
            lines.append(f"""
            <ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>{item['account']}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>{'Yes' if is_debit else 'No'}</ISDEEMEDPOSITIVE>
                <AMOUNT>{sign_amt:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")

        return f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Journal" ACTION="Create">
                        <DATE>20260821</DATE>
                        <NARRATION>{narration}</NARRATION>
                        {''.join(lines)}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
```

---

## 5. Standalone Verification Command
```bash
python -c "
from backend.app.guardrails.invariant_gate import DoubleEntryInvariantGate
from backend.app.guardrails.merkle_audit import MerkleAuditLedger
from backend.app.core.dispatcher import ExecutablePayloadDispatcher

entries = [
    {'account': 'Bank Account', 'debit_paise': 9764000, 'credit_paise': 0},
    {'account': 'MDR Expense', 'debit_paise': 200000, 'credit_paise': 0},
    {'account': 'GST Expense', 'debit_paise': 36000, 'credit_paise': 0},
    {'account': 'Accounts Receivable', 'debit_paise': 0, 'credit_paise': 10000000}
]

valid, msg = DoubleEntryInvariantGate.verify_journal_voucher(entries)
assert valid is True
assert DoubleEntryInvariantGate.verify_tax_formula(200000, 36000) is True

ledger = MerkleAuditLedger()
ledger.add_audit_event('MATCH_001', 'payload_a')
ledger.add_audit_event('MATCH_002', 'payload_b')
assert len(ledger.get_merkle_root()) == 64

zoho = ExecutablePayloadDispatcher.generate_zoho_payload('V1', entries, 'Reconciled')
assert len(zoho['line_items']) == 4

print('✅ Step 09 Invariant Gatekeeper, Merkle Audit & Dispatcher Verified!')
"
```
