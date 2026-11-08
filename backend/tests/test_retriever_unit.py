import pytest
from pymongo.errors import PyMongoError

from app.rag import retriever as r


class FakeCol:
    def __init__(self, hits=None, clauses=None, fail=False):
        self.hits, self.clauses, self.fail = hits or [], clauses or {}, fail

    def aggregate(self, pipeline):
        if self.fail:
            raise PyMongoError("boom: secret-host")
        return iter(self.hits)

    def find_one(self, query, projection):
        if self.fail:
            raise PyMongoError("boom: secret-host")
        return self.clauses.get(query["clause_id"])


@pytest.fixture
def setup(monkeypatch):
    def _setup(col, index="ready"):
        monkeypatch.setattr(r, "embed_query", lambda q: [0.1])
        monkeypatch.setattr(r, "_collection", lambda: col)
        monkeypatch.setattr(r, "vector_index_status", lambda: index)
    return _setup


@pytest.mark.parametrize("k", [0, 21, -1, True, "4", 2.5])
def test_k_is_validated(k):
    with pytest.raises(ValueError):
        r.search_policy("cancelled", k)


@pytest.mark.parametrize("m", [0, 51, True, "8"])
def test_max_total_is_validated(m):
    with pytest.raises(ValueError):
        r.search_with_related("cancelled", 4, m)


def test_no_results_is_an_empty_list_not_an_error(setup):
    setup(FakeCol(hits=[]))
    assert r.search_policy("anything") == []


def test_database_failure_is_distinguishable(setup):
    setup(FakeCol(fail=True))
    with pytest.raises(r.RetrievalUnavailable, match="database unavailable"):
        r.search_policy("anything")


def test_missing_index_gives_a_clear_error(setup):
    setup(FakeCol(fail=True), index="missing")
    with pytest.raises(r.RetrievalUnavailable, match="index is missing"):
        r.search_policy("anything")


def test_embedding_failure_is_retrieval_unavailable(setup, monkeypatch):
    setup(FakeCol())
    from app.rag.embeddings import EmbeddingError

    def boom(q):
        raise EmbeddingError("x")
    monkeypatch.setattr(r, "embed_query", boom)
    with pytest.raises(r.RetrievalUnavailable):
        r.search_policy("anything")


def test_related_expansion_keeps_source_and_score(setup):
    hit = {"clause_id": "3.3.1", "section_title": "Cancellation of Flight", "text": "x", "score": 0.91}
    related = {"clause_id": "3.3.2", "section_title": "Cancellation of Flight", "text": "y"}
    setup(FakeCol(hits=[hit], clauses={"3.3.2": related}))
    out = r.search_with_related("flight cancelled")
    by_id = {c["clause_id"]: c for c in out}
    assert by_id["3.3.1"]["retrieved_by"] == "vector" and by_id["3.3.1"]["score"] == 0.91
    assert by_id["3.3.2"]["retrieved_by"] == "related" and by_id["3.3.2"]["score"] is None


def test_get_clause_distinguishes_missing_from_failure(setup):
    setup(FakeCol())
    assert r.get_clause("9.9.9") is None
    setup(FakeCol(fail=True))
    with pytest.raises(r.RetrievalUnavailable):
        r.get_clause("3.3.1")


def test_unconfigured_mongo_is_reported_not_crashed(monkeypatch):
    monkeypatch.setattr(r, "MONGO_URI", None)
    r._get_client.cache_clear()
    assert r.db_available() is False
    assert r.vector_index_status() == "unavailable"
    r._get_client.cache_clear()
