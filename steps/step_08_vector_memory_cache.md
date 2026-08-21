# STEP 08: Vector Memory Cache & Temporal RAG (`memory_store.py`)

**Model Recommendation:** Heavier Model (e.g., Sonnet 3.7 / Gemini 1.5 Pro / GPT-4o)  
**Target Files:**  
- `backend/app/agent/memory_store.py`  
**Dependencies:** Python 3.10+, `sqlite3`, `numpy`, `hashlib` (optional `sqlite-vec`)

---

## 1. Domain Context & Objective
Memoryless LLM agents waste latency (2,000ms+ per call) and compute re-diagnosing recurring discrepancies that have already been resolved and verified (e.g., a known 2.5% dynamic MDR on international corporate cards or weekend RBI settlement lags).

The objective of Step 08 is to implement **Episodic Resolution Memory (Temporal Vector RAG)** using a local SQLite database (`memory_store.py`).
- It indexes verified historical resolutions by feature vectors (discrepancy ratio, fee deviation, narration pattern).
- For every new anomaly, it executes a fast cosine similarity query.
- **Cache Hit ($>0.95$ similarity)**: Instantly returns the verified precedent in **$<5\text{ms}$**, bypassing LLM invocation.
- **Cache Miss**: Routes to the LLM agent, and once verified by the Invariant Gatekeeper, writes the new resolution into SQLite memory.

---

## 2. Episodic Memory Architecture & Invariant

### ⚠️ Critical Invariant: Deterministic Hash for Cross-Process Stability
> [!IMPORTANT]
> **DO NOT use Python's built-in `hash(token)` function!**  
> In Python 3, `hash()` is randomized on every interpreter startup due to `PYTHONHASHSEED`. If `hash()` is used to project narration tokens into feature vectors, vectors created during one run will NOT match vectors during a subsequent run or test restart.  
> You **MUST** use a deterministic cryptographic hash like `int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)` to map tokens to feature vector dimensions.

```sql
CREATE TABLE IF NOT EXISTS resolution_memory (
    id TEXT PRIMARY KEY,
    pattern_signature TEXT NOT NULL,
    discrepancy_type TEXT NOT NULL,
    variance_ratio REAL NOT NULL,
    ast_dsl_formula TEXT NOT NULL,
    journal_template TEXT NOT NULL,
    embedding_json TEXT NOT NULL,
    usage_count INTEGER DEFAULT 1,
    last_applied TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. Implementation Specification (`backend/app/agent/memory_store.py`)

```python
import sqlite3
import json
import hashlib
import numpy as np
from typing import Optional, Dict, Any, List

class EpisodicMemoryStore:
    def __init__(self, db_path: str = "backend/data/episodic_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS resolution_memory (
                    id TEXT PRIMARY KEY,
                    pattern_signature TEXT NOT NULL,
                    discrepancy_type TEXT NOT NULL,
                    variance_ratio REAL NOT NULL,
                    ast_dsl_formula TEXT NOT NULL,
                    journal_template TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    usage_count INTEGER DEFAULT 1,
                    last_applied TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

    def _compute_feature_vector(self, variance_ratio: float, narration_tokens: List[str]) -> np.ndarray:
        """
        Creates a normalized 384-dimensional feature vector.
        Uses deterministic MD5 hashing to guarantee 100% vector reproducibility across interpreter restarts.
        """
        vec = np.zeros(384, dtype=np.float32)
        vec[0] = variance_ratio
        for token in narration_tokens[:50]:
            token_clean = token.strip().upper()
            if not token_clean:
                continue
            # Deterministic hash across all Python processes/restarts
            h_int = int(hashlib.md5(token_clean.encode('utf-8')).hexdigest(), 16)
            dim_idx = (h_int % 383) + 1  # Map to dimensions 1..383
            vec[dim_idx] += 1.0

        norm = float(np.linalg.norm(vec))
        return (vec / norm) if norm > 0 else vec

    def query_precedent(
        self,
        variance_ratio: float,
        narration_tokens: List[str],
        similarity_threshold: float = 0.95
    ) -> Optional[Dict[str, Any]]:
        """
        Performs sub-5ms cosine similarity lookup against stored precedents.
        """
        query_vec = self._compute_feature_vector(variance_ratio, narration_tokens)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, discrepancy_type, ast_dsl_formula, journal_template, embedding_json, usage_count FROM resolution_memory")
            rows = cursor.fetchall()

        best_match = None
        highest_sim = 0.0

        for row_id, disc_type, dsl, journal, emb_json, count in rows:
            stored_vec = np.array(json.loads(emb_json), dtype=np.float32)
            sim = float(np.dot(query_vec, stored_vec))
            if sim > highest_sim:
                highest_sim = sim
                best_match = {
                    "id": row_id,
                    "discrepancy_type": disc_type,
                    "ast_dsl_formula": dsl,
                    "journal_template": json.loads(journal),
                    "similarity": sim,
                    "usage_count": count
                }

        if best_match and highest_sim >= similarity_threshold:
            self._increment_usage(best_match["id"])
            return best_match

        return None

    def store_verified_precedent(
        self,
        precedent_id: str,
        discrepancy_type: str,
        variance_ratio: float,
        narration_tokens: List[str],
        ast_dsl_formula: str,
        journal_template: Dict[str, Any]
    ):
        """
        Persists a newly verified resolution voucher for future instant recall.
        """
        vec = self._compute_feature_vector(variance_ratio, narration_tokens)
        emb_json = json.dumps(vec.tolist())
        journal_str = json.dumps(journal_template)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO resolution_memory 
                (id, pattern_signature, discrepancy_type, variance_ratio, ast_dsl_formula, journal_template, embedding_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (precedent_id, discrepancy_type, variance_ratio, ast_dsl_formula, journal_str, emb_json))
            conn.commit()

    def _increment_usage(self, precedent_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE resolution_memory SET usage_count = usage_count + 1 WHERE id = ?", (precedent_id,))
            conn.commit()
```

---

## 4. Standalone Verification Command
```bash
python -c "
import os
from backend.app.agent.memory_store import EpisodicMemoryStore

db_file = 'backend/data/test_memory.db'
os.makedirs('backend/data', exist_ok=True)
if os.path.exists(db_file): os.remove(db_file)

store = EpisodicMemoryStore(db_path=db_file)
store.store_verified_precedent(
    precedent_id='prec_001',
    discrepancy_type='MDR_DRIFT_2.5',
    variance_ratio=0.0236,
    narration_tokens=['CORP', 'CARD', 'RZP'],
    ast_dsl_formula='GROSS * 250 // 10000',
    journal_template={'account': 'MDR Expense', 'debit': 25000}
)

match = store.query_precedent(0.0236, ['CORP', 'CARD', 'RZP'], similarity_threshold=0.90)
assert match is not None
assert match['discrepancy_type'] == 'MDR_DRIFT_2.5'
assert match['similarity'] > 0.99
print(f'✅ Step 08 Vector Memory Cache Verified with Deterministic MD5 Embeddings! (Cosine Similarity: {match[\"similarity\"]:.4f})')
"
```
