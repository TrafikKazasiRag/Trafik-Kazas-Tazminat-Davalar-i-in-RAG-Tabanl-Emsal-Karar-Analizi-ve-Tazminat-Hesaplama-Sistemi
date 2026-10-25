import math

from trafikrag.adapters.embedders import bge_m3


class FakeBgeM3Model:
    def __init__(self) -> None:
        self.encode_calls: list[tuple[list[str], dict]] = []
        self.vectors = {
            "trafik kazası tazminat": [3.0, 4.0] + [0.0] * 1022,
            "trafik kazası yaralanma": [3.0, 3.0] + [0.0] * 1022,
            "hava durumu güneş": [0.0, 0.0, 5.0] + [0.0] * 1021,
        }

    def encode(
        self,
        sentences: list[str],
        *,
        batch_size: int,
        max_length: int,
        return_dense: bool,
        return_sparse: bool,
        return_colbert_vecs: bool,
    ) -> dict:
        self.encode_calls.append(
            (
                sentences,
                {
                    "batch_size": batch_size,
                    "max_length": max_length,
                    "return_dense": return_dense,
                    "return_sparse": return_sparse,
                    "return_colbert_vecs": return_colbert_vecs,
                },
            )
        )
        return {"dense_vecs": [self.vectors[text] for text in sentences]}


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def test_bge_m3_builds_once_and_returns_normalized_dense_vectors(monkeypatch):
    model = FakeBgeM3Model()
    load_calls = []

    def load_model(model_name: str, use_fp16: bool) -> FakeBgeM3Model:
        load_calls.append((model_name, use_fp16))
        return model

    monkeypatch.setattr(bge_m3, "_load_model", load_model)

    embedder = bge_m3.build({"batch_size": 2, "max_length": 512})
    texts = [
        "trafik kazası tazminat",
        "trafik kazası yaralanma",
        "hava durumu güneş",
    ]
    vectors = embedder.embed(texts)
    repeated = embedder.embed([texts[0]])

    assert load_calls == [("BAAI/bge-m3", False)]
    assert model.encode_calls[0][1] == {
        "batch_size": 2,
        "max_length": 512,
        "return_dense": True,
        "return_sparse": False,
        "return_colbert_vecs": False,
    }
    assert len(vectors) == len(texts)
    assert all(len(vector) == 1024 for vector in vectors)
    assert all(
        math.isclose(sum(value * value for value in vector), 1.0)
        for vector in vectors
    )
    assert vectors[0] == repeated[0]
    assert _cosine_similarity(vectors[0], vectors[1]) > _cosine_similarity(
        vectors[0], vectors[2]
    )
