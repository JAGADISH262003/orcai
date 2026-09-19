"""Google Gemini provider built on the official google-genai SDK."""

import json
import re
from typing import Any

from google import genai
from google.genai import types

from app.core.ai.providers.base import AIProvider

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_ms: int = 60000) -> None:
        self.model = model
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout_ms),
        )

    async def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.1,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        config: dict[str, Any] = {
            "response_mime_type": "application/json",
            "temperature": temperature,
        }
        if schema:
            config["response_schema"] = schema

        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                **config,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            return None
        cleaned = _FENCE_RE.sub("", text).strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
