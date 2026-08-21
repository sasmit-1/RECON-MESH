"""
RECON-MESH Step 09: Deterministic Invariant Gatekeeper & Merkle Audit Ledger
=============================================================================
Enforces non-probabilistic mathematical zero-sum double-entry accounting
invariants and tax audit verification.

In enterprise FinOps, probabilistic AI outputs cannot be trusted blindly with
general ledger modifications. The InvariantGatekeeper acts as a hard zero-tolerance
mathematical firewall before any ERP dispatch.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.app.core.models import DiscrepancyVoucher
from backend.app.guardrails.merkle_audit import MerkleAuditLedger


class DoubleEntryInvariantError(Exception):
    """Raised when a proposed journal entry violates double-entry zero-sum math."""
    pass


# Alias for spec compatibility
InvariantViolationError = DoubleEntryInvariantError


class InvariantGatekeeper:
    """
    Deterministic Invariant Gatekeeper enforcing non-negotiable financial rules:

      1. Zero-Sum Double Entry: SUM(Debits) - SUM(Credits) == 0 (to exact 0 paise).
      2. Non-Zero Magnitude : SUM(Debits) > 0.
      3. Statutory GST Match: GST == round(MDR * 0.18) (+/- 1 paise tolerance).
      4. Gross Limit Match  : |adjustment| <= absolute transaction gross amount.
    """

    @staticmethod
    def validate_double_entry(entries: List[Dict[str, Any]]) -> bool:
        """
        Strict zero-sum double-entry validator.

        Asserts:
          - sum(Debit Paise) - sum(Credit Paise) == 0
          - sum(Debit Paise) > 0

        Raises:
          DoubleEntryInvariantError: If sum is non-zero, negative, or zero total value.

        Returns:
          True if perfectly balanced and positive.
        """
        if not entries:
            raise DoubleEntryInvariantError("Journal entries list cannot be empty")

        total_debits = sum(
            entry.get("debit_paise", entry.get("debit", 0)) for entry in entries
        )
        total_credits = sum(
            entry.get("credit_paise", entry.get("credit", 0)) for entry in entries
        )

        if total_debits != total_credits:
            diff = total_debits - total_credits
            raise DoubleEntryInvariantError(
                f"Double-entry violation! Debits ({total_debits}) != Credits ({total_credits}), "
                f"Discrepancy: {diff} paise"
            )

        if total_debits <= 0:
            raise DoubleEntryInvariantError(
                f"Journal entry cannot have zero or negative total values (got {total_debits} paise)"
            )

        return True

    @staticmethod
    def verify_journal_voucher(entries: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Non-raising diagnostic wrapper for double-entry verification.

        Returns:
          (True, "ZERO_SUM_INVARIANT_PASSED") or (False, error_message)
        """
        try:
            InvariantGatekeeper.validate_double_entry(entries)
            return True, "ZERO_SUM_INVARIANT_PASSED"
        except DoubleEntryInvariantError as exc:
            return False, str(exc)

    @staticmethod
    def verify_tax_formula(mdr_paise: int, gst_paise: int) -> bool:
        """
        Validates 18% GST statutory audit invariant:
          GST == round(MDR * 0.18) (within max 1 paise rounding tolerance).
        """
        expected_gst = int(round(mdr_paise * 0.18))
        return abs(gst_paise - expected_gst) <= 1

    @staticmethod
    def validate_gross_limit(adjustment_paise: int, max_gross_paise: int) -> bool:
        """
        Ensures net proposed adjustment does not exceed absolute gross transaction limit.

        Raises:
          DoubleEntryInvariantError if adjustment exceeds limits.
        """
        if abs(adjustment_paise) > max_gross_paise:
            raise DoubleEntryInvariantError(
                f"Gross limit invariant violation! Adjustment ({abs(adjustment_paise)} paise) "
                f"exceeds maximum gross limit ({max_gross_paise} paise)"
            )
        return True

    @classmethod
    def check_and_sign_voucher(
        cls,
        voucher: DiscrepancyVoucher,
        entries: List[Dict[str, Any]],
        ledger: Optional[MerkleAuditLedger] = None,
    ) -> DiscrepancyVoucher:
        """
        Validates voucher double-entry invariants and signs it into the MerkleAuditLedger.

        Updates voucher.double_entry_balanced = True and re-computes voucher.audit_hash.
        """
        cls.validate_double_entry(entries)
        voucher.double_entry_balanced = True

        # Generate cryptographic signature
        payload = (
            f"{voucher.voucher_id}:{voucher.cluster_id}:{voucher.discrepancy_type}:"
            f"{voucher.variance_paise}:{voucher.proposed_adjustment_dsl}:"
            f"{voucher.double_entry_balanced}"
        )
        voucher.audit_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        if ledger is not None:
            ledger.add_audit_event("VOUCHER_SIGNED", voucher.audit_hash)

        return voucher


# Class alias for backward/spec compatibility
DoubleEntryInvariantGate = InvariantGatekeeper
