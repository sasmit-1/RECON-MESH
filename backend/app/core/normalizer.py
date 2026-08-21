"""
RECON-MESH Canonical Normalizer (Step 02)
Provides robust sanitization, UTC timestamp parsing, exact integer paise arithmetic,
and UTR token extraction for incoming multi-source financial telemetry.
"""

import re
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

import dateutil.parser

from backend.app.core.models import CanonicalTransaction, SourceType


# List of common Indian banking narration prefixes and location tags to filter out
NOISE_PREFIXES = {
    "CMS", "RZP", "NEFT", "RTGS", "IMPS", "UPI", "INFOSYS", "MUM", "BLR",
    "DEL", "MUMBAI", "BANGALORE", "BENGALURU", "SETTLE", "TRANSFER", "PAY",
    "HDFC", "ICICI", "AXIS", "SBI", "SETTLEMENT", "NOISE", "TRUNC", "HOLIDAY",
    "LAG", "BRANCH", "INT", "INFT", "CLG"
}


def to_paise(amount: Union[float, str, int, Decimal]) -> int:
    """
    Converts standard INR currency values into exact integer paise (1 Rupee = 100 Paise).
    Uses Decimal with ROUND_HALF_UP quantization to eliminate floating-point precision errors.
    
    Examples:
    - to_paise("1,00,000.50") -> 10000050
    - to_paise(976.40) -> 97640
    - to_paise(10000050) -> 10000050
    """
    if isinstance(amount, int):
        return amount
        
    if isinstance(amount, Decimal):
        d = amount
    elif isinstance(amount, float):
        d = Decimal(str(amount))
    elif isinstance(amount, str):
        cleaned = amount.replace(",", "").strip()
        if not cleaned:
            return 0
        d = Decimal(cleaned)
        if "." in cleaned or "," in amount:
            return int((d * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        else:
            return int(d)
    else:
        d = Decimal(str(amount))
        
    return int((d * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_mdr_and_gst(gross_paise: int, mdr_rate_bps: int = 200) -> Tuple[int, int, int]:
    """
    Calculates exact MDR fee, 18% GST on MDR, and net bank credit amount in integer paise.
    
    Invariants:
    - mdr_paise = round(gross_paise * (mdr_rate_bps / 10000))
    - gst_paise = round(mdr_paise * 0.18)
    - net_paise = gross_paise - mdr_paise - gst_paise
    - gross_paise - (mdr_paise + gst_paise + net_paise) == 0
    
    Returns:
        (mdr_paise, gst_paise, net_paise)
    """
    gross_dec = Decimal(gross_paise)
    bps_dec = Decimal(mdr_rate_bps) / Decimal("10000")
    
    mdr_dec = (gross_dec * bps_dec).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    mdr_paise = int(mdr_dec)
    
    gst_dec = (Decimal(mdr_paise) * Decimal("0.18")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    gst_paise = int(gst_dec)
    
    net_paise = gross_paise - mdr_paise - gst_paise
    return mdr_paise, gst_paise, net_paise


def parse_iso_utc(date_input: Union[str, int, float, datetime]) -> datetime:
    """
    Parses diverse timestamp formats (Unix epochs, IST offset strings, banking date strings)
    into a standardized, timezone-aware UTC datetime.
    """
    if isinstance(date_input, datetime):
        if date_input.tzinfo is None:
            return date_input.replace(tzinfo=timezone.utc)
        return date_input.astimezone(timezone.utc)
        
    if isinstance(date_input, (int, float)):
        if date_input > 1e11:  # epoch in milliseconds
            date_input = date_input / 1000.0
        return datetime.fromtimestamp(date_input, tz=timezone.utc)
        
    if isinstance(date_input, str):
        cleaned_str = date_input.strip()
        if not cleaned_str:
            return datetime.now(timezone.utc)
            
        try:
            dt = dateutil.parser.parse(cleaned_str)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)
            
    return datetime.now(timezone.utc)


def extract_clean_utr(narration: str) -> Optional[str]:
    """
    Strips noise prefixes and extracts clean UTR / transaction tokens from bank narrations.
    
    Example:
    'CMS/RZP/PAY9876543210/BLR' -> 'PAY9876543210'
    'UPI/9876543210/PAY/RZP' -> '9876543210'
    """
    if not narration:
        return None
        
    tokens = re.split(r'[/_\-\s:]+', narration.strip())
    
    candidates = []
    for token in tokens:
        clean_tok = token.strip()
        if not clean_tok:
            continue
        if clean_tok.upper() in NOISE_PREFIXES:
            continue
        if len(clean_tok) < 3:
            continue
        candidates.append(clean_tok)
        
    if not candidates:
        return narration.strip()
        
    for cand in candidates:
        if any(c.isdigit() for c in cand):
            return cand
            
    return candidates[0]


def normalize_event(raw_event: Dict[str, Any], source: SourceType) -> CanonicalTransaction:
    """
    Converts raw event payload dict from Razorpay, Bank, or ERP into a validated CanonicalTransaction.
    """
    if source == SourceType.RAZORPAY:
        payment_id = str(raw_event.get("payment_id") or raw_event.get("event_id") or f"pay_{uuid4().hex[:8]}")
        order_id = raw_event.get("order_id")
        utr = raw_event.get("utr") or extract_clean_utr(raw_event.get("narration", ""))
        
        gross_paise = to_paise(raw_event.get("amount_gross_paise", raw_event.get("amount", 0)))
        mdr_paise = to_paise(raw_event.get("fee_mdr_paise", raw_event.get("fee", 0)))
        gst_paise = to_paise(raw_event.get("fee_gst_paise", raw_event.get("tax", 0)))
        
        if mdr_paise == 0 and gross_paise > 0:
            mdr_paise, gst_paise, calculated_net = calculate_mdr_and_gst(gross_paise)
            net_paise = calculated_net
        else:
            net_paise = to_paise(raw_event.get("amount_net_paise", gross_paise - mdr_paise - gst_paise))
            
        ts_utc = parse_iso_utc(raw_event.get("timestamp", datetime.now(timezone.utc)))
        tokens = [utr] if utr else []
        
        return CanonicalTransaction(
            id=f"canon_rzp_{payment_id}",
            source=SourceType.RAZORPAY,
            original_id=payment_id,
            order_id=order_id,
            utr=utr,
            amount_gross_paise=gross_paise,
            fee_mdr_paise=mdr_paise,
            fee_gst_paise=gst_paise,
            amount_net_paise=net_paise,
            currency=raw_event.get("currency", "INR"),
            timestamp_utc=ts_utc,
            raw_narration=raw_event.get("narration"),
            clean_narration_tokens=tokens,
            metadata=raw_event.get("metadata", {})
        )

    elif source == SourceType.BANK:
        entry_id = str(raw_event.get("bank_entry_id") or f"bnk_{uuid4().hex[:8]}")
        narration = raw_event.get("narration", "")
        extracted_utr = raw_event.get("extracted_utr") or extract_clean_utr(narration)
        
        credit_paise = to_paise(raw_event.get("credit_amount_paise", raw_event.get("amount", 0)))
        ts_utc = parse_iso_utc(raw_event.get("timestamp", raw_event.get("value_date", datetime.now(timezone.utc))))
        tokens = [extracted_utr] if extracted_utr else []
        
        return CanonicalTransaction(
            id=f"canon_bnk_{entry_id}",
            source=SourceType.BANK,
            original_id=entry_id,
            order_id=raw_event.get("order_id"),
            utr=extracted_utr,
            amount_gross_paise=credit_paise,
            fee_mdr_paise=0,
            fee_gst_paise=0,
            amount_net_paise=credit_paise,
            currency="INR",
            timestamp_utc=ts_utc,
            raw_narration=narration,
            clean_narration_tokens=tokens,
            metadata={
                "account_number": raw_event.get("account_number"),
                "bank_code": raw_event.get("bank_code")
            }
        )

    elif source == SourceType.ERP:
        invoice_id = str(raw_event.get("invoice_id") or f"inv_{uuid4().hex[:8]}")
        order_id = raw_event.get("order_id")
        amount_paise = to_paise(raw_event.get("invoice_amount_paise", raw_event.get("amount", 0)))
        ts_utc = parse_iso_utc(raw_event.get("issue_date", raw_event.get("timestamp", datetime.now(timezone.utc))))
        
        return CanonicalTransaction(
            id=f"canon_erp_{invoice_id}",
            source=SourceType.ERP,
            original_id=invoice_id,
            order_id=order_id,
            utr=None,
            amount_gross_paise=amount_paise,
            fee_mdr_paise=0,
            fee_gst_paise=0,
            amount_net_paise=amount_paise,
            currency="INR",
            timestamp_utc=ts_utc,
            raw_narration=f"ERP Invoice {invoice_id}",
            clean_narration_tokens=[],
            metadata={
                "customer_id": raw_event.get("customer_id"),
                "gl_account": raw_event.get("gl_account"),
                "status": raw_event.get("status")
            }
        )

    else:
        raise ValueError(f"Unsupported source type: {source}")
