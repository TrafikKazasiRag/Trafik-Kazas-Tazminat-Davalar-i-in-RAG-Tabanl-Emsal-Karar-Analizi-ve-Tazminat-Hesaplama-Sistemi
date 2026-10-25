"""BAAI/bge-m3 embedder. build(cfg) -> Embedder"""

import math
from typing import Any, Protocol


class _BgeM3Model(Protocol):
    def encode(
        self,
        sentences: list[str],
        *,
        batch_size: int,
        max_length: int,
        return_dense: bool,
        return_sparse: bool,
        return_colbert_vecs: bool,
    ) -> dict[str, Any]: ...


def _load_model(model_name: str, use_fp16: bool) -> _BgeM3Model:
    from FlagEmbedding import BGEM3FlagModel

    return BGEM3FlagModel(model_name, use_fp16=use_fp16)


class BgeM3Embedder:
    def __init__(
        self,
        model: _BgeM3Model,
        batch_size: int = 32,
        max_length: int = 8192,
    ) -> None:
        self._model = model
        self._batch_size = batch_size
        self._max_length = max_length

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        output = self._model.encode(
            texts,
            batch_size=self._batch_size,
            max_length=self._max_length,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        if "dense_vecs" not in output:
            raise RuntimeError("BGE-M3 model output does not contain dense_vecs")

        vectors = output["dense_vecs"]
        if len(vectors) != len(texts):
            raise RuntimeError(
                f"BGE-M3 returned {len(vectors)} vectors for {len(texts)} texts"
            )

        normalized: list[list[float]] = []
        for vector in vectors:
            values = [float(value) for value in vector]
            if len(values) != 1024:
                raise RuntimeError(
                    f"BGE-M3 returned a {len(values)}-dimensional vector; expected 1024"
                )

            norm = math.sqrt(sum(value * value for value in values))
            normalized.append([value / norm for value in values] if norm else values)

        return normalized


def build(cfg: dict) -> BgeM3Embedder:
    model_name = cfg.get("model_name", "BAAI/bge-m3")
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("embedder.model_name must be a non-empty string")

    use_fp16 = cfg.get("use_fp16", False)
    if not isinstance(use_fp16, bool):
        raise ValueError("embedder.use_fp16 must be a boolean")

    batch_size = cfg.get("batch_size", 32)
    if (
        not isinstance(batch_size, int)
        or isinstance(batch_size, bool)
        or batch_size <= 0
    ):
        raise ValueError("embedder.batch_size must be a positive integer")

    max_length = cfg.get("max_length", 8192)
    if (
        not isinstance(max_length, int)
        or isinstance(max_length, bool)
        or max_length <= 0
    ):
        raise ValueError("embedder.max_length must be a positive integer")

    return BgeM3Embedder(
        model=_load_model(model_name.strip(), use_fp16),
        batch_size=batch_size,
        max_length=max_length,
    )
