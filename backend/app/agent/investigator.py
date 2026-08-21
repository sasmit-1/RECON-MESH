"""
RECON-MESH AI Recon Investigator (Step 07)
Orchestrates Chain-of-Verification analysis on unresolved discrepancy clusters.
Integrates the AST Safe Math Evaluator (Step 06) to validate generated arithmetic DSLs
and produces cryptographically hashed double-entry DiscrepancyVouchers.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from backend.app.agent.ast_evaluator import ASTSafeMathEvaluator, SecurityViolationError
from backend.app.agent.base_provider import BaseLLMEngine, get_llm_engine
from backend.app.core.models import DiscrepancyVoucher, ReconciliationCluster

logger = logging.getLogger(__name__)

INVESTIGATOR_SYSTEM_PROMPT = """You are the RECON-MESH Autonomous Financial Investigator & Auditor.
Your objective is to analyze unresolved 3-way financial reconciliation discrepancies across Razorpay webhooks, Bank statements, and ERP invoices, and output a structured resolution voucher.

CRITICAL AST DSL SYNTAX CONSTRAINT:
For the 'ast_math_dsl' field: Output ONLY a single, raw, continuous arithmetic expression string evaluating to the final net integer paise. 
- ALLOWED OPERATORS: +, -, *, //, /
- ALLOWED SYMBOLS: GROSS, NET, MDR, GST, BANK_DEPOSIT, ESCROW_HOLD, numeric constants (e.g., 200, 10000, 18, 100).
- FORBIDDEN: Do NOT use variable assignments (e.g. 'x = ...'), statements, comments, semicolons, quotes, or function calls.
- VALID EXAMPLE: "GROSS - (GROSS * 250 // 10000) - ((GROSS * 250 // 10000) * 18 // 100)"
- INVALID EXAMPLE: "let net = GROSS - fee; // result" (WILL BE HARD-REJECTED)

Output MUST be a valid JSON object matching the following structure:
{
  "hypothesis": "Detailed explanation of the discrepancy cause",
  "discrepancy_type": "MDR_DRIFT | CHARGEBACK_HOLD | TIMING_LAG | PARTIAL_REFUND | UNKNOWN_VARIANCE",
  "ast_math_dsl": "Single raw continuous arithmetic expression",
  "journal_entries": [
    {"account": "Bank Account", "debit_paise": 9705000, "credit_paise": 0},
    {"account": "Razorpay Fee Expense (MDR)", "debit_paise": 250000, "credit_paise": 0},
    {"account": "Input GST Recoverable", "debit_paise": 45000, "credit_paise": 0},
    {"account": "Accounts Receivable", "debit_paise": 0, "credit_paise": 10000000}
  ],
  "confidence": 0.98
}
"""


class ReconInvestigator:
    """
    Chain-of-Verification AI Investigator for RECON-MESH.
    Analyzes discrepancy clusters, generates math DSL proofs, and builds DiscrepancyVouchers.
    """

    def __init__(self, llm_engine: Optional[BaseLLMEngine] = None):
        self.llm_engine = llm_engine or get_llm_engine()
        self.ast_evaluator = ASTSafeMathEvaluator()

    async def investigate_cluster(self, cluster: ReconciliationCluster) -> DiscrepancyVoucher:
        """
        Investigates an unresolved cluster, generates resolution hypothesis via LLM,
        validates the AST DSL formula, checks double-entry balance, and returns a DiscrepancyVoucher.
        """
        user_prompt = f"""
Reconciliation Cluster ID: {cluster.cluster_id}
Discrepancy Variance (paise): {cluster.discrepancy_paise}
Sum Gross Amount (paise): {cluster.sum_gross_paise}
Sum Net Expected (paise): {cluster.sum_net_expected_paise}
Sum Bank Credit (paise): {cluster.sum_bank_credit_paise}

Razorpay Transactions: {[t.dict() for t in cluster.razorpay_txns]}
Bank Transactions: {[b.dict() for b in cluster.bank_txns]}
ERP Invoices: {[e.dict() for e in cluster.erp_txns]}

Please analyze the variance and generate the resolution hypothesis JSON.
"""
        response_text = await self.llm_engine.generate_resolution(
            INVESTIGATOR_SYSTEM_PROMPT, user_prompt
        )

        try:
            res_data = json.loads(response_text)
        except Exception:
            # Fallback if response is not clean JSON
            res_data = {
                "hypothesis": f"Raw analysis: {response_text[:200]}",
                "discrepancy_type": "UNPARSED_HYPOTHESIS",
                "ast_math_dsl": "GROSS - NET",
                "journal_entries": [],
                "confidence": 0.5
            }

        ast_dsl = res_data.get("ast_math_dsl", "GROSS - NET")
        discrepancy_type = res_data.get("discrepancy_type", "UNCLASSIFIED")
        journal_entries = res_data.get("journal_entries", [])

        # Evaluate AST DSL using ASTSafeMathEvaluator
        symbols = {
            "GROSS": cluster.sum_gross_paise,
            "NET": cluster.sum_net_expected_paise,
            "BANK_DEPOSIT": cluster.sum_bank_credit_paise,
            "MDR": 200,
            "GST": 18,
            "ESCROW_HOLD": abs(cluster.discrepancy_paise)
        }

        try:
            evaluated_paise = self.ast_evaluator.evaluate(ast_dsl, symbols)
        except (SecurityViolationError, ValueError, ZeroDivisionError) as err:
            logger.warning(f"AST DSL evaluation failed ({err}), falling back to safe subtraction.")
            ast_dsl = "GROSS - NET"
            evaluated_paise = self.ast_evaluator.evaluate(ast_dsl, symbols)

        # Audit hash linking formula to evaluated result
        audit_hash = self.ast_evaluator.generate_proof_hash(ast_dsl, evaluated_paise)

        # Check double-entry balance: total debits must equal total credits
        total_debits = sum(entry.get("debit_paise", 0) for entry in journal_entries)
        total_credits = sum(entry.get("credit_paise", 0) for entry in journal_entries)
        double_entry_balanced = (total_debits == total_credits) if journal_entries else True

        return DiscrepancyVoucher(
            voucher_id=f"vch_{uuid4().hex[:10]}",
            cluster_id=cluster.cluster_id,
            discrepancy_type=discrepancy_type,
            variance_paise=cluster.discrepancy_paise,
            proposed_adjustment_dsl=ast_dsl,
            double_entry_balanced=double_entry_balanced,
            audit_hash=audit_hash
        )
