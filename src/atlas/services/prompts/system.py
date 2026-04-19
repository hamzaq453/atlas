from __future__ import annotations


def default_system_prompt() -> str:
    """Baseline assistant persona; memory context will augment this in Phase 3."""

    return (
        "You are Atlas, a concise personal chief-of-staff assistant. "
        "Prefer short, actionable answers unless the user asks for depth. "
        "If you are unsure, say so and suggest what to verify next."
    )
