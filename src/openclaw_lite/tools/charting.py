"""Charting tool — generates PNG charts using matplotlib."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from openclaw_lite.tools.base import Tool, ToolContext


class ChartingTool(Tool):
    name = "charting"
    description = "Create a chart (bar, line, pie, scatter) and save as PNG."
    input_schema = {
        "type": "object",
        "properties": {
            "chart_type": {
                "type": "string",
                "enum": ["bar", "line", "pie", "scatter"],
            },
            "title": {"type": "string"},
            "data": {
                "type": "object",
                "properties": {
                    "labels": {"type": "array", "items": {"type": "string"}},
                    "values": {"type": "array", "items": {"type": "number"}},
                },
                "required": ["labels", "values"],
            },
            "filename": {"type": "string"},
        },
        "required": ["chart_type", "title", "data"],
    }

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> str:
        chart_type = tool_input.get("chart_type", "bar")
        title = tool_input.get("title", "Chart")
        data = tool_input.get("data", {})
        filename = tool_input.get("filename", "chart.png")

        labels = data.get("labels", [])
        values = data.get("values", [])

        if not labels or not values:
            return "Error: data must contain non-empty 'labels' and 'values'"
        if len(labels) != len(values):
            return "Error: 'labels' and 'values' must have the same length"

        workspace = Path(context.workspace)
        workspace.mkdir(parents=True, exist_ok=True)
        output_path = workspace / filename

        fig, ax = plt.subplots(figsize=(8, 5))

        if chart_type == "bar":
            ax.bar(labels, values)
        elif chart_type == "line":
            ax.plot(labels, values, marker="o")
        elif chart_type == "pie":
            ax.pie(values, labels=labels, autopct="%1.1f%%")
        elif chart_type == "scatter":
            ax.scatter(range(len(values)), values)
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels)
        else:
            plt.close(fig)
            return f"Error: unsupported chart type '{chart_type}'"

        ax.set_title(title)
        fig.tight_layout()
        fig.savefig(str(output_path), dpi=100)
        plt.close(fig)

        return f"Chart saved to {filename}"
