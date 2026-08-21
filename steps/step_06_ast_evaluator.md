# STEP 06: AST Safe Math Evaluator & Sandboxed Grammar (`ast_evaluator.py`)

**Model Recommendation:** Heavier Model (e.g., Sonnet 3.7 / Gemini 1.5 Pro / GPT-4o)  
**Target Files:**  
- `backend/app/agent/ast_evaluator.py`  
**Dependencies:** Python 3.10+ (Standard Library `ast`, `operator`, `hashlib`)

---

## 1. Domain Context & Objective
In enterprise FinOps and banking integrations (SOC-2, ISO-27001, DPDP compliance), **granting an AI agent raw code execution (`eval()` or `exec()`) is a catastrophic security vulnerability**. Hallucinated or malicious prompts can escape sandboxes, access environment variables, read private encryption keys, or corrupt ledger databases.

The objective of Step 06 is to build a **Strict Abstract Syntax Tree (AST) Safe Math Evaluator** (`ast_evaluator.py`). The local AI agent outputs a constrained Domain-Specific Language (DSL) arithmetic formula explaining any detected discrepancy. The AST evaluator parses the formula, validates every node against a strict whitelist, injects validated numeric symbol tables, and computes the exact mathematical proof down to the paisa with **zero RCE risk**.

---

## 2. Whitelist & Security Specifications

```
Allowed AST Nodes:
  • ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name
  • Operators: ast.Add (+), ast.Sub (-), ast.Mult (*), ast.FloorDiv (//), ast.Div (/), ast.USub (-val)

Explicitly Blocked (Raises SecurityViolationException):
  ❌ ast.Call (No function execution: os.system, open, exec, eval)
  ❌ ast.Attribute (No object traversal: __globals__, __subclasses__)
  ❌ ast.Import, ast.ImportFrom (No module loading)
  ❌ ast.Subscript, ast.Lambda, ast.ListComp, ast.DictComp
```

---

## 3. Implementation Specification (`backend/app/agent/ast_evaluator.py`)

```python
import ast
import operator
import hashlib
from typing import Dict, Any, Union

class SecurityViolationError(Exception):
    """Raised when an expression contains unauthorized AST nodes."""
    pass

class ASTSafeMathEvaluator:
    # Whitelisted binary and unary operators
    SAFE_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    ALLOWED_NODES = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Name,
        ast.Load,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.FloorDiv,
        ast.Mod,
        ast.USub,
        ast.UAdd
    )

    def __init__(self):
        pass

    def evaluate(self, expression_str: str, variables: Dict[str, Union[int, float]]) -> int:
        """
        Parses and evaluates a safe math expression in integer paise.
        """
        if not expression_str or len(expression_str) > 500:
            raise ValueError("Invalid expression length")

        try:
            tree = ast.parse(expression_str, mode='eval')
        except SyntaxError as e:
            raise ValueError(f"Syntax error in expression: {e}")

        # Security AST walk
        for node in ast.walk(tree):
            if not isinstance(node, self.ALLOWED_NODES):
                raise SecurityViolationError(
                    f"Forbidden AST Node '{type(node).__name__}' detected! Potential RCE attempt blocked."
                )

        result = self._eval_node(tree.body, variables)
        return int(round(result))

    def _eval_node(self, node: ast.AST, variables: Dict[str, Union[int, float]]) -> Union[int, float]:
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)):
                raise SecurityViolationError(f"Constant value must be numeric, got {type(node.value)}")
            return node.value

        elif isinstance(node, ast.Name):
            if node.id not in variables:
                raise ValueError(f"Undefined variable in expression: {node.id}")
            return variables[node.id]

        elif isinstance(node, ast.BinOp):
            left_val = self._eval_node(node.left, variables)
            right_val = self._eval_node(node.right, variables)
            op_type = type(node.op)
            if op_type not in self.SAFE_OPERATORS:
                raise SecurityViolationError(f"Unsupported binary operator: {op_type.__name__}")
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right_val == 0:
                raise ZeroDivisionError("Division by zero in formula")
            return self.SAFE_OPERATORS[op_type](left_val, right_val)

        elif isinstance(node, ast.UnaryOp):
            operand_val = self._eval_node(node.operand, variables)
            op_type = type(node.op)
            if op_type not in self.SAFE_OPERATORS:
                raise SecurityViolationError(f"Unsupported unary operator: {op_type.__name__}")
            return self.SAFE_OPERATORS[op_type](operand_val)

        else:
            raise SecurityViolationError(f"Unhandled node type: {type(node).__name__}")

    def generate_proof_hash(self, expression_str: str, result_paise: int) -> str:
        payload = f"{expression_str.strip()}:{result_paise}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
```

---

## 4. Standalone Verification Command
```bash
python -c "
from backend.app.agent.ast_evaluator import ASTSafeMathEvaluator, SecurityViolationError

evaluator = ASTSafeMathEvaluator()
symbols = {'GROSS': 10000000, 'MDR_BPS': 200, 'GST_PCT': 18}
# Calculate Net = GROSS - (GROSS * 200 // 10000) - ((GROSS * 200 // 10000) * 18 // 100)
dsl = 'GROSS - (GROSS * MDR_BPS // 10000) - ((GROSS * MDR_BPS // 10000) * GST_PCT // 100)'
net = evaluator.evaluate(dsl, symbols)
assert net == 9764000

# Verify RCE rejection:
try:
    evaluator.evaluate('__import__(\"os\").system(\"calc\")', {})
    assert False, 'Should have failed!'
except SecurityViolationError:
    print('🛡️ RCE Attack blocked successfully!')

print('✅ Step 06 AST Evaluator Verified Successfully!')
"
```
