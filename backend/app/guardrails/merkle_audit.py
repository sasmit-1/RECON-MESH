"""
RECON-MESH Step 09: Cryptographic Merkle Audit Tree
====================================================
Computes SHA-256 tamper-proof Merkle binary tree proofs over all
resolved financial vouchers and agent audit events.

Guarantees cryptographic auditability of financial ledger entries.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, List, Union

from backend.app.core.models import DiscrepancyVoucher


class MerkleAuditLedger:
    """
    Cryptographic Merkle Audit Ledger building SHA-256 binary tree proofs.

    Leaves are SHA-256 digests of individual vouchers or audit events.
    Successive adjacent pairs are concatenated and hashed layer-by-layer
    until reaching a single 64-character hex Merkle Root.

    If an odd number of nodes exists at any layer, the last node is duplicated
    to balance the tree layer.
    """

    def __init__(self) -> None:
        self.leaf_hashes: List[str] = []

    def _leaf_hash_for(self, item: Union[DiscrepancyVoucher, Dict[str, Any], str]) -> str:
        """Computes a deterministic SHA-256 leaf digest for a voucher, dict, or string."""
        if isinstance(item, DiscrepancyVoucher):
            raw_str = (
                f"{item.voucher_id}:{item.cluster_id}:{item.discrepancy_type}:"
                f"{item.variance_paise}:{item.proposed_adjustment_dsl}:{item.audit_hash}"
            )
        elif isinstance(item, dict):
            raw_str = json.dumps(item, sort_keys=True)
        else:
            raw_str = str(item)

        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    def add_audit_event(self, event_type: str, payload_str: str) -> str:
        """
        Hashes an audit event (f"{event_type}:{payload_str}") with SHA-256,
        appends it to leaf_hashes, and returns the leaf hash.
        """
        digest = hashlib.sha256(f"{event_type}:{payload_str}".encode("utf-8")).hexdigest()
        self.leaf_hashes.append(digest)
        return digest

    def _reduce_merkle_tree(self, hashes: List[str]) -> str:
        """
        Reduces a list of leaf hashes to a single 64-character SHA-256 Merkle root.
        Duplicating the last element when a layer has an odd number of items.
        """
        if not hashes:
            return hashlib.sha256(b"EMPTY_LEDGER").hexdigest()

        current_level = hashes[:]
        while len(current_level) > 1:
            if len(current_level) % 2 == 1:
                current_level.append(current_level[-1])

            next_level = []
            for i in range(0, len(current_level), 2):
                combined = current_level[i] + current_level[i + 1]
                parent_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
                next_level.append(parent_hash)
            current_level = next_level

        return current_level[0]

    def get_merkle_root(self) -> str:
        """Computes and returns the Merkle Root over all accumulated audit event leaf hashes."""
        return self._reduce_merkle_tree(self.leaf_hashes)

    def compute_merkle_root(
        self, vouchers: List[Union[DiscrepancyVoucher, Dict[str, Any], str]]
    ) -> str:
        """
        Computes the Merkle Root over a list of resolved vouchers or audit items.
        Leaves are computed using _leaf_hash_for.
        """
        leaf_hashes = [self._leaf_hash_for(v) for v in vouchers]
        return self._reduce_merkle_tree(leaf_hashes)
