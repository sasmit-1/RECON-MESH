"""
RECON-MESH Ground-Truth Synthetic Data Generator (Step 01)
Generates deterministic, production-grade 3-way financial reconciliation benchmarks
covering all 5 enterprise FinOps edge cases with exact integer paise precision.
"""

import argparse
import asyncio
import json
import os
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# Pydantic Schemas for Synthetic Financial Data
# ------------------------------------------------------------------------------

class RazorpayEvent(BaseModel):
    """Raw Razorpay Webhook Event Payload Schema."""
    event_id: str = Field(..., description="Unique webhook event ID")
    order_id: str = Field(..., description="Razorpay order identifier")
    payment_id: str = Field(..., description="Razorpay payment identifier")
    amount_gross_paise: int = Field(..., description="Gross order amount in paise")
    fee_mdr_paise: int = Field(..., description="Merchant Discount Rate fee in paise")
    fee_gst_paise: int = Field(..., description="18% GST on MDR fee in paise")
    amount_net_paise: int = Field(..., description="Net settlement credit expected in paise")
    currency: str = Field("INR", description="Currency code")
    status: str = Field("captured", description="Payment status: captured, partially_refunded, etc.")
    timestamp: str = Field(..., description="ISO-8601 UTC event timestamp")
    utr: str = Field(..., description="Unique Transaction Reference")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")


class BankStatement(BaseModel):
    """Bank Feed Statement Line Item Schema (CAMT.053 / MT940)."""
    bank_entry_id: str = Field(..., description="Unique bank statement entry ID")
    account_number: str = Field("XXXXXX4590", description="Masked bank account number")
    credit_amount_paise: int = Field(..., description="Credit amount received in paise")
    debit_amount_paise: int = Field(0, description="Debit amount in paise")
    value_date: str = Field(..., description="Banking value date YYYY-MM-DD")
    timestamp: str = Field(..., description="ISO-8601 UTC credit timestamp")
    narration: str = Field(..., description="Raw bank transaction narration text")
    extracted_utr: str = Field(..., description="Parsed or truncated UTR token")
    bank_code: str = Field("HDFC", description="Financial institution code")


class ERPInvoice(BaseModel):
    """General Ledger / ERP Invoice Record Schema (Zoho Books / Tally Prime)."""
    invoice_id: str = Field(..., description="ERP Invoice unique identifier")
    order_id: str = Field(..., description="Corresponding order identifier")
    customer_id: str = Field(..., description="Customer profile identifier")
    invoice_amount_paise: int = Field(..., description="Invoice total gross amount in paise")
    status: str = Field("PAID", description="ERP invoice status: PAID, UNPAID, PARTIAL")
    issue_date: str = Field(..., description="ISO-8601 UTC invoice issue timestamp")
    gl_account: str = Field("Accounts Receivable - Razorpay", description="General Ledger Account")


class GroundTruthMatch(BaseModel):
    """Ground-Truth Benchmark Match Verification Schema."""
    match_id: str = Field(..., description="Unique match identifier")
    type: str = Field(..., description="Match structural topology: ONE_TO_ONE, ONE_TO_MANY, TEMPORAL_LAG, DISPUTE_HOLD, FUZZY_UTR")
    razorpay_event_ids: List[str] = Field(..., description="Associated Razorpay event IDs")
    bank_entry_ids: List[str] = Field(..., description="Associated bank statement entry IDs")
    erp_invoice_ids: List[str] = Field(..., description="Associated ERP invoice IDs")
    edge_case_type: str = Field(..., description="FinOps edge case classifier")
    discrepancy_paise: int = Field(0, description="Known discrepancy amount in paise")
    expected_status: str = Field("MATCHED", description="Expected recon engine status: MATCHED or DISCREPANCY")


class BenchmarkMetadata(BaseModel):
    """Ground-Truth Benchmark Dataset Metadata Schema."""
    version: str = Field("2.1", description="Benchmark specification version")
    record_count: int = Field(..., description="Total count of Razorpay events generated")
    seed: int = Field(..., description="Random seed used for deterministic generation")
    total_gross_paise: int = Field(..., description="Aggregate gross transactions in paise")
    total_net_paise: int = Field(..., description="Aggregate net bank credits in paise")
    total_mdr_paise: int = Field(..., description="Aggregate MDR deductions in paise")
    total_gst_paise: int = Field(..., description="Aggregate GST deductions in paise")


class GroundTruthDataset(BaseModel):
    """Complete Ground-Truth Benchmark Output Schema."""
    benchmark_metadata: BenchmarkMetadata
    razorpay_events: List[RazorpayEvent]
    bank_statements: List[BankStatement]
    erp_invoices: List[ERPInvoice]
    ground_truth_matches: List[GroundTruthMatch]


# ------------------------------------------------------------------------------
# Synthetic Data Generation Core Engine
# ------------------------------------------------------------------------------

def _random_alphanumeric(length: int = 8) -> str:
    """Generate a random alphanumeric string of specified length."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def generate_ground_truth_dataset(count: int = 100, seed: int = 42) -> Dict[str, Any]:
    """
    Generates a complete, deterministic, synthetic ground-truth dataset containing
    Razorpay Webhook events, Bank Statements, and ERP Invoices across the 5 FinOps edge cases:
    
    1. 60% Standard 1:1 matches with 2.0% MDR + 18% GST on MDR.
    2. 20% 1-to-N batch settlements aggregating 3 to 10 orders each.
    3. 10% Multi-day bank holiday / weekend temporal lag.
    4. 5% Partial refund & dispute reserve holdbacks.
    5. 5% Fuzzy and truncated bank narrations / UTRs.
    """
    random.seed(seed)
    
    # Calculate exact counts for each edge case
    c_standard = int(round(count * 0.60))
    c_batch = int(round(count * 0.20))
    c_holiday = int(round(count * 0.10))
    c_dispute = int(round(count * 0.05))
    c_fuzzy = count - (c_standard + c_batch + c_holiday + c_dispute)
    
    base_time = datetime(2026, 8, 21, 10, 0, 0, tzinfo=timezone.utc)  # Friday 10:00 UTC
    
    razorpay_events: List[RazorpayEvent] = []
    bank_statements: List[BankStatement] = []
    erp_invoices: List[ERPInvoice] = []
    ground_truth_matches: List[GroundTruthMatch] = []
    
    event_counter = 1
    bank_counter = 1
    erp_counter = 1
    match_counter = 1
    batch_counter = 1
    
    # Realistic enterprise preset amounts in paise (e.g. ₹1,000 to ₹1,50,000)
    preset_amounts_paise = [
        100000, 250000, 500000, 750000, 1000000, 1500000,
        2500000, 5000000, 7500000, 10000000, 12500000, 15000000
    ]
    
    # --------------------------------------------------------------------------
    # CASE 1: Standard 1:1 Matches with MDR & GST (60%)
    # --------------------------------------------------------------------------
    for _ in range(c_standard):
        gross_paise = random.choice(preset_amounts_paise)
        mdr_paise = int(round(gross_paise * 0.020))         # 2.0% MDR
        gst_paise = int(round(mdr_paise * 0.18))           # 18% GST on MDR
        net_paise = gross_paise - mdr_paise - gst_paise
        
        event_id = f"evt_rzp_{event_counter:03d}"
        order_id = f"order_{_random_alphanumeric(8)}"
        payment_id = f"pay_{9876543210 + event_counter}"
        utr = f"{9876543210 + event_counter}"
        
        event_ts = base_time + timedelta(minutes=15 * event_counter)
        bank_ts = event_ts + timedelta(hours=4, minutes=30)
        erp_ts = event_ts - timedelta(minutes=10)
        
        event = RazorpayEvent(
            event_id=event_id,
            order_id=order_id,
            payment_id=payment_id,
            amount_gross_paise=gross_paise,
            fee_mdr_paise=mdr_paise,
            fee_gst_paise=gst_paise,
            amount_net_paise=net_paise,
            currency="INR",
            status="captured",
            timestamp=event_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            utr=utr,
            metadata={
                "customer_email": f"user{event_counter}@enterprise.in",
                "settlement_batch_id": f"batch_std_{event_counter:03d}"
            }
        )
        razorpay_events.append(event)
        
        invoice_id = f"INV-2026-{erp_counter:03d}"
        erp = ERPInvoice(
            invoice_id=invoice_id,
            order_id=order_id,
            customer_id=f"cust_{900 + (event_counter % 50)}",
            invoice_amount_paise=gross_paise,
            status="PAID",
            issue_date=erp_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            gl_account="Accounts Receivable - Razorpay"
        )
        erp_invoices.append(erp)
        
        bank_entry_id = f"bnk_stmt_{bank_counter:03d}"
        bank = BankStatement(
            bank_entry_id=bank_entry_id,
            account_number="XXXXXX4590",
            credit_amount_paise=net_paise,
            debit_amount_paise=0,
            value_date=bank_ts.strftime("%Y-%m-%d"),
            timestamp=bank_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            narration=f"CMS/RZP/{utr}/MUMBAI",
            extracted_utr=utr,
            bank_code="HDFC"
        )
        bank_statements.append(bank)
        
        match = GroundTruthMatch(
            match_id=f"match_{match_counter:03d}",
            type="ONE_TO_ONE",
            razorpay_event_ids=[event_id],
            bank_entry_ids=[bank_entry_id],
            erp_invoice_ids=[invoice_id],
            edge_case_type="MDR_GST_SPLIT",
            discrepancy_paise=0,
            expected_status="MATCHED"
        )
        ground_truth_matches.append(match)
        
        event_counter += 1
        bank_counter += 1
        erp_counter += 1
        match_counter += 1

    # --------------------------------------------------------------------------
    # CASE 2: 1-to-N Batch Settlements (20%)
    # Aggregating groups of 3 to 10 orders into single net bank deposits
    # --------------------------------------------------------------------------
    remaining_batch_events = c_batch
    while remaining_batch_events > 0:
        batch_size = random.randint(3, 5)
        if batch_size > remaining_batch_events:
            batch_size = remaining_batch_events
        remaining_batch_events -= batch_size
        
        batch_id = f"batch_{batch_counter:03d}"
        batch_event_ids: List[str] = []
        batch_invoice_ids: List[str] = []
        
        batch_net_sum = 0
        latest_event_ts = base_time
        
        for _ in range(batch_size):
            gross_paise = random.choice(preset_amounts_paise)
            mdr_paise = int(round(gross_paise * 0.020))
            gst_paise = int(round(mdr_paise * 0.18))
            net_paise = gross_paise - mdr_paise - gst_paise
            batch_net_sum += net_paise
            
            event_id = f"evt_rzp_{event_counter:03d}"
            order_id = f"order_{_random_alphanumeric(8)}"
            payment_id = f"pay_{9876543210 + event_counter}"
            utr = f"{9876543210 + event_counter}"
            
            event_ts = base_time + timedelta(minutes=10 * event_counter)
            if event_ts > latest_event_ts:
                latest_event_ts = event_ts
            erp_ts = event_ts - timedelta(minutes=5)
            
            event = RazorpayEvent(
                event_id=event_id,
                order_id=order_id,
                payment_id=payment_id,
                amount_gross_paise=gross_paise,
                fee_mdr_paise=mdr_paise,
                fee_gst_paise=gst_paise,
                amount_net_paise=net_paise,
                currency="INR",
                status="captured",
                timestamp=event_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                utr=utr,
                metadata={
                    "customer_email": f"user{event_counter}@enterprise.in",
                    "settlement_batch_id": batch_id
                }
            )
            razorpay_events.append(event)
            batch_event_ids.append(event_id)
            
            invoice_id = f"INV-2026-{erp_counter:03d}"
            erp = ERPInvoice(
                invoice_id=invoice_id,
                order_id=order_id,
                customer_id=f"cust_{900 + (event_counter % 50)}",
                invoice_amount_paise=gross_paise,
                status="PAID",
                issue_date=erp_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                gl_account="Accounts Receivable - Razorpay"
            )
            erp_invoices.append(erp)
            batch_invoice_ids.append(invoice_id)
            
            event_counter += 1
            erp_counter += 1
        
        # Single net bank credit entry for the entire batch
        bank_ts = latest_event_ts + timedelta(hours=6)
        bank_entry_id = f"bnk_stmt_{bank_counter:03d}"
        extracted_utr = f"BATCH{8900 + batch_counter}"
        bank = BankStatement(
            bank_entry_id=bank_entry_id,
            account_number="XXXXXX4590",
            credit_amount_paise=batch_net_sum,
            debit_amount_paise=0,
            value_date=bank_ts.strftime("%Y-%m-%d"),
            timestamp=bank_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            narration=f"NEFT-RZP-SETTLE-BATCH-{8900 + batch_counter}-HDFC",
            extracted_utr=extracted_utr,
            bank_code="HDFC"
        )
        bank_statements.append(bank)
        
        match = GroundTruthMatch(
            match_id=f"match_{match_counter:03d}",
            type="ONE_TO_MANY",
            razorpay_event_ids=batch_event_ids,
            bank_entry_ids=[bank_entry_id],
            erp_invoice_ids=batch_invoice_ids,
            edge_case_type="BATCH_SETTLEMENT",
            discrepancy_paise=0,
            expected_status="MATCHED"
        )
        ground_truth_matches.append(match)
        
        bank_counter += 1
        batch_counter += 1
        match_counter += 1

    # --------------------------------------------------------------------------
    # CASE 3: Multi-Day Bank Holiday Timing Lag (10%)
    # Capture on Friday evening / Saturday settling 3-4 days later on Tuesday
    # --------------------------------------------------------------------------
    friday_night_base = datetime(2026, 8, 21, 23, 58, 0, tzinfo=timezone.utc)  # Friday 23:58 UTC
    for i in range(c_holiday):
        gross_paise = random.choice(preset_amounts_paise)
        mdr_paise = int(round(gross_paise * 0.020))
        gst_paise = int(round(mdr_paise * 0.18))
        net_paise = gross_paise - mdr_paise - gst_paise
        
        event_id = f"evt_rzp_{event_counter:03d}"
        order_id = f"order_{_random_alphanumeric(8)}"
        payment_id = f"pay_{9876543210 + event_counter}"
        utr = f"{9876543210 + event_counter}"
        
        event_ts = friday_night_base + timedelta(minutes=10 * i)
        # Bank credit arrives Tuesday morning (approx 3 days 10 hours later)
        bank_ts = event_ts + timedelta(days=3, hours=10, minutes=17)
        erp_ts = event_ts - timedelta(minutes=15)
        
        event = RazorpayEvent(
            event_id=event_id,
            order_id=order_id,
            payment_id=payment_id,
            amount_gross_paise=gross_paise,
            fee_mdr_paise=mdr_paise,
            fee_gst_paise=gst_paise,
            amount_net_paise=net_paise,
            currency="INR",
            status="captured",
            timestamp=event_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            utr=utr,
            metadata={
                "customer_email": f"user{event_counter}@enterprise.in",
                "settlement_batch_id": f"batch_hol_{event_counter:03d}",
                "timing_lag_days": 4
            }
        )
        razorpay_events.append(event)
        
        invoice_id = f"INV-2026-{erp_counter:03d}"
        erp = ERPInvoice(
            invoice_id=invoice_id,
            order_id=order_id,
            customer_id=f"cust_{900 + (event_counter % 50)}",
            invoice_amount_paise=gross_paise,
            status="PAID",
            issue_date=erp_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            gl_account="Accounts Receivable - Razorpay"
        )
        erp_invoices.append(erp)
        
        bank_entry_id = f"bnk_stmt_{bank_counter:03d}"
        bank = BankStatement(
            bank_entry_id=bank_entry_id,
            account_number="XXXXXX4590",
            credit_amount_paise=net_paise,
            debit_amount_paise=0,
            value_date=bank_ts.strftime("%Y-%m-%d"),
            timestamp=bank_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            narration=f"CMS/RZP/{utr}/HOLIDAY_LAG_SETTLE",
            extracted_utr=utr,
            bank_code="ICICI"
        )
        bank_statements.append(bank)
        
        match = GroundTruthMatch(
            match_id=f"match_{match_counter:03d}",
            type="TEMPORAL_LAG",
            razorpay_event_ids=[event_id],
            bank_entry_ids=[bank_entry_id],
            erp_invoice_ids=[invoice_id],
            edge_case_type="HOLIDAY_LAG",
            discrepancy_paise=0,
            expected_status="MATCHED"
        )
        ground_truth_matches.append(match)
        
        event_counter += 1
        bank_counter += 1
        erp_counter += 1
        match_counter += 1

    # --------------------------------------------------------------------------
    # CASE 4: Partial Refund & Dispute Reserve Holdbacks (5%)
    # Partial refunds and escrow holdbacks creating discrepancy exceptions
    # --------------------------------------------------------------------------
    for _ in range(c_dispute):
        gross_paise = 1200000  # ₹12,000.00
        mdr_paise = int(round(gross_paise * 0.020))   # 24,000 paise (₹240)
        gst_paise = int(round(mdr_paise * 0.18))     # 4,320 paise (₹43.20)
        refund_paise = 400000                        # 400,000 paise (₹4,000) partial refund
        holdback_paise = 40000                       # 40,000 paise (₹400) dispute reserve hold
        
        # Net bank credit received = Gross - MDR - GST - Refund - DisputeHold
        net_bank_credit_paise = gross_paise - mdr_paise - gst_paise - refund_paise - holdback_paise  # 731,680 paise
        expected_standard_net = gross_paise - mdr_paise - gst_paise                                    # 1,171,680 paise
        discrepancy_variance = expected_standard_net - net_bank_credit_paise                          # 440,000 paise
        
        event_id = f"evt_rzp_{event_counter:03d}"
        order_id = f"order_{_random_alphanumeric(8)}"
        payment_id = f"pay_{9876543210 + event_counter}"
        utr = f"{9876543210 + event_counter}"
        
        event_ts = base_time + timedelta(hours=2 * event_counter)
        bank_ts = event_ts + timedelta(hours=5)
        erp_ts = event_ts - timedelta(minutes=20)
        
        event = RazorpayEvent(
            event_id=event_id,
            order_id=order_id,
            payment_id=payment_id,
            amount_gross_paise=gross_paise,
            fee_mdr_paise=mdr_paise,
            fee_gst_paise=gst_paise,
            amount_net_paise=expected_standard_net,
            currency="INR",
            status="partially_refunded",
            timestamp=event_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            utr=utr,
            metadata={
                "customer_email": f"user{event_counter}@enterprise.in",
                "dispute_reserve_holdback_paise": holdback_paise,
                "partial_refund_paise": refund_paise
            }
        )
        razorpay_events.append(event)
        
        invoice_id = f"INV-2026-{erp_counter:03d}"
        erp = ERPInvoice(
            invoice_id=invoice_id,
            order_id=order_id,
            customer_id=f"cust_{900 + (event_counter % 50)}",
            invoice_amount_paise=gross_paise,
            status="PAID",
            issue_date=erp_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            gl_account="Accounts Receivable - Razorpay"
        )
        erp_invoices.append(erp)
        
        bank_entry_id = f"bnk_stmt_{bank_counter:03d}"
        bank = BankStatement(
            bank_entry_id=bank_entry_id,
            account_number="XXXXXX4590",
            credit_amount_paise=net_bank_credit_paise,
            debit_amount_paise=0,
            value_date=bank_ts.strftime("%Y-%m-%d"),
            timestamp=bank_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            narration=f"CMS/RZP/{utr}/DISPUTE_HOLD",
            extracted_utr=utr,
            bank_code="AXIS"
        )
        bank_statements.append(bank)
        
        match = GroundTruthMatch(
            match_id=f"match_{match_counter:03d}",
            type="DISPUTE_HOLD",
            razorpay_event_ids=[event_id],
            bank_entry_ids=[bank_entry_id],
            erp_invoice_ids=[invoice_id],
            edge_case_type="DISPUTE_RESERVE_HOLD",
            discrepancy_paise=discrepancy_variance,
            expected_status="DISCREPANCY"
        )
        ground_truth_matches.append(match)
        
        event_counter += 1
        bank_counter += 1
        erp_counter += 1
        match_counter += 1

    # --------------------------------------------------------------------------
    # CASE 5: Fuzzy & Truncated Bank UTRs (5%)
    # Truncated or noisy bank narrations and UTR tokens matching exact net amounts
    # --------------------------------------------------------------------------
    for _ in range(c_fuzzy):
        gross_paise = random.choice(preset_amounts_paise)
        mdr_paise = int(round(gross_paise * 0.020))
        gst_paise = int(round(mdr_paise * 0.18))
        net_paise = gross_paise - mdr_paise - gst_paise
        
        event_id = f"evt_rzp_{event_counter:03d}"
        order_id = f"order_{_random_alphanumeric(8)}"
        payment_id = f"pay_{9876543210 + event_counter}"
        full_utr = f"9876543210{event_counter:02d}"
        truncated_utr = full_utr[:9]  # Truncated UTR
        
        event_ts = base_time + timedelta(hours=3 * event_counter)
        bank_ts = event_ts + timedelta(hours=4)
        erp_ts = event_ts - timedelta(minutes=12)
        
        event = RazorpayEvent(
            event_id=event_id,
            order_id=order_id,
            payment_id=payment_id,
            amount_gross_paise=gross_paise,
            fee_mdr_paise=mdr_paise,
            fee_gst_paise=gst_paise,
            amount_net_paise=net_paise,
            currency="INR",
            status="captured",
            timestamp=event_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            utr=full_utr,
            metadata={
                "customer_email": f"user{event_counter}@enterprise.in"
            }
        )
        razorpay_events.append(event)
        
        invoice_id = f"INV-2026-{erp_counter:03d}"
        erp = ERPInvoice(
            invoice_id=invoice_id,
            order_id=order_id,
            customer_id=f"cust_{900 + (event_counter % 50)}",
            invoice_amount_paise=gross_paise,
            status="PAID",
            issue_date=erp_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            gl_account="Accounts Receivable - Razorpay"
        )
        erp_invoices.append(erp)
        
        bank_entry_id = f"bnk_stmt_{bank_counter:03d}"
        bank = BankStatement(
            bank_entry_id=bank_entry_id,
            account_number="XXXXXX4590",
            credit_amount_paise=net_paise,
            debit_amount_paise=0,
            value_date=bank_ts.strftime("%Y-%m-%d"),
            timestamp=bank_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            narration=f"UPI/{truncated_utr}/PAY/RZP_NOISE",
            extracted_utr=truncated_utr,
            bank_code="SBI"
        )
        bank_statements.append(bank)
        
        match = GroundTruthMatch(
            match_id=f"match_{match_counter:03d}",
            type="FUZZY_UTR",
            razorpay_event_ids=[event_id],
            bank_entry_ids=[bank_entry_id],
            erp_invoice_ids=[invoice_id],
            edge_case_type="FUZZY_TRUNCATED_UTR",
            discrepancy_paise=0,
            expected_status="MATCHED"
        )
        ground_truth_matches.append(match)
        
        event_counter += 1
        bank_counter += 1
        erp_counter += 1
        match_counter += 1

    # Calculate aggregate metadata metrics
    total_gross_paise = sum(e.amount_gross_paise for e in razorpay_events)
    total_net_paise = sum(b.credit_amount_paise for b in bank_statements)
    total_mdr_paise = sum(e.fee_mdr_paise for e in razorpay_events)
    total_gst_paise = sum(e.fee_gst_paise for e in razorpay_events)
    
    metadata = BenchmarkMetadata(
        version="2.1",
        record_count=len(razorpay_events),
        seed=seed,
        total_gross_paise=total_gross_paise,
        total_net_paise=total_net_paise,
        total_mdr_paise=total_mdr_paise,
        total_gst_paise=total_gst_paise
    )
    
    dataset = GroundTruthDataset(
        benchmark_metadata=metadata,
        razorpay_events=razorpay_events,
        bank_statements=bank_statements,
        erp_invoices=erp_invoices,
        ground_truth_matches=ground_truth_matches
    )
    
    # Convert Pydantic models to dict for JSON serialization / standalone verification compatibility
    if hasattr(dataset, "model_dump"):
        return dataset.model_dump()
    return dataset.dict()


def export_ground_truth_benchmark(count: int = 100, seed: int = 42, output_path: str = "benchmark_results/ground_truth_100.json") -> str:
    """
    Generates and exports the ground truth benchmark dataset to a JSON file.
    """
    dataset_dict = generate_ground_truth_dataset(count=count, seed=seed)
    
    # Ensure directory exists
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
        
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset_dict, f, indent=2)
        
    return os.path.abspath(output_path)


async def stream_synthetic_events(rate_hz: float = 1.0, count: int = 100, seed: int = 42) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Asynchronous generator yielding live financial events (Razorpay events, Bank feeds, ERP invoices)
    in chronological sequence with simulated time intervals based on rate_hz.
    """
    delay_sec = 1.0 / rate_hz if rate_hz > 0 else 0.0
    dataset = generate_ground_truth_dataset(count=count, seed=seed)
    
    # Collate all events into a unified chronological stream
    all_events: List[Dict[str, Any]] = []
    
    for rzp in dataset["razorpay_events"]:
        all_events.append({
            "source_type": "RAZORPAY",
            "timestamp": rzp["timestamp"],
            "payload": rzp
        })
    for bnk in dataset["bank_statements"]:
        all_events.append({
            "source_type": "BANK",
            "timestamp": bnk["timestamp"],
            "payload": bnk
        })
    for erp in dataset["erp_invoices"]:
        all_events.append({
            "source_type": "ERP",
            "timestamp": erp["issue_date"],
            "payload": erp
        })
        
    # Sort chronologically by event timestamp
    all_events.sort(key=lambda item: item["timestamp"])
    
    for event_item in all_events:
        yield event_item
        if delay_sec > 0:
            await asyncio.sleep(delay_sec)


# ------------------------------------------------------------------------------
# CLI Execution Entrypoint
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RECON-MESH Step 01 Ground-Truth Data Generator")
    parser.add_argument("--count", type=int, default=100, help="Number of Razorpay events to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--out", type=str, default="benchmark_results/ground_truth_100.json", help="Output JSON path")
    
    args = parser.parse_args()
    
    abs_path = export_ground_truth_benchmark(count=args.count, seed=args.seed, output_path=args.out)
    print(f"✅ Ground truth benchmark successfully exported ({args.count} records) -> {abs_path}")
