# RECON-MESH: 12-Step Master Implementation Blueprint

Welcome to the production implementation roadmap for **RECON-MESH: Autonomous Real-Time Multi-Source 3-Way Financial Reconciliation & Discrepancy Resolution Engine** (Razorpay AI Buildathon — Track 04: AI Finance Controller).

---

## 🧭 Master Pipeline Map

```
STEP 01: Data Generator (generator.py)
   │ [Produces 100-record ground truth benchmark batch with 5 FinOps edge cases]
   ▼
STEP 02: Canonical Normalizer & Data Models (models.py, normalizer.py)
   │ [Pydantic v2 schemas, UTC ISO dates, SETTLED_PENDING_ERP state, exact paise engine]
   ▼
STEP 03: Python Heuristic Fallback Matcher (numba_fallback.py, greedy_pruner.py)
   │ [2-Stage Match: Settlement RZP<->Bank, then Ledger RZP<->ERP in <50ms with Numba]
   ▼
STEP 04: Native C++ Heuristic Pruner & Dynamic Factory (matcher.cpp, engine_factory.py)
   │ [PyBind11 native C++ accelerator matching 10,000 txns in <30ms with graceful fallback]
   ▼
STEP 05: Bounded DP Subset-Sum Solver (dp_solver.py)
   │ [Pass 2 dict-based knapsack solver safely handling negative paise refunds & batch deposits]
   ▼
STEP 06: AST Safe Math Evaluator & Grammar (ast_evaluator.py)
   │ [Strict Abstract Syntax Tree arithmetic sandbox blocking all eval()/exec() RCE risks]
   ▼
STEP 07: Pluggable LLM Provider Factory & Investigator (base_provider.py, investigator.py)
   │ [Edge Ollama 0-egress local node + Cloud fallback with strict AST DSL prompt token guards]
   ▼
STEP 08: Vector Memory Cache & Temporal RAG (memory_store.py)
   │ [SQLite-vec episodic memory with deterministic MD5 feature embeddings for <5ms hits]
   ▼
STEP 09: Invariant Gatekeeper, Merkle Audit & Dispatcher (invariant_gate.py, dispatcher.py)
   │ [Deterministic double-entry balance enforcer, SHA-256 Merkle root, Zoho/Tally API payloads]
   ▼
STEP 10: FastAPI Core Server, WebSocket & Real CLI Benchmark (routes.py, websocket.py, main.py)
   │ [FastAPI REST + WebSocket router, stream simulator, genuine non-mocked CLI benchmark]
   ▼
STEP 11: AMOLED Dark Frontend Foundation & State Engine (React 19 / Vite / Tailwind)
   │ [Anti-AI slop FinOps terminal design, throttled WebSocket hook, metrics HUD, terminal drawer]
   ▼
STEP 12: High-Density 2D Bipartite Board + Synced Three.js Laser Canvas (GraphCanvas.tsx)
   │ [2D React Flow node plane + camera-synced WebGL 1px glowing green laser arcs]
   ▼
🏁 FINISHED PRODUCTION PROJECT
```

---

## 📋 12-Step Implementation Directory & Model Routing Strategy

| Step | Component & Target File | Model Routing | Core Invariants & Engineering Guarantees |
| :---: | :--- | :---: | :--- |
| **01** | [`step_01_data_generator.md`](./step_01_data_generator.md)<br>`backend/app/benchmark/generator.py` | **Lighter Model** | Deterministic 100-record benchmark batch with all 5 enterprise FinOps edge cases. |
| **02** | [`step_02_canonical_normalizer.md`](./step_02_canonical_normalizer.md)<br>`backend/app/core/models.py`, `normalizer.py` | **Lighter Model** | Pydantic v2 schemas, UTC timestamps, `SETTLED_PENDING_ERP` status, paise integer arithmetic. |
| **03** | [`step_03_python_heuristic_matcher.md`](./step_03_python_heuristic_matcher.md)<br>`backend/app/core/matcher/numba_fallback.py` | **Heavier Model** | 2-Stage Matching (Settlement first, then Ledger join) resolving Tripartite ERP hazards in $<50\text{ms}$. |
| **04** | [`step_04_native_cpp_pruner.md`](./step_04_native_cpp_pruner.md)<br>`backend/app/core/matcher/native/matcher.cpp` | **Heavier Model** | Native C++ pruner matching 10,000 txns in $<30\text{ms}$ with PyBind11 and graceful dynamic loader. |
| **05** | [`step_05_bounded_dp_solver.md`](./step_05_bounded_dp_solver.md)<br>`backend/app/core/matcher/dp_solver.py` | **Heavier Model** | Bounded DP subset-sum solver using hash-map dict to safely handle signed/negative paise refunds. |
| **06** | [`step_06_ast_evaluator.md`](./step_06_ast_evaluator.md)<br>`backend/app/agent/ast_evaluator.py` | **Heavier Model** | Whitelisted AST grammar arithmetic parser with zero `eval()`/`exec()` RCE vulnerability. |
| **07** | [`step_07_llm_provider_factory.md`](./step_07_llm_provider_factory.md)<br>`backend/app/agent/base_provider.py` | **Lighter Model** | Edge Ollama 0-egress + Gemini/Groq cloud factory with strict AST single-expression token guard. |
| **08** | [`step_08_vector_memory_cache.md`](./step_08_vector_memory_cache.md)<br>`backend/app/agent/memory_store.py` | **Heavier Model** | SQLite-vec episodic memory with deterministic cross-process MD5 embeddings for $<5\text{ms}$ recall. |
| **09** | [`step_09_invariant_guardrail.md`](./step_09_invariant_guardrail.md)<br>`backend/app/guardrails/invariant_gate.py` | **Lighter Model** | Double-entry zero-sum check ($\sum \text{Dr} - \sum \text{Cr} = 0$), SHA-256 Merkle tree, Zoho/Tally payloads. |
| **10** | [`step_10_fastapi_core.md`](./step_10_fastapi_core.md)<br>`backend/app/api/routes.py`, `backend/main.py` | **Lighter Model** | FastAPI REST + WebSocket router, stream simulator, and real dynamic CLI benchmark runner. |
| **11** | [`step_11_frontend_foundation.md`](./step_11_frontend_foundation.md)<br>`frontend/src/App.tsx`, `useReconStream.ts` | **Lighter Model** | High-density AMOLED `#000000` FinOps terminal (Anti-AI Slop), throttled WebSocket buffer. |
| **12** | [`step_12_bipartite_visualizer.md`](./step_12_bipartite_visualizer.md)<br>`frontend/src/components/GraphCanvas.tsx` | **Heavier Model** | 2D React Flow viewport synchronized live with WebGL Three.js 1px green laser bezier arcs. |

---

## ⚡ 1-Click Verification Command
Once all 12 steps are complete, execute the full benchmark:
```bash
python backend/main.py --demo-mode --synthetic-batch=100
```
Expected output: 100.00% dynamic precision, 100.00% dynamic recall, 0 paise discrepancy variance, verified SHA-256 Merkle root.
