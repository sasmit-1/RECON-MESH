# RECON-MESH: Critical Code Review & Technical Audit (`problems.md`)

**Target Event:** Razorpay AI Buildathon — Track 04 (AI Finance Controller)  
**Evaluator Perspective:** Principal Systems & FinOps Infrastructure Engineer at Razorpay  
**Document Status:** Comprehensive Code & Architecture Assessment

---

## 1. Executive Verdict & Scorecard

| Evaluation Dimension | Score | Verdict |
| :--- | :---: | :--- |
| **Domain Modeling & FinOps Rigor** | **9.5 / 10** | Exceptional modeling of 3-way reconciliation, integer paise arithmetic, MDR/GST statutory splits, and Indian banking narrations. |
| **Security & AST Sandboxing** | **9.5 / 10** | Outstanding whitelist-only AST evaluator (`ast_evaluator.py`); completely eliminates `eval()`/`exec()` RCE risks. |
| **Frontend UI/UX & Visual Craft** | **9.0 / 10** | Clean, razor-sharp Razorpay enterprise theme (React 19 + Tailwind + React Flow + Three.js WebGL laser overlays). |
| **Matching Algorithms (Pass 1 & Pass 2)** | **8.5 / 10** | Fast heuristic hash-map pruner and signed-integer knapsack DP handling negative refund paise correctly. |
| **System Integration ("Pitch vs. Code" Gap)** | **5.5 / 10** | **Critical Blocker**: Core modules (`ReconInvestigator`, `EpisodicMemoryStore`, WebSocket event broadcasting) are implemented as isolated files but **never wired into the execution pipeline**. |
| **DevOps & Packaging** | **6.0 / 10** | Missing `requirements.txt`; no automated unit test suite in `backend/tests/`. |
| **Overall Score** | **8.0 / 10** | **Strong Foundation with Great Potential, but needs pipeline wiring to reach a top 1% submission.** |

---

## 2. Critical Blockers & "Pitch vs. Code" Gaps

### 🚨 Gap 1: AI Agent & Temporal Vector RAG are Disconnected from the Pipeline
In `recon.md` and `user.md`, the architecture specifies:
$$\text{Pass 1 Heuristic} \longrightarrow \text{Pass 2 DP} \longrightarrow \text{Episodic Memory Cache} \longrightarrow \text{Zero-Egress LLM Agent} \longrightarrow \text{AST Proof}$$

**Reality in Code:**
1. In `backend/main.py:L116-L126` and `backend/app/api/routes.py:L104-L113`, the execution stops after Pass 2 DP:
   ```python
   # Stage 2: Bounded DP Solver on Residual Orphans
   dp_solver = BoundedDPSolver()
   pass2_clusters, final_orphan_rzp, final_orphan_bank = dp_solver.match_residual_orphans(
       orphan_rzp, orphan_bank
   )
   all_clusters = pass1_clusters + pass2_clusters
   # Invariant Gatekeeper & Merkle Audit runs ONLY on resolved clusters!
   ```
2. `ReconInvestigator` (`backend/app/agent/investigator.py`) is **never instantiated or called anywhere in the backend** outside its own file.
3. `EpisodicMemoryStore` (`backend/app/agent/memory_store.py`) is **never queried or written to** during batch reconciliation.
4. **Impact on Benchmarks**: In `backend/app/benchmark/generator.py`, 5% of synthetic data is designed with dispute holds/partial refunds (Case 4). Because the AI agent never processes these orphan bank credits, recall drops to **94.19% (81/86 clusters)** instead of resolving the exceptions.

---

### 🚨 Gap 2: WebSocket Streaming is a Disconnected Stub
In `backend/app/api/websocket.py:L96-L105`:
- When the UI sends `START_STREAM` or calls `/api/recon/stream/start`, the backend simply sends back `{"event": "STREAM_STATUS", "active": true}`.
- No background task starts consuming `stream_synthetic_events()` from `generator.py`.
- `manager.broadcast(...)` is defined on line 48 but **never invoked anywhere in the repository**.
- Consequently, clicking **"Start Stream"** in the UI does not produce live incoming transaction animations.

---

### 🚨 Gap 3: C++ Native Extension Bypasses Batch Matching
In `backend/app/core/matcher/native/matcher.cpp:L143-L220`, a C++ method `match_1toN_batch` is defined. However, in `backend/app/core/matcher/engine_factory.py:L110-L165`, `NativeMatcher.prune()` **only calls `match_1to1`**:
```python
# Stage 1A: C++ 1:1 UTR + amount + time window match
raw_matches = self._native_kernel.match_1to1(native_rzp, native_bank)
# Residuals are immediately bounced back to the Python pruner:
if residual_rzp or residual_bank:
    py_settled, orphan_rzp, orphan_bank = self._python_pruner.prune(
        residual_rzp, residual_bank, erp_txns
    )
```
The C++ 1:N batch matching logic is dead code.

---

## 3. Deep Component-by-Component Review & Code Deficiencies

### 3.1 Data Modeling & Canonical Normalizer
**Files:** `backend/app/core/models.py`, `backend/app/core/normalizer.py`

* **Strengths:**
  - Standardized integer paise representations across all entities (`amount_gross_paise`, `fee_mdr_paise`, `fee_gst_paise`, `amount_net_paise`) prevent floating-point inaccuracies.
  - Regex UTR token extractor (`normalizer.py:L116-L148`) effectively filters Indian banking noise tokens (`CMS`, `RZP`, `NEFT`, `RTGS`, `MUM`, `BLR`).
  - Strict 2-stage status separation (`MATCHED` vs. `SETTLED_PENDING_ERP` vs. `DISCREPANCY`) avoids false orphan alarms when ERP invoices arrive with latency.

* **Vulnerabilities / Edge Cases:**
  1. **String Amount Parsing Bug (`normalizer.py:L48-L53`)**:
     ```python
     d = Decimal(cleaned)
     if "." in cleaned or "," in amount:
         return int((d * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
     else:
         return int(d)
     ```
     If an ERP or webhook passes a raw rupee integer as a string (e.g. `"500"` for ₹500), it returns `500` paise (₹5). But if `"500.00"` is passed, it returns `50000` paise (₹500). This causes a 100x discrepancy depending on decimal presence.

---

### 3.2 Dynamic Programming Subset-Sum Solver
**File:** `backend/app/core/matcher/dp_solver.py`

* **Strengths:**
  - Uses `Dict[int, List[int]]` as a signed-hash table instead of a flat array, properly supporting negative net paise adjustments from customer refunds.
  - `_MAX_DP_STATES = 50_000` caps memory consumption against combinatorial explosion.

* **Flaws:**
  1. **Premature Candidate Window Truncation (`dp_solver.py:L160-L166`)**:
     ```python
     candidates = [
         r for r in remaining_rzp
         if abs((bank_item.timestamp_utc - r.timestamp_utc).total_seconds()) <= self.max_time_window_sec
     ][: self.max_cluster_size]
     ```
     `[: self.max_cluster_size]` slices the input array to the first 25 items before searching. If a batch contains 60 orphan transactions in the window, but the true subset consists of items #10, #30, and #45, the DP solver will fail because items #30 and #45 were dropped prior to evaluation.

---

### 3.3 Security & AST Math Evaluator
**File:** `backend/app/agent/ast_evaluator.py`

* **Strengths:**
  - Whitelist-only node traversal (`ast.Constant`, `ast.Name`, `ast.BinOp`, `ast.UnaryOp`).
  - Explicit blacklist for high-risk AST nodes (`ast.Call`, `ast.Attribute`, `ast.Import`, `ast.ListComp`, etc.).
  - Variables resolved strictly via a numeric symbol table without access to `eval()`, `exec()`, `globals()`, or `__builtins__`.
  - Exponentiation (`**` / `ast.Pow`) is excluded, preventing algorithmic complexity DoS attacks.
  - SHA-256 proof hash binding links expressions to evaluated paise outputs.

---

### 3.4 Episodic Memory Store & Temporal Vector RAG
**File:** `backend/app/agent/memory_store.py`

* **Strengths:**
  - Uses `hashlib.md5()` rather than Python's built-in `hash()`, guaranteeing deterministic vector projection across OS restarts and `PYTHONHASHSEED` changes.
  - Context manager explicitly closes SQLite connection on `__exit__`, preventing Windows file-lock issues during testing.
  - Dual-table architecture: exact range queries on `(discrepancy_type, variance_paise)` combined with 384-d cosine similarity re-ranking.

* **Flaws:**
  - Needs to be connected to the reconciliation loop so that unresolved exceptions query this store before calling an LLM.

---

### 3.5 Guardrails, Merkle Tree & ERP Dispatcher
**Files:** `backend/app/guardrails/invariant_gate.py`, `backend/app/guardrails/merkle_audit.py`, `backend/app/core/dispatcher.py`

* **Strengths:**
  - `InvariantGatekeeper.validate_double_entry` strictly enforces $\sum \text{Debits} - \sum \text{Credits} = 0 \text{ and } \sum \text{Debits} > 0$.
  - `ERPDispatcher` formats accurate payloads for Zoho Books (`POST /api/v3/journalentries`), Tally Prime XML (`<TALLYMESSAGE>`), and SAP S/4HANA OData (`API_JOURNALENTRY_CREATE`).

* **Flaws:**
  - **Memory Leak in Global Merkle Ledger (`routes.py:L28`)**:
    `_GLOBAL_LEDGER = MerkleAuditLedger()` accumulates leaf hashes continuously in memory across all HTTP requests. In a production environment, this will grow unbounded and mixes audit trees across independent batches.

---

### 3.6 Frontend Architecture & UX
**Files:** `frontend/src/App.tsx`, `frontend/src/components/ReconGraphCanvas.tsx`, `frontend/src/components/ThreeLaserArcOverlay.tsx`, `frontend/src/components/HUDMetricsBar.tsx`

* **Strengths:**
  - **Production-grade design aesthetic**: Razorpay `#2D65F8` palette, `#F4F6FA` canvas, and clean typographic hierarchy.
  - Three.js orthographic camera projection is synchronized with React Flow pan/zoom matrices (`ThreeLaserArcOverlay.tsx:L98-L114`).
  - 100ms buffered throttling in `useReconStream.ts:L212-L225` prevents React 19 rendering bottlenecks.

* **Flaws:**
  - Graph is currently bound to static batch responses; live streaming controls send WebSocket messages that receive only acknowledgments rather than streamed transaction nodes.

---

## 4. Missing Artifacts & Developer Experience

1. **No `requirements.txt`**: A clean `requirements.txt` is missing from the repository root, forcing external evaluators to guess Python package requirements.
2. **No Automated Unit Tests**: There are no test scripts in `backend/tests/` to verify invariants, DP bounds, or AST security violations automatically via `pytest`.

---

## 5. Prioritized Action Plan to Reach a 10/10 Score

### Action 1: Wire `ReconInvestigator` & `EpisodicMemoryStore` into the Pipeline
In `backend/main.py` and `backend/app/api/routes.py`, pass `final_orphan_rzp` and `final_orphan_bank` to the agent for investigation:
```python
# Pass 3: AI Exception Investigation & Episodic Resolution
if final_orphan_rzp or final_orphan_bank:
    investigator = ReconInvestigator()
    memory = EpisodicMemoryStore()
    
    for bank_orphan in final_orphan_bank:
        # 1. Check Episodic Memory Cache (<5ms)
        hit = memory.recall_similar("DISPUTE_RESERVE_HOLD", bank_orphan.amount_net_paise)
        if hit:
            # Apply precedent instantly
            pass
        else:
            # 2. Invoke Zero-Egress AI Agent + AST Evaluator
            voucher = await investigator.investigate_cluster(...)
            memory.store_voucher(voucher)
```

### Action 2: Activate Live WebSocket Event Streaming
In `backend/app/api/websocket.py`, start an asynchronous task running `stream_synthetic_events()` when `START_STREAM` is triggered, broadcasting `CLUSTER_MATCHED` payloads directly to the React canvas.

### Action 3: Resolve `to_paise` Heuristic Ambiguity
In `backend/app/core/normalizer.py:L27-L57`, normalize string numbers consistently:
```python
def to_paise(amount: Union[float, str, int, Decimal], is_rupees: bool = True) -> int:
    if isinstance(amount, int) and not is_rupees:
        return amount
    cleaned = str(amount).replace(",", "").strip()
    d = Decimal(cleaned)
    if is_rupees:
        return int((d * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
```

### Action 4: Add Root `requirements.txt`
Create a clean `requirements.txt` in the root directory:
```txt
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.3
numpy>=1.26.0
python-dateutil>=2.8.2
httpx>=0.26.0
python-dotenv>=1.0.0
websockets>=12.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```
