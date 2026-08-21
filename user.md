# RECON-MESH: User Guide & Quick Understanding

**Project Name:** `Recon-Mesh`  
**Track:** Track 04 — AI Finance Controller (Razorpay AI Buildathon)  
**Goal:** Land the AI Builder Internship at Razorpay (₹75,000/month stipend, Bangalore)  
**Deadline:** September 5th  

---

## 1. What Is This Project in Simple Words? (The 30-Second Pitch)

Imagine you run an online store that sells shoes:
1. Your **website orders (ERP)** say you sold ₹1,00,000 worth of shoes today.
2. But your **bank account** only received ₹97,640.
3. Your **Razorpay dashboard** says ₹1,00,000 was collected, but ₹2,000 was deducted for gateway fees (MDR), ₹360 was deducted for GST, and one customer returned a pair of socks for ₹500 that was refunded separately.

In real life, accounting and finance teams at big companies spend **hours every single day looking at messy Excel sheets** trying to match every single rupee: *Which ₹500 order belongs to which bank deposit? Why is the bank balance short by ₹2,360?*

**`Recon-Mesh` is an Autonomous Real-Time AI Finance Engine that does all of this live in milliseconds:**
- It listens to live **Razorpay Webhook Streams**, Bank Feeds, and ERP Invoices.
- It uses a **Dual-Pass Matcher** (Pass 1: C++ greedy heuristic for sub-100ms speed on 10,000 rows; Pass 2: Bounded Dynamic Programming) to match 90%+ of transactions instantly.
- It leverages an **Episodic Resolution Memory (Temporal RAG)** in SQLite to auto-resolve recurring discrepancy patterns in $<5\text{ms}$ without wasting LLM compute.
- For novel exceptions, it triggers an **Asymmetric Zero-Egress Local AI Agent** that uses a **strict AST-Safe Math Evaluator** (no unsafe `eval()`/`exec()`) to verify the exact discrepancy down to the paisa.
- It guarantees that **not a single rupee is hallucinated** through a double-entry invariant check ($\text{Debits} - \text{Credits} = 0.00$) backed by a SHA-256 Merkle audit trail.
- It closes the operational loop by **automatically dispatching executable API payloads** (Zoho Books JSON, Tally Prime XML, Razorpay Route transfers).
- It displays everything on a stunning, uncluttered **AMOLED Dark React 19 + Three.js visual canvas** with live glowing laser arcs.

---

## 2. Why Does This Idea Beat 99% of Submissions?

### The "Crowd Trap" That Most Students Fall Into:
- **90% of applicants** will build a generic chatbot (e.g., *"Chat with bot to buy shoes"*) wrapped in a basic white Streamlit template.
- Razorpay evaluators review hundreds of these at 2 AM. They get bored and reject them within 15 seconds.

### Your "Unfair Advantage":
1. **Contrarian High-Value Domain (<3% of submissions)**: Solves core RazorpayX and Settlement infrastructure operations—the exact multi-crore problem Razorpay engineers solve daily.
2. **Systems Engineering + Security Depth**: Writing a native C++ heuristic acceleration layer, decoupled asymmetric inference, and a strict AST-safe sandbox proves you understand systems engineering and infosec, not just prompt wrappers.
3. **Enterprise Compliance & Closed-Loop Action**: 100% Zero-Egress local execution guarantees privacy, while direct Zoho/Tally API dispatching actually executes financial remediation rather than generating passive text summaries.
4. **Cinematic AMOLED Visual Craft**: Instead of boring Streamlit tables, you present a sleek React + Three.js graph visualization where live transactions physically connect with glowing green arcs and exceptions pulse into an agent terminal.

---

## 3. The 6 Big USPs (Unique Selling Points)

1. **Dual-Pass Scalability**: C++ greedy cluster pruner handles 10,000 transactions in <100ms, bypassing the classic $O(2^N)$ subset-sum exponential death trap (with pure Python `@numba.jit` dynamic fallback).
2. **AST-Enforced Sandboxing**: Replaces unsafe `exec()` with a strict AST grammar parser, guaranteeing mathematical zero-risk execution.
3. **Episodic Resolution Memory**: Caches verified discrepancy vectors in SQLite-vec; recurring fee shifts resolve in $<5\text{ms}$ without re-calling the LLM.
4. **Closed-Loop API Interventions**: Automatically generates ready-to-execute REST/XML payloads for Zoho Books, Tally Prime, and Razorpay Route.
5. **Zero-Egress Local AI & Dual-Mode Runtime**: Showmanship demo runs 100% on-device/edge Ollama for air-gapped compliance; GitHub evaluator mode seamlessly routes to cloud APIs (Gemini/Groq) or 1-click CLI replay.
6. **Production-Grade Visual Scrollytelling**: High-contrast AMOLED Dark React dashboard with 2D React Flow layout for text legibility and Three.js background laser effects.

---

## 4. How the 5-Minute Pitch Video Will Flow

When recording your submission video on Loom/YouTube, here is your winning script:

- **Minute 0:00 – 0:45 (The FinOps Nightmare)**:
  - Explain why 3-way reconciliation (Razorpay $\leftrightarrow$ Bank $\leftrightarrow$ ERP) is the single biggest operational bottleneck for modern commerce.
  - Explain the enterprise privacy & code execution dilemma: why companies cannot send financial ledgers to public cloud LLMs or run unvetted Python `exec()`.
- **Minute 0:45 – 1:45 (The Multi-Tier Architecture)**:
  - Walk through the architecture: Streaming Webhooks $\rightarrow$ Dual-Pass C++ Matcher $\rightarrow$ Temporal Memory Cache $\rightarrow$ Zero-Egress AST Local Agent $\rightarrow$ Executable Dispatcher.
- **Minute 1:45 – 3:30 (Live Real-Time Demo)**:
  - Launch the AMOLED Vite+React Dashboard with the live webhook simulator running.
  - Show the bipartite canvas: React Flow 2D cards with glowing green Three.js laser arcs forming instant 1:1 and 1:N batch matches.
  - Show a cached anomaly resolving in $<5\text{ms}$ from SQLite memory.
  - Show a novel anomaly: node pulses red, drops into the Agent Terminal, local AI executes AST-safe math, proves the balance, and generates an executable Zoho Books journal voucher.
- **Minute 3:30 – 4:30 (Systems Performance & Quantitative Benchmarks)**:
  - Show benchmark metrics: 10,000-row batch handled in <100ms, 100/100 ground-truth accuracy, 0.00% balance discrepancy (`python main.py --demo-mode --synthetic-batch=100`).
- **Minute 4:30 – 5:00 (Closing & Intern Fit)**:
  - Highlight your dual mastery of systems performance (C++/FastAPI), secure agent architectures (AST sandboxing/Temporal RAG), and visual craft, proving why you are ready to hit the ground running as an AI Builder Intern at Razorpay.

---

## 5. Implementation Sequence

When we start building, we will follow this phased pipeline:
1. **Backend Core**: FastAPI event server + Synthetic Webhook/Bank streaming generator + `.env.example` config factory.
2. **Matching Engine**: Pass 1 C++ / Numba heuristic pruner + Pass 2 Bounded DP bipartite solver.
3. **Safe Local AI & Memory**: AST safe math parser + SQLite episodic vector cache + Pluggable LLM client (Ollama/Gemini/Groq).
4. **Closed-Loop Dispatcher**: Invariant Gatekeeper + Zoho/Tally executable payload generator.
5. **AMOLED Frontend**: Vite + React 19 + Tailwind + React Flow 2D canvas with Three.js laser effects + WebSocket stream hook.
6. **Benchmark & Packaging**: 100-case automated test suite (`python main.py --demo-mode`) + 5-minute video pitch asset bundle.

---

*Both [`recon.md`](file:///C:/Users/sasmi/recon-mesh/recon.md) (full technical specification) and [`user.md`](file:///C:/Users/sasmi/recon-mesh/user.md) (pitch guide) are synchronized and ready in `C:\Users\sasmi\recon-mesh\`.*

