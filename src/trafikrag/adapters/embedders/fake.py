"""Test için deterministik sahte embedder (model indirmeden çalışır)."""
import hashlib


class FakeEmbedder:
    def __init__(self, dim: int = 16):
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            out.append([b / 255 for b in h[: self.dim]])
        return out


def build(cfg: dict) -> FakeEmbedder:
    return FakeEmbedder(cfg.get("dim", 16))
