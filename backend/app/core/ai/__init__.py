"""Provider-agnostic AI facade.

Selects the configured provider (Gemini preferred, OpenAI-compatible fallback)
and exposes a single completion entry point. When no provider is configured the
callers fall back to deterministic logic, so the platform works fully offline.

Priority (AI_PROVIDER):
  auto    -> gemini if GEMINI_API_KEY set, else openai if OPENAI_API_KEY set
  gemini  -> gemini only
  openai  -> openai only
  none    -> no provider (deterministic only)
"""

import logging
from functools import lru_cache
from typing import Any

from app.core.ai.providers.base import AIProvider
from app.core.ai.providers.gemini import GeminiProvider
from app.core.ai.providers.openai_compat import OpenAICompatProvider
from app.core.config import get_settings

logger = logging.getLogger("orcai.ai")
settings = get_settings()


@lru_cache(maxsize=1)
def get_provider() -> AIProvider | None:
    mode = settings.AI_PROVIDER.lower().strip()
    priority: list[str] = []
    if mode in ("auto", "gemini"):
        priority.append("gemini")
    if mode in ("auto", "openai"):
        priority.append("openai")

    for name in priority:
        if name == "gemini" and settings.GEMINI_API_KEY:
            logger.info("AI provider: gemini (%s)", settings.GEMINI_MODEL)
            return GeminiProvider(
                settings.GEMINI_API_KEY,
                settings.GEMINI_MODEL,
                timeout_ms=int(settings.AI_TIMEOUT_SECONDS * 1000),
            )
        if name == "openai" and settings.OPENAI_API_KEY:
            logger.info("AI provider: openai-compatible (%s)", settings.LLM_MODEL)
            return OpenAICompatProvider(
                settings.OPENAI_API_KEY,
                settings.OPENAI_BASE_URL,
                settings.LLM_MODEL,
                timeout_s=settings.AI_TIMEOUT_SECONDS,
            )
    logger.info("AI provider: none (deterministic fallback)")
    return None


def llm_available() -> bool:
    return get_provider() is not None


async def ai_complete(
    system: str,
    user: str,
    *,
    temperature: float = 0.1,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return a parsed JSON object from the provider, or None if unavailable/failed."""
    provider = get_provider()
    if provider is None:
        return None
    try:
        return await provider.complete(system, user, temperature=temperature, schema=schema)
    except Exception as exc:  # noqa: BLE001 - provider failure must not break the request
        logger.warning("AI provider %s failed: %s", provider.name, exc)
        return None
