"""Claude API LLM. build(cfg) -> LLM"""
import json
import os

DEFAULT_MODEL = "claude-sonnet-5-5"

class ClaudeLLM:
    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 2000):
        import anthropic # ağır bağımlılık: yalnızca bu adaptör kullanılırken yüklenir
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = model
        self.max_tokens = max_tokens
    def complete(self, prompt: str, *, system: str | None = None, json_schema: dict | None = None) -> str:
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        if json_schema is None:
            response = self.client.messages.create(**kwargs)
            return "".join(b.text for b in response.content if b.type == "text")
        # Şema verilmişse aracı zorunlu kıl: çıktı her zaman şemaya uyan JSON olur
        kwargs["tools"] = [{
            "name": "kaydet",
            "description": "Çıkarılan alanları kaydet.",
            "input_schema": json_schema,
        }]
        kwargs["tool_choice"] = {"type": "tool", "name": "kaydet"}
        response = self.client.messages.create(**kwargs)
        for block in response.content:
            if block.type == "tool_use":
                return json.dumps(block.input, ensure_ascii=False)
        return "{}"
def build(cfg: dict) -> ClaudeLLM:
    return ClaudeLLM(model=cfg.get("model", DEFAULT_MODEL), max_tokens=cfg.get("max_tokens", 2000))