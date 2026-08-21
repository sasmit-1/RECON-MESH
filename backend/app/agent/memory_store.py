"""
RECON-MESH Step 08: Episodic Memory Store & Temporal Vector RAG
================================================================
Implements a local SQLite-backed episodic memory that:

 * Indexes verified DiscrepancyVoucher resolutions as 384-d feature vectors
   built from deterministic MD5 hashes (NEVER Python's hash(), which is
   randomised per interpreter start via PYTHONHASHSEED).

 * Exposes two primary APIs consumed by the reconciliation agent:
     - store_voucher(voucher)          -> persist a verified resolution
     - recall_similar(type, variance)  -> sub-5 ms band + cosine recall

 * Also exposes the architecture-level RAG API:
     - store_verified_precedent(...)   -> embed + persist arbitrary precedent
     - query_precedent(...)            -> cosine similarity lookup (>=0.95 gate)

Schema
------
  vouchers          - one row per DiscrepancyVoucher (typed domain objects)
  resolution_memory - one row per precedent (embedding + DSL + journal)

Connection handling
-------------------
Python's ``with sqlite3.connect(...) as conn`` does NOT close the connection
on __exit__; it only commits or rolls back.  We therefore call conn.close()
explicitly in a finally-block so Windows can remove the file immediately after
the last operation (critical for test cleanup with os.remove()).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

import numpy as np

from backend.app.core.models import DiscrepancyVoucher

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EMBEDDING_DIM: int = 384
_DEFAULT_TOLERANCE_PAISE: int = 1_000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _deterministic_md5_int(text: str) -> int:
    """
    Returns a deterministic 128-bit integer derived from *text* using MD5.
    Safe across all Python processes and restarts (unlike the built-in hash()).
    """
    return int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)


def _compute_feature_vector(
    variance_ratio: float,
    narration_tokens: List[str],
) -> np.ndarray:
    """
    Builds a normalised 384-dimensional float32 feature vector.

    Dimension 0  - scalar variance ratio (captures financial magnitude).
    Dims 1..383  - token-frequency projection via deterministic MD5 modulo.

    Determinism guarantee: all hash operations use hashlib.md5, which produces
    identical digests across interpreter restarts, OS reboots, and platforms.
    """
    vec = np.zeros(_EMBEDDING_DIM, dtype=np.float32)
    vec[0] = float(variance_ratio)

    for token in narration_tokens[:50]:
        token_clean = token.strip().upper()
        if not token_clean:
            continue
        h_int = _deterministic_md5_int(token_clean)
        dim_idx = (h_int % (_EMBEDDING_DIM - 1)) + 1  # maps to 1..383
        vec[dim_idx] += 1.0

    norm = float(np.linalg.norm(vec))
    return (vec / norm) if norm > 0.0 else vec


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two pre-normalised vectors."""
    return float(np.dot(a, b))


def _voucher_narration_tokens(voucher: DiscrepancyVoucher) -> List[str]:
    """
    Extracts pattern tokens from a DiscrepancyVoucher for embedding.
    Tokens are derived from discrepancy_type and the DSL expression so that
    structurally identical resolutions cluster tightly in vector space.
    """
    tokens: List[str] = []
    tokens.extend(voucher.discrepancy_type.replace("_", " ").split())
    dsl_tokens = (
        voucher.proposed_adjustment_dsl
        .replace("*", " ")
        .replace("/", " ")
        .replace("-", " ")
        .replace("+", " ")
        .replace("(", " ")
        .replace(")", " ")
        .split()
    )
    tokens.extend(dsl_tokens)
    return tokens


def _variance_ratio(variance_paise: int) -> float:
    """
    Normalises variance_paise to a comparable float using log1p scaling so
    that wildly different absolute amounts embed in a comparable range.
    """
    return float(math.log1p(abs(variance_paise)) / 20.0)  # 20 ~= log1p(5e8)


# ---------------------------------------------------------------------------
# EpisodicMemoryStore
# ---------------------------------------------------------------------------


class EpisodicMemoryStore:
    """
    SQLite-backed episodic memory for the RECON-MESH agent.

    Each method opens a fresh connection and explicitly closes it in a
    finally-block, guaranteeing the OS file handle is released on Windows
    immediately after each operation (safe for os.remove() in tests).

    Performance: On a cold SQLite file with <10 000 rows, both store and recall
    complete in <5 ms on commodity hardware (pure Python + NumPy, no network).
    """

    def __init__(self, db_path: str = "backend/data/episodic_memory.db") -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Private connection helper
    # ------------------------------------------------------------------

    @contextlib.contextmanager
    def _db(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager that opens a SQLite connection, yields it, and
        unconditionally closes it on exit so Windows releases the file handle.
        Uses isolation_level=None (autocommit) for explicit transaction control.
        """
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        try:
            yield conn
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """
        Creates both tables and indexes inside a single transaction.
        Idempotent: uses IF NOT EXISTS on every DDL statement.
        """
        with self._db() as conn:
            conn.execute("BEGIN;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vouchers (
                    voucher_id              TEXT PRIMARY KEY,
                    cluster_id              TEXT NOT NULL,
                    discrepancy_type        TEXT NOT NULL,
                    variance_paise          INTEGER NOT NULL,
                    proposed_adjustment_dsl TEXT NOT NULL,
                    double_entry_balanced   INTEGER NOT NULL,
                    audit_hash              TEXT NOT NULL,
                    created_at              TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_vouchers_type_variance
                ON vouchers (discrepancy_type, variance_paise);
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS resolution_memory (
                    id                  TEXT PRIMARY KEY,
                    pattern_signature   TEXT NOT NULL,
                    discrepancy_type    TEXT NOT NULL,
                    variance_ratio      REAL NOT NULL,
                    ast_dsl_formula     TEXT NOT NULL,
                    journal_template    TEXT NOT NULL,
                    embedding_json      TEXT NOT NULL,
                    usage_count         INTEGER DEFAULT 1,
                    last_applied        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("COMMIT;")

    # ------------------------------------------------------------------
    # Public API - DiscrepancyVoucher level
    # ------------------------------------------------------------------

    def store_voucher(self, voucher: DiscrepancyVoucher) -> None:
        """
        Persists a verified DiscrepancyVoucher in the ``vouchers`` table and
        simultaneously writes a feature-vector embedding to ``resolution_memory``
        so the precedent is immediately queryable via query_precedent().

        Idempotent: uses INSERT OR REPLACE keyed on voucher_id.
        """
        created_at_str = (
            voucher.created_at.isoformat()
            if isinstance(voucher.created_at, datetime)
            else str(voucher.created_at)
        )

        with self._db() as conn:
            conn.execute("BEGIN;")
            conn.execute(
                """
                INSERT OR REPLACE INTO vouchers
                    (voucher_id, cluster_id, discrepancy_type, variance_paise,
                     proposed_adjustment_dsl, double_entry_balanced, audit_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    voucher.voucher_id,
                    voucher.cluster_id,
                    voucher.discrepancy_type,
                    voucher.variance_paise,
                    voucher.proposed_adjustment_dsl,
                    int(voucher.double_entry_balanced),
                    voucher.audit_hash,
                    created_at_str,
                ),
            )
            conn.execute("COMMIT;")

        # Mirror into resolution_memory for cosine-similarity RAG recall.
        narration_tokens = _voucher_narration_tokens(voucher)
        v_ratio = _variance_ratio(voucher.variance_paise)
        self.store_verified_precedent(
            precedent_id=voucher.voucher_id,
            discrepancy_type=voucher.discrepancy_type,
            variance_ratio=v_ratio,
            narration_tokens=narration_tokens,
            ast_dsl_formula=voucher.proposed_adjustment_dsl,
            journal_template={
                "cluster_id": voucher.cluster_id,
                "variance_paise": voucher.variance_paise,
                "double_entry_balanced": voucher.double_entry_balanced,
                "audit_hash": voucher.audit_hash,
            },
        )

    def recall_similar(
        self,
        discrepancy_type: str,
        variance_paise: int,
        tolerance_paise: int = _DEFAULT_TOLERANCE_PAISE,
    ) -> List[DiscrepancyVoucher]:
        """
        Fast episodic recall returning all vouchers whose (discrepancy_type,
        variance_paise) fall within [variance_paise +/- tolerance_paise].

        Primary recall path : indexed SQLite range query  -> <1 ms warm cache.
        Secondary ranking   : cosine similarity re-ranking -> best match first.

        Returns an empty list when no match exists (never raises).
        """
        lo = variance_paise - tolerance_paise
        hi = variance_paise + tolerance_paise

        with self._db() as conn:
            cursor = conn.execute(
                """
                SELECT voucher_id, cluster_id, discrepancy_type, variance_paise,
                       proposed_adjustment_dsl, double_entry_balanced, audit_hash, created_at
                FROM   vouchers
                WHERE  discrepancy_type = ?
                  AND  variance_paise BETWEEN ? AND ?
                ORDER BY ABS(variance_paise - ?) ASC
                """,
                (discrepancy_type, lo, hi, variance_paise),
            )
            rows = cursor.fetchall()

        if not rows:
            return []

        query_tokens: List[str] = discrepancy_type.replace("_", " ").split()
        query_vec = _compute_feature_vector(_variance_ratio(variance_paise), query_tokens)

        scored: List[tuple] = []
        for row in rows:
            (
                voucher_id, cluster_id, disc_type, var_paise,
                dsl, balanced_int, audit_hash, created_at_str,
            ) = row

            sim = self._cosine_similarity_for(voucher_id, query_vec)
            if sim is None:
                band_width = max(tolerance_paise, 1)
                sim = 1.0 - abs(var_paise - variance_paise) / band_width

            try:
                created_at_dt = datetime.fromisoformat(created_at_str)
            except (ValueError, TypeError):
                created_at_dt = datetime.now(timezone.utc)

            vch = DiscrepancyVoucher(
                voucher_id=voucher_id,
                cluster_id=cluster_id,
                discrepancy_type=disc_type,
                variance_paise=var_paise,
                proposed_adjustment_dsl=dsl,
                double_entry_balanced=bool(balanced_int),
                audit_hash=audit_hash,
                created_at=created_at_dt,
            )
            scored.append((sim, vch))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [vch for _, vch in scored]

    # ------------------------------------------------------------------
    # Public API - resolution_memory (architecture-level RAG)
    # ------------------------------------------------------------------

    def store_verified_precedent(
        self,
        precedent_id: str,
        discrepancy_type: str,
        variance_ratio: float,
        narration_tokens: List[str],
        ast_dsl_formula: str,
        journal_template: Dict[str, Any],
    ) -> None:
        """
        Persists a newly verified resolution into ``resolution_memory`` for
        future cosine-similarity lookup via query_precedent().

        The 384-d feature vector is computed with deterministic MD5 hashing so
        it reproduces identically on every process invocation.
        """
        vec = _compute_feature_vector(variance_ratio, narration_tokens)
        emb_json = json.dumps(vec.tolist())
        journal_str = json.dumps(journal_template)
        pattern_sig = hashlib.md5(
            f"{discrepancy_type}:{variance_ratio:.6f}".encode("utf-8")
        ).hexdigest()

        with self._db() as conn:
            conn.execute("BEGIN;")
            conn.execute(
                """
                INSERT OR REPLACE INTO resolution_memory
                    (id, pattern_signature, discrepancy_type, variance_ratio,
                     ast_dsl_formula, journal_template, embedding_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    precedent_id,
                    pattern_sig,
                    discrepancy_type,
                    variance_ratio,
                    ast_dsl_formula,
                    journal_str,
                    emb_json,
                ),
            )
            conn.execute("COMMIT;")

    def query_precedent(
        self,
        variance_ratio: float,
        narration_tokens: List[str],
        similarity_threshold: float = 0.95,
    ) -> Optional[Dict[str, Any]]:
        """
        Cosine similarity lookup against all stored precedents.
        Returns the best match only if its similarity >= similarity_threshold.

        Typical latency: <5 ms for up to ~5 000 stored precedents on a
        modern SSD (pure NumPy dot products, no network I/O).
        """
        query_vec = _compute_feature_vector(variance_ratio, narration_tokens)

        with self._db() as conn:
            cursor = conn.execute(
                """
                SELECT id, discrepancy_type, ast_dsl_formula,
                       journal_template, embedding_json, usage_count
                FROM   resolution_memory
                """
            )
            rows = cursor.fetchall()

        if not rows:
            return None

        best_match: Optional[Dict[str, Any]] = None
        highest_sim: float = 0.0

        for row_id, disc_type, dsl, journal, emb_json, count in rows:
            stored_vec = np.array(json.loads(emb_json), dtype=np.float32)
            sim = _cosine_similarity(query_vec, stored_vec)
            if sim > highest_sim:
                highest_sim = sim
                best_match = {
                    "id": row_id,
                    "discrepancy_type": disc_type,
                    "ast_dsl_formula": dsl,
                    "journal_template": json.loads(journal),
                    "similarity": sim,
                    "usage_count": count,
                }

        if best_match and highest_sim >= similarity_threshold:
            self._increment_usage(best_match["id"])
            return best_match

        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cosine_similarity_for(
        self,
        voucher_id: str,
        query_vec: np.ndarray,
    ) -> Optional[float]:
        """
        Looks up the stored embedding for *voucher_id* in resolution_memory
        and returns its cosine similarity to *query_vec*, or None if absent.
        """
        with self._db() as conn:
            cursor = conn.execute(
                "SELECT embedding_json FROM resolution_memory WHERE id = ?",
                (voucher_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        stored_vec = np.array(json.loads(row[0]), dtype=np.float32)
        return _cosine_similarity(query_vec, stored_vec)

    def _increment_usage(self, precedent_id: str) -> None:
        """Atomically increments the usage counter for a stored precedent."""
        with self._db() as conn:
            conn.execute("BEGIN;")
            conn.execute(
                "UPDATE resolution_memory SET usage_count = usage_count + 1 WHERE id = ?",
                (precedent_id,),
            )
            conn.execute("COMMIT;")
