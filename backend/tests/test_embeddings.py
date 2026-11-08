from types import SimpleNamespace

import pytest

from app.rag import embeddings as emb


class FakeClient:
    """Returns one vector per input text; vector[0] encodes the text so order is checkable."""

    def __init__(self, dims=4, fail_times=0, drop=0, wrong_dims=False):
        self.calls, self.fail_times, self.drop, self.dims = [], fail_times, drop, dims
        self.wrong_dims = wrong_dims
        self.models = SimpleNamespace(embed_content=self._embed)

    def _embed(self, model, contents, config):
        self.calls.append(list(contents))
        if self.fail_times:
            self.fail_times -= 1
            raise ConnectionError("temporary")
        n = len(contents) - self.drop
        d = self.dims + (1 if self.wrong_dims else 0)
        return SimpleNamespace(embeddings=[
            SimpleNamespace(values=[float(text)] + [0.0] * (d - 1)) for text in contents[:n]
        ])


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr(emb, "EMBED_DIMS", 4)
    monkeypatch.setattr(emb.time, "sleep", lambda s: None)
    emb.embed_query.cache_clear()
    yield
    emb.embed_query.cache_clear()


def use(monkeypatch, client):
    monkeypatch.setattr(emb, "_get_client", lambda: client)
    return client


def test_batches_and_preserves_order(monkeypatch):
    client = use(monkeypatch, FakeClient())
    texts = [str(i) for i in range(7)]
    vectors = emb.embed_documents(texts, batch_size=3)
    assert [v[0] for v in vectors] == [float(i) for i in range(7)]
    assert [len(c) for c in client.calls] == [3, 3, 1]


def test_retries_then_succeeds(monkeypatch):
    client = use(monkeypatch, FakeClient(fail_times=2))
    assert len(emb.embed_documents(["1", "2"])) == 2
    assert len(client.calls) == 3


def test_gives_up_after_retries(monkeypatch):
    use(monkeypatch, FakeClient(fail_times=99))
    with pytest.raises(emb.EmbeddingError):
        emb.embed_documents(["1"])


def test_count_mismatch_is_an_error(monkeypatch):
    use(monkeypatch, FakeClient(drop=1))
    with pytest.raises(emb.EmbeddingError, match="Expected 3 embeddings"):
        emb.embed_documents(["1", "2", "3"])


def test_wrong_dimensions_is_an_error(monkeypatch):
    use(monkeypatch, FakeClient(wrong_dims=True))
    with pytest.raises(emb.EmbeddingError, match="dimensions"):
        emb.embed_documents(["1"])


def test_missing_key_fails_lazily_not_at_import(monkeypatch):
    monkeypatch.setattr(emb, "GEMINI_API_KEY", None)
    emb._get_client.cache_clear()
    with pytest.raises(emb.EmbeddingError, match="GEMINI_API_KEY"):
        emb.embed_query("hello")
    emb._get_client.cache_clear()
