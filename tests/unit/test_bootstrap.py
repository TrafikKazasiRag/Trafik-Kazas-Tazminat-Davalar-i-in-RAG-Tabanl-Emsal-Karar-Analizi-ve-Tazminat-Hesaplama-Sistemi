from trafikrag.adapters.embedders.fake import FakeEmbedder


def test_fake_embedder_is_deterministic():
    e = FakeEmbedder()
    assert e.embed(["a"]) == e.embed(["a"])
