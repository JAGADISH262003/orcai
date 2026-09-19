"""Backwards-compatible facade over the provider-agnostic AI layer.

Keeps the historical `app.services.llm` import path working for all callers.
"""

from typing import Any

__all__ = ["chat_json", "llm_available"]


def llm_available() -> bool:
    from app.core.ai import llm_available as _impl

    return _impl()


async def chat_json(
    system: str, user: str, *, temperature: float = 0.1
) -> dict[str, Any] | None:
    from app.core.ai import ai_complete

    return await ai_complete(system, user, temperature=temperature)
