# STEP 07: Pluggable LLM Provider Factory & AI Investigator (`base_provider.py`, `investigator.py`)

**Model Recommendation:** Lighter Model (e.g., Flash / Claude 3.5 Haiku / GPT-4o-mini)  
**Target Files:**  
- `backend/app/agent/base_provider.py`  
- `backend/app/agent/local_llm.py`  
- `backend/app/agent/groq_client.py`  
- `backend/app/agent/gemini_client.py`  
- `backend/app/agent/investigator.py`  
**Dependencies:** Python 3.10+, `httpx`, `pydantic` (optional `google-genai` / `groq`)

---

## 1. Domain Context & Objective
Financial enterprises cannot risk leaking confidential customer transaction data to public cloud APIs, while hackathon evaluators need zero-setup, instant execution on GitHub without requiring a local GPU or edge Ollama server.

The objective of Step 07 is to implement:
1. **`BaseLLMEngine` Abstract Factory**: A unified interface decoupling LLM inference from core business logic, supporting:
   - **Local Edge Node (`local_llm.py`)**: Ollama / llama.cpp (e.g., Qwen2 1.5B / Phi-3 Mini) on edge hardware for 100% air-gapped Zero-Egress compliance.
   - **Cloud Low-Latency Endpoints (`gemini_client.py`, `groq_client.py`)**: High-speed fallback for evaluators.
2. **`ReconInvestigator` (Chain-of-Verification Orchestrator)**: Guides the model through structured FinOps hypothesis generation, forcing the output of a deterministic AST math DSL and a balanced double-entry voucher.

---

## 2. LLM Provider Architecture

```
                       ┌──────────────────────┐
                       │   BaseLLMEngine      │ (Abstract Interface)
                       └──────────┬───────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  LocalOllamaLLM  │    │   GeminiLLM      │    │    GroqLLM       │
│  (Edge / 0-Egress)│   │ (Cloud Evaluator)│    │  (Sub-200ms LPU) │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

---

## 3. Implementation Details & System Prompt Invariant

### ⚠️ Critical System Prompt Rule: AST DSL Output Token Guard
> [!IMPORTANT]
> The AST Safe Evaluator (Step 06) evaluates the mathematical hypothesis in `mode='eval'`. If the LLM generates variable assignments (e.g. `let x = ...` or `total = ...`), code comments (`// deduct fees`), or multiple statements, the evaluator will immediately fail with a `SyntaxError` or `SecurityViolationError`.
>
> In `investigator.py`, the system prompt MUST include this exact instruction:
> ```
> CRITICAL AST DSL SYNTAX CONSTRAINT:
> For the 'ast_math_dsl' field: Output ONLY a single, raw, continuous arithmetic expression string evaluating to the final net integer paise. 
> - ALLOWED OPERATORS: +, -, *, //, /
> - ALLOWED SYMBOLS: GROSS, NET, MDR, GST, BANK_DEPOSIT, ESCROW_HOLD, numeric constants (e.g., 200, 10000, 18, 100).
> - FORBIDDEN: Do NOT use variable assignments (e.g. 'x = ...'), statements, comments, semicolons, quotes, or function calls.
> - VALID EXAMPLE: "GROSS - (GROSS * 250 // 10000) - ((GROSS * 250 // 10000) * 18 // 100)"
> - INVALID EXAMPLE: "let net = GROSS - fee; // result" (WILL BE HARD-REJECTED)
> ```

### A. Base Provider Interface (`backend/app/agent/base_provider.py`)

```python
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any

class BaseLLMEngine(ABC):
    @abstractmethod
    async def generate_resolution(self, system_prompt: str, user_prompt: str) -> str:
        """Returns the full text / JSON response from the LLM."""
        pass

    @abstractmethod
    async def stream_reasoning(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        """Streams token-by-token reasoning for live UI terminal playback."""
        pass
```

### B. Factory Router (`backend/app/agent/base_provider.py`)

```python
import os

def get_llm_engine() -> BaseLLMEngine:
    use_edge = os.getenv("USE_EDGE_INFERENCE", "false").lower() == "true"
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if use_edge or provider == "local_ollama":
        from backend.app.agent.local_llm import LocalOllamaLLM
        return LocalOllamaLLM(
            endpoint=os.getenv("EDGE_NODE_URL", "http://127.0.0.1:11434"),
            model=os.getenv("EDGE_MODEL_NAME", "qwen2:1.5b-instruct-q4_K_M")
        )
    elif provider == "groq":
        from backend.app.agent.groq_client import GroqLLM
        return GroqLLM(api_key=os.getenv("GROQ_API_KEY", ""))
    else:
        from backend.app.agent.gemini_client import GeminiLLM
        return GeminiLLM(api_key=os.getenv("GEMINI_API_KEY", ""))
```

### C. Structured Investigator Output Specification (`backend/app/agent/investigator.py`)

```json
{
  "hypothesis": "MDR rate drift from 2.0% to 2.5% on international card payment",
  "discrepancy_type": "MDR_DRIFT",
  "ast_math_dsl": "GROSS - (GROSS * 250 // 10000) - ((GROSS * 250 // 10000) * 18 // 100)",
  "journal_entries": [
    {"account": "Bank Account", "debit_paise": 9705000, "credit_paise": 0},
    {"account": "Razorpay Fee Expense (MDR)", "debit_paise": 250000, "credit_paise": 0},
    {"account": "Input GST Recoverable", "debit_paise": 45000, "credit_paise": 0},
    {"account": "Accounts Receivable", "debit_paise": 0, "credit_paise": 10000000}
  ],
  "confidence": 0.98
}
```

---

## 4. Standalone Verification Command
```bash
python -c "
from backend.app.agent.base_provider import get_llm_engine
engine = get_llm_engine()
assert engine is not None
print('✅ Step 07 LLM Provider Factory Loaded Successfully! (Active Provider:', type(engine).__name__, ')')
"
```
