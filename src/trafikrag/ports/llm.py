from typing import Protocol


class LLM(Protocol):
    def complete(self, prompt: str, *, system: str | None = None, json_schema: dict | None = None) -> str: ...
