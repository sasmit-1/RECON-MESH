"""
TRIDENT Canonical Data Models (Step 02)
Defines Pydantic v2 domain schemas for multi-source 3-way financial reconciliation.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Source system of incoming telemetry."""
    RAZORPAY = "RAZORPAY"
    BANK = "BANK"
    ERP = "ERP"


class MatchStatus(str, Enum):
    """Lifecycle reconciliation status of a transaction or cluster."""
    PENDING = "PENDING"
    MATCHED = "MATCHED"
    SETTLED_PENDING_ERP = "SETTLED_PENDING_ERP"
    DISCREPANCY = "DISCREPANCY"
    ORPHAN = "ORPHAN"


class CanonicalTransaction(BaseModel):
    """
    Unified canonical transaction record normalized from heterogeneous sources
    (Razorpay Webhooks, Bank CAMT.053 / MT940, ERP Invoices).
    All currency figures are stored as exact 64-bit integer paise.
    """
    id: str = Field(default_factory=lambda: f"txn_{uuid4().hex[:12]}", description="Unique internal canonical UUID")
    source: SourceType = Field(..., description="Source system: RAZORPAY, BANK, or ERP")
    original_id: str = Field(..., description="Raw source record ID (payment_id, bank_entry_id, or invoice_id)")
    order_id: Optional[str] = Field(None, description="Razorpay order identifier")
    utr: Optional[str] = Field(None, description="Unique Transaction Reference")
    amount_gross_paise: int = Field(..., description="Gross transaction amount in exact integer paise")
    fee_mdr_paise: int = Field(0, description="Merchant Discount Rate fee in paise")
    fee_gst_paise: int = Field(0, description="18% GST on MDR in paise")
    amount_net_paise: int = Field(..., description="Net expected bank credit in paise")
    currency: str = Field("INR", description="Currency code")
    timestamp_utc: datetime = Field(..., description="Timezone-aware UTC timestamp")
    raw_narration: Optional[str] = Field(None, description="Raw bank narration string")
    clean_narration_tokens: List[str] = Field(default_factory=list, description="Sanitized UTR and narration tokens")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary source metadata")


class ReconciliationCluster(BaseModel):
    """
    Group of matching or candidate transactions across 3 sources
    evaluating exact linear balance equations.
    """
    cluster_id: str = Field(default_factory=lambda: f"cls_{uuid4().hex[:12]}", description="Unique cluster ID")
    razorpay_txns: List[CanonicalTransaction] = Field(default_factory=list, description="Associated Razorpay canonical transactions")
    bank_txns: List[CanonicalTransaction] = Field(default_factory=list, description="Associated Bank canonical transactions")
    erp_txns: List[CanonicalTransaction] = Field(default_factory=list, description="Associated ERP canonical invoices")
    sum_gross_paise: int = Field(0, description="Sum of Razorpay gross amounts in paise")
    sum_net_expected_paise: int = Field(0, description="Sum of Razorpay net expected amounts in paise")
    sum_bank_credit_paise: int = Field(0, description="Sum of actual bank credits in paise")
    discrepancy_paise: int = Field(0, description="Net discrepancy variance in paise")
    status: MatchStatus = Field(MatchStatus.PENDING, description="Cluster reconciliation status")


class DiscrepancyVoucher(BaseModel):
    """
    Agent-generated resolution voucher detailing discrepancy variance,
    AST safe arithmetic adjustment, and double-entry balance validation.
    """
    voucher_id: str = Field(default_factory=lambda: f"vch_{uuid4().hex[:12]}", description="Unique voucher ID")
    cluster_id: str = Field(..., description="Target reconciliation cluster ID")
    discrepancy_type: str = Field(..., description="Discrepancy classification: MDR_DRIFT, CHARGEBACK_HOLD, TIMING_LAG, PARTIAL_REFUND")
    variance_paise: int = Field(..., description="Variance amount in paise")
    proposed_adjustment_dsl: str = Field(..., description="AST safe arithmetic DSL expression")
    double_entry_balanced: bool = Field(..., description="Double-entry invariant status")
    audit_hash: str = Field(..., description="SHA-256 Merkle audit hash")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Voucher creation UTC timestamp")
