"""Unit tests for charting tool."""
from __future__ import annotations

from pathlib import Path

import pytest

from openclaw_lite.tools.charting import ChartingTool
from openclaw_lite.tools.base import ToolContext


@pytest.fixture()
def tool() -> ChartingTool:
    return ChartingTool()


@pytest.fixture()
def ctx(tmp_workspace: Path) -> ToolContext:
    return ToolContext(session_id="test", workspace=str(tmp_workspace))


class TestChartingTool:
    def test_bar_chart_produces_png(self, tool: ChartingTool, ctx: ToolContext) -> None:
        result = tool.run(
            {
                "chart_type": "bar",
                "title": "Test Bar Chart",
                "data": {"labels": ["A", "B", "C"], "values": [1, 2, 3]},
                "filename": "test_bar.png",
            },
            ctx,
        )
        assert "test_bar.png" in result
        assert (Path(ctx.workspace) / "test_bar.png").exists()

    def test_line_chart_produces_png(self, tool: ChartingTool, ctx: ToolContext) -> None:
        result = tool.run(
            {
                "chart_type": "line",
                "title": "Test Line",
                "data": {"labels": ["Jan", "Feb"], "values": [10, 20]},
                "filename": "test_line.png",
            },
            ctx,
        )
        assert (Path(ctx.workspace) / "test_line.png").exists()

    def test_pie_chart_produces_png(self, tool: ChartingTool, ctx: ToolContext) -> None:
        result = tool.run(
            {
                "chart_type": "pie",
                "title": "Test Pie",
                "data": {"labels": ["X", "Y"], "values": [30, 70]},
                "filename": "test_pie.png",
            },
            ctx,
        )
        assert (Path(ctx.workspace) / "test_pie.png").exists()

    def test_empty_data_returns_error(self, tool: ChartingTool, ctx: ToolContext) -> None:
        result = tool.run(
            {
                "chart_type": "bar",
                "title": "Empty",
                "data": {"labels": [], "values": []},
                "filename": "empty.png",
            },
            ctx,
        )
        assert "error" in result.lower()

    def test_default_filename(self, tool: ChartingTool, ctx: ToolContext) -> None:
        result = tool.run(
            {
                "chart_type": "bar",
                "title": "Default",
                "data": {"labels": ["A"], "values": [1]},
            },
            ctx,
        )
        assert "chart.png" in result
