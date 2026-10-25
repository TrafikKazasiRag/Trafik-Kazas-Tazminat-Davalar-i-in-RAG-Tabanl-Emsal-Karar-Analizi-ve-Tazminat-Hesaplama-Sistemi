"""Yerel model LLM (Ollama). build(cfg) -> LLM"""
import requests

DEFAULT_MODEL = "qwen3:8b"
DEFAULT_URL = "http://localhost:11434"


class LocalLLM:
    def __init__(self, model: str = DEFAULT_MODEL, url: str = DEFAULT_URL, timeout: int = 600):
        self.model = model
        self.url = url
        self.timeout = timeout

    def complete(self, prompt: str, *, system: str | None = None, json_schema: dict | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_ctx": 16384},
        }
        if json_schema is not None:
            payload["format"] = json_schema  # Ollama çıktıyı şemaya zorlar
        response = requests.post(f"{self.url}/api/chat", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()["message"]["content"]


def build(cfg: dict) -> LocalLLM:
    return LocalLLM(model=cfg.get("model", DEFAULT_MODEL), url=cfg.get("url", DEFAULT_URL))