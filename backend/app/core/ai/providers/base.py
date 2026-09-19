from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """A large-language-model provider. Implementations return a parsed JSON object
    or None if the model is unavailable or the response cannot be parsed."""

    name: str = "base"

    @abstractmethod
    async def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.1,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None: ...
