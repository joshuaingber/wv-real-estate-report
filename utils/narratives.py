"""
Narrative text generation and source citations.
Template-based descriptive sentences — no LLM calls.
"""
from __future__ import annotations

from utils.formatting import fmt_currency, fmt_signed_pct


def source_citation(name: str, url: str, frequency: str) -> str:
    """Return a source citation string for st.caption()."""
    return f"Source: [{name}]({url}) — {frequency}"


def format_name_list(names: list[str]) -> str:
    """Join 1, 2, or 3+ names with correct comma/conjunction usage."""
    if len(names) == 0:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def narrate_home_value(
    county_name: str,
    latest_value: float | None,
    yoy_pct: float | None,
) -> str:
    """One-sentence description of a county's latest home value and YoY change."""
    if latest_value is None or str(latest_value) == "nan":
        return f"Home-value data for {county_name} County is not currently published."
    if yoy_pct is None or str(yoy_pct) == "nan":
        return (
            f"The typical home in {county_name} County is valued at "
            f"{fmt_currency(latest_value)}."
        )
    direction = "up" if yoy_pct >= 0 else "down"
    return (
        f"The typical home in {county_name} County is valued at "
        f"{fmt_currency(latest_value)}, {direction} {fmt_signed_pct(yoy_pct)} "
        f"over the past year."
    )
