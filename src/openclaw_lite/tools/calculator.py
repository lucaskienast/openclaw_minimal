"""Calculator tool — safe arithmetic expression evaluator."""
from __future__ import annotations

import ast
import math
import operator
from typing import Any

from openclaw_lite.tools.base import Tool, ToolContext

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

_UNARY_OPS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_FUNCTIONS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "ceil": math.ceil,
    "floor": math.floor,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pow": math.pow,
    "round": round,
}

_CONSTANTS = {"pi": math.pi, "e": math.e, "inf": math.inf}


def _eval(node: ast.expr) -> float:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        return _UNARY_OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise ValueError(f"unsupported function: {ast.dump(node.func)}")
        return _FUNCTIONS[node.func.id](*[_eval(a) for a in node.args])
    if isinstance(node, ast.Name):
        if node.id not in _CONSTANTS:
            raise ValueError(f"unsupported name: {node.id}")
        return _CONSTANTS[node.id]
    raise ValueError(f"unsupported expression node: {type(node).__name__}")


class CalculatorTool(Tool):
    name = "calculator"
    description = (
        "Evaluate an arithmetic expression. Supports basic ops, math functions "
        "(sqrt, abs, ceil, floor, log, sin, cos, tan, pow, round), and "
        "constants (pi, e, inf)."
    )
    input_schema = {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    }

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> str:
        expr = tool_input.get("expression", "")
        if not expr:
            return "Error: missing required parameter 'expression'"
        try:
            tree = ast.parse(expr, mode="eval")
            return str(_eval(tree.body))
        except Exception as e:
            return f"Error: {e}"
