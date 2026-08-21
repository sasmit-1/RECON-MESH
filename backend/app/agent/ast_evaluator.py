"""
RECON-MESH AST Safe Math Evaluator & Sandboxed Grammar (Step 06)

Provides a strict whitelist-based Abstract Syntax Tree evaluator for agent-generated
financial arithmetic DSL expressions. Zero `eval()` / `exec()` usage — all evaluation
is performed by a recursive node walker constrained to an immutable whitelist of safe
arithmetic AST node types.

Security Guarantees:
  • ast.Call, ast.Attribute, ast.Import, ast.ImportFrom, ast.Subscript,
    ast.Lambda, ast.ListComp, ast.DictComp are explicitly detected and raise
    SecurityViolationError before any evaluation occurs.
  • Variables are injected from a validated numeric symbol table — no globals(),
    locals(), or builtins() access possible.
  • All intermediate and final results are numeric (int/float) and rounded back
    to integer paise with int(round(result)).

Compliance: SOC-2, ISO-27001, RBI DPDP — zero RCE risk.
"""

import ast
import hashlib
import operator
from typing import Dict, Union


# ---------------------------------------------------------------------------
# Custom Exception
# ---------------------------------------------------------------------------

class SecurityViolationError(Exception):
    """
    Raised when an expression string contains AST nodes outside the
    explicitly whitelisted arithmetic grammar. Any occurrence of this
    exception means a potential RCE attempt or policy violation has been
    detected and hard-blocked before any code execution occurs.
    """


# ---------------------------------------------------------------------------
# ASTSafeMathEvaluator
# ---------------------------------------------------------------------------

class ASTSafeMathEvaluator:
    """
    Strict AST-based arithmetic evaluator for RECON-MESH agent DSL expressions.

    Supports only:
      • Integer and float constants
      • Named variables injected from a caller-supplied symbol table
      • Binary operators: +, -, *, /, //, %
      • Unary operators: -(negation), +(identity)

    All other AST node types raise SecurityViolationError immediately.
    """

    # Mapping from AST operator node type to a pure-Python operator function.
    # This is the ONLY dispatch table used during evaluation — no getattr or
    # dynamic dispatch that could be subverted.
    SAFE_OPERATORS: Dict[type, object] = {
        ast.Add:      operator.add,
        ast.Sub:      operator.sub,
        ast.Mult:     operator.mul,
        ast.Div:      operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod:      operator.mod,
        ast.USub:     operator.neg,
        ast.UAdd:     operator.pos,
    }

    # Complete set of whitelisted AST node types.
    # Any node NOT in this tuple triggers SecurityViolationError.
    ALLOWED_NODES = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Name,
        ast.Load,
        # Operator nodes (children of BinOp.op / UnaryOp.op)
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.FloorDiv,
        ast.Mod,
        ast.USub,
        ast.UAdd,
    )

    # Nodes that are explicitly dangerous and must be named in the error message
    # for audit trail clarity. Checked inside the walk loop before the generic test.
    BLOCKED_NODES = (
        ast.Call,
        ast.Attribute,
        ast.Import,
        ast.ImportFrom,
        ast.Subscript,
        ast.Lambda,
        ast.ListComp,
        ast.DictComp,
        ast.SetComp,
        ast.GeneratorExp,
        ast.Await,
        ast.Yield,
        ast.YieldFrom,
        ast.Global,
        ast.Nonlocal,
        ast.Delete,
        ast.Exec if hasattr(ast, "Exec") else type(None),  # Python 2 remnant guard
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.Return,
        ast.Assert,
        ast.Raise,
        ast.Try,
        ast.With,
        ast.AsyncWith,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.If,
        ast.IfExp,
        ast.Assign,
        ast.AugAssign,
        ast.AnnAssign,
        ast.List,
        ast.Tuple,
        ast.Set,
        ast.Dict,
        ast.JoinedStr,  # f-strings
        ast.FormattedValue,
    )

    def evaluate(
        self,
        expression_str: str,
        variables: Dict[str, Union[int, float]],
    ) -> int:
        """
        Parses and evaluates a safe arithmetic expression, returning an integer paise result.

        Steps:
          1. Length sanity check (max 500 chars — prevents DoS via giant expression strings).
          2. Parse with mode='eval' (enforces single-expression constraint; statements disallowed).
          3. Full AST walk — any blocked or unrecognised node type raises SecurityViolationError.
          4. Recursive node evaluation using only whitelisted operator dispatch.
          5. Result rounded and cast to int (paise precision).

        Args:
            expression_str: Arithmetic DSL string produced by the AI agent.
            variables:       Numeric symbol table injected into Name node resolution.
                             Values must be int or float — no objects, callables, or strings.

        Returns:
            Integer paise result of the expression.

        Raises:
            SecurityViolationError: Any prohibited AST node detected.
            ValueError:             Syntax error, empty input, or undefined variable.
            ZeroDivisionError:      Division or modulo by zero.
        """
        if not expression_str or not expression_str.strip():
            raise ValueError("Expression string must not be empty.")

        if len(expression_str) > 500:
            raise ValueError(
                f"Expression exceeds maximum length of 500 characters (got {len(expression_str)})."
            )

        # Validate that all supplied variables are numeric types
        for var_name, var_val in variables.items():
            if not isinstance(var_val, (int, float)):
                raise ValueError(
                    f"Variable '{var_name}' must be int or float, got {type(var_val).__name__}."
                )

        try:
            tree = ast.parse(expression_str, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"Syntax error in DSL expression: {exc}") from exc

        # Security AST Walk — two-pass detection for clearer error messages
        for node in ast.walk(tree):
            # Pass 1: Explicitly named dangerous node types — detailed error
            if isinstance(node, self.BLOCKED_NODES):
                raise SecurityViolationError(
                    f"SECURITY VIOLATION: Explicitly blocked AST node "
                    f"'{type(node).__name__}' detected in expression. "
                    f"Potential RCE / sandbox escape attempt hard-blocked."
                )
            # Pass 2: Any node outside the whitelist — generic error
            if not isinstance(node, self.ALLOWED_NODES):
                raise SecurityViolationError(
                    f"SECURITY VIOLATION: Unrecognised AST node "
                    f"'{type(node).__name__}' is not in the arithmetic whitelist. "
                    f"Expression rejected."
                )

        result = self._eval_node(tree.body, variables)
        return int(round(result))

    def _eval_node(
        self,
        node: ast.AST,
        variables: Dict[str, Union[int, float]],
    ) -> Union[int, float]:
        """
        Recursively evaluates a whitelisted AST node.
        Only called after the full-tree security walk has passed.
        """
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)):
                raise SecurityViolationError(
                    f"Constant value must be numeric (int/float), got {type(node.value).__name__}."
                )
            return node.value

        if isinstance(node, ast.Name):
            if node.id not in variables:
                raise ValueError(
                    f"Undefined variable '{node.id}' in DSL expression. "
                    f"Available symbols: {sorted(variables.keys())}"
                )
            return variables[node.id]

        if isinstance(node, ast.BinOp):
            left_val = self._eval_node(node.left, variables)
            right_val = self._eval_node(node.right, variables)
            op_type = type(node.op)

            if op_type not in self.SAFE_OPERATORS:
                raise SecurityViolationError(
                    f"Unsupported binary operator '{op_type.__name__}' encountered during evaluation."
                )

            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right_val == 0:
                raise ZeroDivisionError(
                    f"Division by zero in DSL expression (operator: {op_type.__name__})."
                )

            op_fn = self.SAFE_OPERATORS[op_type]
            return op_fn(left_val, right_val)  # type: ignore[operator]

        if isinstance(node, ast.UnaryOp):
            operand_val = self._eval_node(node.operand, variables)
            op_type = type(node.op)

            if op_type not in self.SAFE_OPERATORS:
                raise SecurityViolationError(
                    f"Unsupported unary operator '{op_type.__name__}' encountered during evaluation."
                )

            op_fn = self.SAFE_OPERATORS[op_type]
            return op_fn(operand_val)  # type: ignore[operator]

        # Should be unreachable after the security walk, but defence-in-depth
        raise SecurityViolationError(
            f"Unhandled AST node type '{type(node).__name__}' reached the evaluator. "
            f"Expression rejected as a security precaution."
        )

    def generate_proof_hash(self, expression_str: str, result_paise: int) -> str:
        """
        Generates a SHA-256 proof hash binding the DSL expression to its evaluated result.

        The hash payload is the UTF-8 encoding of "{expression_str.strip()}:{result_paise}".
        This hash is stored in the Merkle audit ledger (Step 09) for cryptographic
        verifiability of every agent-proposed adjustment.

        Returns:
            64-character lowercase hex SHA-256 digest.
        """
        payload = f"{expression_str.strip()}:{result_paise}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
