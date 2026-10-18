"""Test için sahte LLM: API anahtarı gerektirmez."""


class FakeLLM:
    def __init__(self, response: str = "{}"):
        self.response = response

    def complete(self, prompt: str, *, system: str | None = None, json_schema: dict | None = None) -> str:
        return self.response


def build(cfg: dict) -> FakeLLM:
    return FakeLLM(cfg.get("response", "{}"))
