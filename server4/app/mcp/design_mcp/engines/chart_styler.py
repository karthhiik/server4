"""
Chart styler — applies theme colors and styles to chart data.
"""

from typing import Optional

from app.mcp.design_mcp.engines.color_engine import ColorEngine


class ChartStyler:
    """Applies theme-aware styling to chart data for rendering."""

    def style_chart(self, chart_data: dict, theme_colors: dict) -> dict:
        """Apply theme colors and styling to chart data."""
        chart_type = chart_data.get("chart_type", "bar")
        chart_colors = theme_colors.get("chart_colors", [
            "#2563eb", "#7c3aed", "#059669", "#d97706", "#dc2626", "#0891b2"
        ])

        styled = dict(chart_data)
        styled["style"] = self._get_chart_style(chart_type, chart_colors, theme_colors)
        styled["colors"] = chart_colors

        # Apply colors to datasets
        datasets = styled.get("datasets", [])
        for i, ds in enumerate(datasets):
            ds["color"] = chart_colors[i % len(chart_colors)]
            if chart_type in ("pie", "donut"):
                # Each data point gets its own color
                ds["colors"] = [chart_colors[j % len(chart_colors)] for j in range(len(ds.get("values", [])))]

        return styled

    def _get_chart_style(self, chart_type: str, colors: list[str], theme: dict) -> dict:
        """Get chart-type-specific style settings."""
        text_color = theme.get("text_primary", "#333333")
        grid_color = ColorEngine.lighten(text_color, 60) if text_color.startswith("#") else "#e5e7eb"

        base_style = {
            "font_family": "Inter, sans-serif",
            "title_font_size": 16,
            "label_font_size": 11,
            "legend_font_size": 10,
            "text_color": text_color,
            "grid_color": grid_color,
            "background": "transparent",
        }

        type_specific = {
            "bar": {"bar_width": 0.7, "border_radius": 4, "show_grid": True},
            "line": {"line_width": 2.5, "point_radius": 4, "fill": False, "tension": 0.3},
            "pie": {"inner_radius": 0, "padding": 2, "show_labels": True},
            "donut": {"inner_radius": 0.55, "padding": 2, "show_labels": True},
            "area": {"line_width": 2, "fill_opacity": 0.15, "tension": 0.4},
        }

        return {**base_style, **type_specific.get(chart_type, type_specific["bar"])}

    def get_pptx_chart_config(self, chart_data: dict, theme_colors: dict) -> dict:
        """Get configuration optimized for python-pptx native chart rendering."""
        chart_type = chart_data.get("chart_type", "bar")

        # Map our chart types to python-pptx chart types
        pptx_type_map = {
            "bar": "COLUMN_CLUSTERED",
            "line": "LINE_MARKERS",
            "pie": "PIE",
            "donut": "DOUGHNUT",
            "area": "AREA",
        }

        return {
            "pptx_chart_type": pptx_type_map.get(chart_type, "COLUMN_CLUSTERED"),
            "chart_colors": theme_colors.get("chart_colors", []),
            "title": chart_data.get("title", ""),
            "labels": chart_data.get("labels", []),
            "datasets": chart_data.get("datasets", []),
            "has_legend": len(chart_data.get("datasets", [])) > 1,
            "source_text": chart_data.get("source_attribution", ""),
        }
