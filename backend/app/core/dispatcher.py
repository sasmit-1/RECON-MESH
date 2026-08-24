"""
TRIDENT Step 09: Closed-Loop Executable ERP Dispatcher
=========================================================
Transforms verified DiscrepancyVouchers into production-ready API payloads
and dispatches them to external accounting ledgers (Zoho Books, TallyPrime, SAP S/4HANA).

In enterprise reconciliation, generating static markdown summaries leaves the loop open;
human accountants still have to manually key vouchers into ERPs. The ERPDispatcher
automates the posting of balanced, signed vouchers into target ledgers.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from backend.app.core.models import DiscrepancyVoucher


class ERPDispatcher:
    """
    Closed-Loop Executable ERP Payload Dispatcher.

    Supports formatting and dispatching journal vouchers to:
      1. Zoho Books REST API (JSON)
      2. TallyPrime XML / JSON HTTP Bridge
      3. SAP S/4HANA OData Journal Entries
    """

    @staticmethod
    def _current_date_str() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    @staticmethod
    def _current_date_tally_str() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d")

    @classmethod
    def generate_zoho_payload(
        cls,
        voucher_id: str,
        journal_entries: List[Dict[str, Any]],
        narration: str = "",
    ) -> Dict[str, Any]:
        """
        Formats ready-to-execute Zoho Books POST /api/v3/journalentries JSON payload.

        Structure adheres to Zoho Books API specification while supporting top-level
        property access.
        """
        narration_text = narration or f"TRIDENT Automated Adjustment for {voucher_id}"
        date_str = cls._current_date_str()

        line_items = []
        for item in journal_entries:
            debit = item.get("debit_paise", item.get("debit", 0))
            credit = item.get("credit_paise", item.get("credit", 0))
            is_debit = debit > 0
            amt_paise = debit if is_debit else credit

            line_items.append(
                {
                    "account_name": item.get("account", "Suspense Account"),
                    "debit_or_credit": "debit" if is_debit else "credit",
                    "amount": round(amt_paise / 100.0, 2),
                }
            )

        payload = {
            "journal_date": date_str,
            "reference_number": f"RECON-{voucher_id}",
            "notes": narration_text,
            "line_items": line_items,
        }

        # Provide nested "journal_entry" key for Zoho Books API compliance
        payload["journal_entry"] = {
            "journal_date": date_str,
            "reference_number": f"RECON-{voucher_id}",
            "notes": narration_text,
            "line_items": line_items,
        }
        return payload

    @classmethod
    def generate_tally_xml(
        cls,
        voucher_id: str,
        journal_entries: List[Dict[str, Any]],
        narration: str = "",
    ) -> str:
        """Formats standard Tally Prime TALLYMESSAGE XML voucher payload."""
        narration_text = narration or f"TRIDENT Automated Adjustment for {voucher_id}"
        date_str = cls._current_date_tally_str()

        lines = []
        for item in journal_entries:
            debit = item.get("debit_paise", item.get("debit", 0))
            credit = item.get("credit_paise", item.get("credit", 0))
            is_debit = debit > 0
            amt = (debit if is_debit else credit) / 100.0
            sign_amt = -amt if is_debit else amt

            lines.append(
                f"""            <ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>{item.get('account', 'Suspense Account')}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>{'Yes' if is_debit else 'No'}</ISDEEMEDPOSITIVE>
                <AMOUNT>{sign_amt:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>"""
            )

        ledger_entries_xml = "\n".join(lines)

        return f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Journal" ACTION="Create">
                        <DATE>{date_str}</DATE>
                        <NARRATION>{narration_text}</NARRATION>
{ledger_entries_xml}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""

    @classmethod
    def generate_tally_payload(
        cls,
        voucher_id: str,
        journal_entries: List[Dict[str, Any]],
        narration: str = "",
    ) -> Dict[str, Any]:
        """Formats JSON envelope structure for Tally HTTP REST bridge integration."""
        return {
            "tally_request": "Import Data",
            "voucher_type": "Journal",
            "voucher_number": f"RECON-{voucher_id}",
            "date": cls._current_date_tally_str(),
            "narration": narration or f"TRIDENT Automated Adjustment for {voucher_id}",
            "xml_payload": cls.generate_tally_xml(voucher_id, journal_entries, narration),
        }

    @classmethod
    def generate_sap_payload(
        cls,
        voucher_id: str,
        journal_entries: List[Dict[str, Any]],
        narration: str = "",
    ) -> Dict[str, Any]:
        """Formats SAP S/4HANA OData Journal Entry API (API_JOURNALENTRY_CREATE) JSON payload."""
        date_str = cls._current_date_str()
        items = []

        for idx, item in enumerate(journal_entries, start=1):
            debit = item.get("debit_paise", item.get("debit", 0))
            credit = item.get("credit_paise", item.get("credit", 0))
            is_debit = debit > 0
            amt_paise = debit if is_debit else credit

            items.append(
                {
                    "GLAccount": item.get("account", "100000"),
                    "DebitCreditCode": "S" if is_debit else "H",
                    "AmountInTransactionCurrency": round(amt_paise / 100.0, 2),
                    "TransactionCurrency": "INR",
                    "DocumentItemText": f"Item {idx}: {narration or voucher_id}",
                }
            )

        return {
            "CompanyCode": "1000",
            "DocumentType": "SA",
            "PostingDate": date_str,
            "DocumentDate": date_str,
            "AccountingDocumentHeaderText": f"RECON-{voucher_id}",
            "to_JournalEntryItem": items,
        }

    @classmethod
    async def dispatch_voucher(
        cls,
        voucher: DiscrepancyVoucher,
        journal_entries: List[Dict[str, Any]],
        target_system: str = "ZOHO",
        narration: str = "",
        live_endpoint: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches a verified voucher to the specified ERP target system.

        If `live_endpoint` is provided, sends an HTTP POST using `httpx.AsyncClient`.
        Otherwise, executes a local mock dispatch returning the structured payload.
        """
        system_upper = target_system.upper()
        narration_text = narration or f"TRIDENT adjustment for cluster {voucher.cluster_id}"

        if system_upper == "ZOHO":
            payload = cls.generate_zoho_payload(voucher.voucher_id, journal_entries, narration_text)
            content_type = "application/json"
        elif system_upper in ("TALLY", "TALLYPRIME"):
            payload = cls.generate_tally_payload(voucher.voucher_id, journal_entries, narration_text)
            content_type = "application/json"
        elif system_upper == "SAP":
            payload = cls.generate_sap_payload(voucher.voucher_id, journal_entries, narration_text)
            content_type = "application/json"
        else:
            payload = cls.generate_zoho_payload(voucher.voucher_id, journal_entries, narration_text)
            content_type = "application/json"

        # Mock dispatch path (when live_endpoint is not configured)
        if not live_endpoint:
            return {
                "status": "DISPATCH_MOCK_SUCCESS",
                "target_system": system_upper,
                "voucher_id": voucher.voucher_id,
                "cluster_id": voucher.cluster_id,
                "audit_hash": voucher.audit_hash,
                "payload": payload,
                "response_code": 200,
            }

        # Live dispatch path via httpx.AsyncClient
        req_headers = {"Content-Type": content_type}
        if headers:
            req_headers.update(headers)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    live_endpoint,
                    json=payload if isinstance(payload, dict) else None,
                    content=payload if isinstance(payload, str) else None,
                    headers=req_headers,
                )
                return {
                    "status": "DISPATCH_LIVE_SUCCESS" if response.is_success else "DISPATCH_LIVE_FAILED",
                    "target_system": system_upper,
                    "voucher_id": voucher.voucher_id,
                    "cluster_id": voucher.cluster_id,
                    "audit_hash": voucher.audit_hash,
                    "response_code": response.status_code,
                    "response_body": response.text,
                }
            except Exception as exc:
                return {
                    "status": "DISPATCH_LIVE_ERROR",
                    "target_system": system_upper,
                    "voucher_id": voucher.voucher_id,
                    "error": str(exc),
                    "response_code": 500,
                }


# Alias for spec compatibility
ExecutablePayloadDispatcher = ERPDispatcher
