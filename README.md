<div align="center">

# ⚡ RECON-MESH
### Autonomous Multi-Source 3-Way Financial Reconciliation Engine & Invariant Gatekeeper

[![Build Status](https://img.shields.io/badge/build-passing-059669.svg?style=flat-square)](https://github.com/sasmit-1/RECON-MESH)
[![Tests](https://img.shields.io/badge/pytest-8%2F8%20passed%20(100%25)-059669.svg?style=flat-square)](https://github.com/sasmit-1/RECON-MESH)
[![Ground Truth Benchmark](https://img.shields.io/badge/ground%20truth%20benchmark-100.00%25%20precision%20%2F%20recall-2D65F8.svg?style=flat-square)](https://github.com/sasmit-1/RECON-MESH)
[![Variance Delta](https://img.shields.io/badge/variance%20delta-%E2%82%B90.00%20(0%20paise)-059669.svg?style=flat-square)](https://github.com/sasmit-1/RECON-MESH)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%20FastAPI-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Frontend](https://img.shields.io/badge/frontend-React%2019%20%7C%20TypeScript%20%7C%20Tailwind-61DAFB.svg?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Audit](https://img.shields.io/badge/audit-SHA--256%20Merkle%20Ledger-4F46E5.svg?style=flat-square)](https://github.com/sasmit-1/RECON-MESH)
[![Track](https://img.shields.io/badge/Track-04%3A%20AI%20Finance%20Controller-2D65F8.svg?style=flat-square)](https://github.com/sasmit-1/RECON-MESH)

**Track 04: AI Finance Controller — Razorpay AI Buildathon**  
*Autonomous Real-Time Reconciliation of Payment Gateways (Razorpay), Core Banking Feeds (CAMT.053 / MT940), and ERP General Ledgers (Zoho Books / TallyPrime / SAP S/4HANA).*

---

### 🎥 Live Engine Preview
![RECON-MESH Demo Walkthrough](assets/demo-preview.gif)

> 📹 **[Watch the Full Demo Recording (assets/demo-video.mp4)](assets/demo-video.mp4)**

</div>

---

## 🧭 Executive Overview

Digital enterprises process millions of transactions daily across fragmented, asynchronous financial pipelines:
1. **Payment Gateways (Razorpay):** Gross customer charges, partial refunds, 2.0% MDR fees, and 18% statutory GST.
2. **Core Bank Statements (CAMT.053 / MT940):** Net lump-sum settlement credits, clearing narrations, and timing lag.
3. **ERP General Ledgers (Zoho Books / Tally / SAP):** Invoices raised, Accounts Receivable, and journal postings.

In production FinOps, standard rule-based scripts break on complex real-world anomalies, manual reconciliation takes days, and generic LLM wrappers are fundamentally dangerous due to floating-point rounding drift, hallucinations, and Remote Code Execution (RCE) vulnerabilities.

**RECON-MESH** solves this with an industrial **3-Pass Reconciliation Kernel**:
- **Pass 1 (Heuristic Pruner):** $O(N)$ hash-map UTR & settlement pruner in C++ SIMD / Python Numba resolving 1:1 matches and batch metadata in $<30\text{ms}$.
- **Pass 2 (Bounded DP Knapsack Solver):** Exact 0-1 subset-sum solver matching unindexed 1-to-N batch deposits and customer refund debits over signed integer paise hash tables.
- **Pass 3 (Forensic AI Agent & AST Sandbox):** Sub-5ms SQLite episodic memory recall + LLM anomaly analyzer evaluated through a strict, whitelist-only Abstract Syntax Tree (AST) arithmetic parser with zero `eval()`/`exec()`.
- **Double-Entry Invariant Gatekeeper & Merkle Tree:** Non-negotiable mathematical validation ($\sum \text{Debits} - \sum \text{Credits} = 0$) and cryptographic SHA-256 Merkle audit trail.

---

## 🏛️ System Architecture

```
════════════════════════════════════════════════════════════════════════════════════════════════════
                                  RECON-MESH ARCHITECTURE PIPELINE
════════════════════════════════════════════════════════════════════════════════════════════════════

     [Razorpay Webhooks]                [Bank Feeds (MT940)]             [ERP Invoices (Zoho/SAP)]
     (Gross ₹, MDR, GST, UTR)           (Net Credit ₹, Narration)        (Invoice ID, AR Account)
              │                                  │                                  │
              └──────────────────────────────────┼──────────────────────────────────┘
                                                 │
                                                 ▼
                                     ┌───────────────────────┐
                                     │  Canonical Normalizer │ (Exact 64-Bit Integer Paise)
                                     └───────────┬───────────┘
                                                 │
                   ┌─────────────────────────────┼─────────────────────────────┐
                   │                             │                             │
                   ▼                             ▼                             ▼
        ┌──────────────────────┐      ┌──────────────────────┐      ┌──────────────────────────────┐
        │  PASS 1: HEURISTIC   │      │    PASS 2: BOUNDED   │      │   PASS 3: EPISODIC MEMORY    │
        │    GREEDY PRUNER     │      │   KNAPSACK DP SOLVER │      │   + FORENSIC AI AGENT (AST)  │
        │                      │      │                      │      │                              │
        │ • C++ / Numba SIMD   │      │ • Signed Paise Table │      │ • <5ms SQLite-vec Precedents │
        │ • 1:1 UTR Hash Index │      │ • 1:N Batch Knapsack │      │ • Zero-Egress Air-Gapped LLM │
        │ • 2-Stage ERP Join   │      │ • Refund Debits Sub- │      │ • Whitelisted AST Evaluator  │
        │ • SETTLED_PENDING_ERP│      │   set-Sum Resolution │      │ • SHA-256 Proof Hash Binding │
        └──────────┬───────────┘      └──────────┬───────────┘      └──────────────┬───────────────┘
                   │                             │                                 │
                   └─────────────────────────────┼─────────────────────────────────┘
                                                 │
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │ Double-Entry Invariant Gate │ (∑ Debits - ∑ Credits == 0.00)
                                  └──────────────┬──────────────┘
                                                 │
                                  ┌──────────────┴──────────────┐
                                  │ Cryptographic Merkle Ledger │ (Binary SHA-256 Audit Tree)
                                  └──────────────┬──────────────┘
                                                 │
                                  ┌──────────────┴──────────────┐
                                  │ Closed-Loop ERP Dispatcher  │ (Zoho Books / Tally / SAP API)
                                  └─────────────────────────────┘
```

---

## 🔬 Core Engineering Innovations

### 1. Exact 64-Bit Integer Paise Normalizer (`models.py`, `normalizer.py`)
- Standard floating-point math (`0.1 + 0.2 = 0.30000000000000004`) causes cumulative ledger drift over enterprise volumes.
- All monetary amounts are quantized into **exact 64-bit integer paise** ($1\text{ INR} = 100\text{ Paise}$).
- Strips 27+ noisy Indian banking narration prefixes (`CMS`, `RZP`, `NEFT`, `RTGS`, `IMPS`, `UPI`) to isolate pure transaction tokens.

### 2. 2-Stage Heuristic Pruning & State Machine (`greedy_pruner.py`, `matcher.cpp`)
- Solves the **Tripartite Timing Asymmetry**: Gateway webhooks arrive in 4 hours, ERP invoices take 24–48 hours, and holiday bank settlements take 3–4 days.
- **Stage 1:** Settles Razorpay charges against Bank Statement deposits.
- **Stage 2:** Joins ERP invoices on `order_id`, safely assigning `SETTLED_PENDING_ERP` (🟠) when an invoice is pending rather than raising false orphan alarms.

### 3. Bounded DP Knapsack Subset-Sum Solver (`dp_solver.py`)
- Unindexed 1-to-N batch settlements bundle multiple customer payments minus concurrent refunds into single lump-sum bank credits with zero foreign keys.
- Operates on a signed integer hash table (`dict[int, list[int]]`). Negative refund debits shift state keys left safely without array index wrapping or `IndexError`.
- Combinatorial depth is bounded to $K \le 25$ items and guarded by `_MAX_DP_STATES = 50,000`.

### 4. Whitelisted AST Safe Math Evaluator (`ast_evaluator.py`)
- Eliminates Python `eval()` and `exec()` Remote Code Execution (RCE) vulnerabilities.
- Recursively inspects arithmetic formulas generated by the AI agent against an explicit node whitelist (`ast.BinOp`, `ast.UnaryOp`, `ast.Constant`, `ast.Name`).
- Rejects function calls, imports, lambdas, comprehensions, and attribute accesses with `SecurityViolationError`.
- Computes an immutable proof hash: $\text{SHA256}(\text{DSL} \parallel \text{Paise Result})$.

### 5. SQLite Episodic Resolution Memory & Temporal RAG (`memory_store.py`)
- Caches verified anomaly precedents as 384-dimensional deterministic MD5 feature vectors.
- Range-queries on `(discrepancy_type, variance_paise)` followed by cosine similarity ranking resolve repeat anomalies in **$<5\text{ms}$** without calling external LLMs.

### 6. Invariant Gatekeeper & Binary Merkle Audit Ledger (`invariant_gate.py`, `merkle_audit.py`)
- Enforces strict statutory accounting invariants:
  $$\sum \text{Debits} - \sum \text{Credits} = 0 \quad \text{and} \quad \text{GST} = \text{round}(\text{MDR} \times 0.18)$$
- Generates a tamper-evident binary SHA-256 Merkle root across all settled transactions and adjustment vouchers. A 1-paisa modification invalidates the cryptographic proof.

---

## 🖥️ User Interface & Bipartite Financial Canvas

### 1. 3-Column Bipartite Financial Board (`1 Cluster = 1 Row`)
![Bipartite Financial Board](assets/dashboard-canvas.png)

- **Column 1 (Razorpay Feeds):** Gross ₹, MDR fee, 18% GST fee, UTR, and `(Batch 1:N)` badge.
- **Column 2 (Bank Statement):** Net Credit ₹, clearing narration, and value date.
- **Column 3 (ERP / GL Ledger):** Invoice reference, AR account, and posting status.
- **Pure Horizontal Edges:** Guaranteed 1:1:1 horizontal alignment ($y = \text{rowIndex} \times 175\text{px}$) eliminates vertical ladder steps, diagonal crossings, and blank column gaps.

### 2. Granular Investigation Drawer & Closed-Loop ERP Dispatch
![Investigation Drawer](assets/investigation-drawer.png)

- Clicking any cluster card opens the slide-over drawer:
  - **Financial Summary:** Expected Net vs. Bank Credit vs. Discrepancy Delta.
  - **Granular Line Items:** Complete itemized breakdown of all individual payments within a 1:N batch.
  - **AST Adjustment Formula:** Validated mathematical proof (`NET_SETTLEMENT = GROSS − MDR − GST`).
  - **SHA-256 Audit Hash:** Tamper-proof leaf verification.
  - **1-Click ERP Dispatch:** Formatted payload dispatch to **Zoho Books**, **TallyPrime**, and **SAP S/4HANA**.

---

## 📊 Quantitative Benchmark Evaluation

Execution of the genuine 100-batch multi-source benchmark (`python backend/main.py --demo-mode --synthetic-batch=100`):

![CLI Benchmark Terminal](assets/cli-benchmark.png)

| Benchmark Metric | Measured Result | Evaluation Standard | Status | Context |
| :--- | :---: | :---: | :---: | :--- |
| **Invariant Precision** | **100.00%** | $\ge 99.50\%$ | **PASSED** | Synthetic Ground Truth Invariant Convergence |
| **Invariant Recall** | **100.00%** | $\ge 99.50\%$ | **PASSED** | Zero Omissions & Exact Integer Subset-Sum Proof |
| **Discrepancy Variance** | **₹0.00 (0 paise)** | $\text{INR } 0.00$ | **PASSED** | Zero Floating-Point Drift (64-Bit Integer Math) |
| **End-to-End Latency** | **34.78 ms** | $<500\text{ ms}$ | **PASSED** | Real-time C++ / Numba SIMD Execution |
| **Total Records Processed** | **286 transactions** | 100 batch (3-way) | **PASSED** | Razorpay Feeds + Bank Deposits + ERP Invoices |
| **Pass 1 Resolved** | **71 clusters** | Heuristic Pruner | **PASSED** | 1:1 Hash Index & 2-Stage Settlement Join |
| **Pass 2 Resolved** | **10 clusters** | DP Knapsack Solver | **PASSED** | 1:N Batch & Signed Refund Subset-Sum |
| **Pass 3 AI Resolved** | **5 clusters** | Forensic AI Agent | **PASSED** | Episodic Memory & AST Sandbox Proof |
| **Double-Entry Invariants** | **100% VERIFIED** | Zero-Sum Gate | **PASSED** | Non-Negotiable Double-Entry Audit Gatekeeper |

> 💡 **Benchmark Interpretation:** The 100.00% metric is a formal mathematical proof of the engine's double-entry invariants on synthetic ground truth, validating zero floating-point drift and exact integer subset-sum knapsack convergence across 1:1 settlements, 1:N batch deposits, and refund debits.

---

## 🧪 Automated Pytest Test Suite

Execution of the full 8-layer test suite (`pytest backend/tests/ -v`):

![Pytest Test Suite](assets/pytest-suite.png)

```bash
pytest backend/tests/ -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.11.5, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\my github projects\razorpay
configfile: pytest.ini

backend/tests/test_recon_pipeline.py::test_zero_sum_invariant_gate PASSED           [ 12%]
backend/tests/test_recon_pipeline.py::test_ast_safe_evaluator_whitelist PASSED      [ 25%]
backend/tests/test_recon_pipeline.py::test_3way_batch_pipeline_100pct PASSED        [ 37%]
backend/tests/test_recon_pipeline.py::test_merkle_tree_integrity PASSED            [ 50%]
backend/tests/test_recon_pipeline.py::test_normalizer_integer_paise_edge_cases PASSED [ 62%]
backend/tests/test_recon_pipeline.py::test_dp_solver_signed_paise PASSED           [ 75%]
backend/tests/test_recon_pipeline.py::test_episodic_memory_store PASSED            [ 87%]
backend/tests/test_recon_pipeline.py::test_fastapi_rest_routes PASSED              [100%]

============================== 8 passed in 1.41s ==============================
```

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+ (Recommended: Python 3.11)
- Node.js 18+ & npm

### 1. Clone & Setup Backend
```bash
git clone https://github.com/sasmit-1/RECON-MESH.git
cd RECON-MESH

# Create & activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run 1-Click Headless CLI Benchmark
```bash
python backend/main.py --demo-mode --synthetic-batch=100
```

### 3. Run Automated Tests
```bash
pytest backend/tests/ -v
```

### 4. Launch Full-Stack Visualizer
```bash
# Terminal 1: Start FastAPI Server
python backend/main.py --port=8000

# Terminal 2: Start React 19 Frontend
cd frontend
npm install
npm run dev
```
Open **`http://localhost:5173`** in your browser.

---

## 📂 Repository Structure

```
.
├── assets/                            # Demo video, animated GIF, and verified UI screenshots
│   ├── cli-benchmark.png              # Headless CLI benchmark execution screenshot
│   ├── dashboard-canvas.png           # 3-column bipartite financial board screenshot
│   ├── demo-preview.gif               # Animated hero walkthrough GIF
│   ├── demo-video.mp4                 # Full recorded video pitch
│   ├── investigation-drawer.png       # Slide-over drawer with AST proofs & line items
│   └── pytest-suite.png               # 8/8 spotless pytest verification screenshot
├── backend/
│   ├── app/
│   │   ├── agent/                     # Pass 3 Forensic AI Agent & Sandboxing
│   │   │   ├── ast_evaluator.py       # Strict whitelisted AST parser & proof hash
│   │   │   ├── base_provider.py       # Pluggable LLM factory router
│   │   │   ├── gemini_client.py       # Google Gemini 1.5 Flash client
│   │   │   ├── groq_client.py         # Groq LPU ultra-low latency client
│   │   │   ├── investigator.py        # Forensic exception investigator
│   │   │   ├── local_llm.py           # Zero-egress local edge node client (Ollama/Phone)
│   │   │   ├── memory_store.py        # SQLite episodic memory with 384-d vector RAG
│   │   │   └── offline_fallback.py    # Zero-config deterministic fallback engine
│   │   ├── api/                       # REST Endpoints & WebSockets
│   │   │   ├── routes.py              # FastAPI REST endpoints (/health, /recon, /dispatch)
│   │   │   └── websocket.py           # Real-time WebSocket streaming manager
│   │   ├── benchmark/
│   │   │   └── generator.py           # 5-topology ground-truth synthetic data generator
│   │   ├── core/                      # Core Financial & Normalization Engine
│   │   │   ├── dispatcher.py          # Zoho / Tally / SAP closed-loop dispatchers
│   │   │   ├── matcher/
│   │   │   │   ├── dp_solver.py       # Bounded DP knapsack subset-sum solver (Pass 2)
│   │   │   │   ├── engine_factory.py  # Dual-mode engine factory (C++ SIMD vs Numba JIT)
│   │   │   │   ├── greedy_pruner.py   # 2-Stage Heuristic pruner (Pass 1)
│   │   │   │   ├── native/
│   │   │   │   │   ├── matcher.cpp    # PyBind11 C++ SIMD matching kernel
│   │   │   │   │   └── setup.py       # C++ extension compilation script
│   │   │   │   └── numba_fallback.py  # Vectorized Numba JIT fallback pruner
│   │   │   ├── models.py              # Canonical Pydantic v2 domain schemas
│   │   │   └── normalizer.py          # Exact integer paise sanitizer & UTR extractor
│   │   └── guardrails/                # Accounting Invariants & Merkle Ledger
│   │       ├── invariant_gate.py      # Double-entry zero-sum mathematical firewall
│   │       └── merkle_audit.py        # Binary SHA-256 Merkle audit tree
│   ├── main.py                        # Server entry point & 1-Click CLI Benchmark runner
│   ├── requirements.txt               # Backend Python dependencies
│   └── tests/
│       └── test_recon_pipeline.py     # 8 automated pytest validation suites
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # Main workspace layout & lane headers
│   │   ├── components/
│   │   │   ├── ControlHeader.tsx      # Ingestion controls (100 / 500 / 1000) & stream toggle
│   │   │   ├── CustomTransactionNode.tsx # 3-column financial transaction cards
│   │   │   ├── HUDMetricsBar.tsx      # Live telemetry bar (Accuracy, Variance, Merkle)
│   │   │   ├── InvestigationDrawer.tsx # Slide-over showing AST proofs & journal vouchers
│   │   │   ├── LiveAuditTerminal.tsx  # Collapsible live audit log terminal
│   │   │   └── ReconGraphCanvas.tsx   # 1:1:1 React Flow 2D bipartite canvas
│   │   ├── hooks/
│   │   │   └── useReconStream.ts      # 100ms buffered WebSocket streaming hook
│   │   └── types/
│   │       └── recon.ts               # TypeScript canonical domain schemas
│   ├── package.json                   # Frontend dependencies
│   └── vite.config.ts                 # Vite bundler configuration
├── pytest.ini                         # Pytest configuration & warning suppression
├── requirements.txt                   # Root Python dependencies
└── README.md                          # Master Production Documentation
```

---

<div align="center">

**Built with precision for the Razorpay AI Buildathon — Track 04 (AI Finance Controller).**  
*Autonomous, Mathematically Proven, and Cryptographically Verifiable FinOps Infrastructure.*

</div>
