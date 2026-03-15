from __future__ import annotations

import ast
import operator

from openclaw_lite.tools.base import Tool, ToolContext, ToolRegistry

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _eval(node: ast.expr) -> float:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    raise ValueError(f"unsupported expression node: {type(node).__name__}")


class CalculatorTool(Tool):
    name = "calculator"
    description = "Evaluate a simple arithmetic expression like '3 * (4 + 2)'."
    input_schema = {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    }

    def run(self, tool_input: dict, context: ToolContext) -> str:
        tree = ast.parse(tool_input["expression"], mode="eval")
        return str(_eval(tree.body))


def register(registry: ToolRegistry) -> None:
    registry.register(CalculatorTool())
