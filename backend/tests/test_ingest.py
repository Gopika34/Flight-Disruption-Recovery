import pytest

from scripts import ingest_policies as ing


class FakeCol:
    def __init__(self, docs):
        self.docs = docs

    def find(self, query, projection):
        return iter(self.docs)

    def count_documents(self, q):
        return 0


def chunks(n=3):
    return [{"chunk_id": f"c{i}", "content_hash": f"h{i}"} for i in range(n)]


def stored(n=3, dims=4, hash_fmt="h{}"):
    return [{"chunk_id": f"c{i}", "content_hash": hash_fmt.format(i), "embedding": [0.0] * dims}
            for i in range(n)]


def test_real_chunk_file_loads_and_validates():
    assert len(ing.load_chunks()) > 0


def test_fewer_embeddings_than_chunks_is_fatal_not_silently_truncated(monkeypatch):
    # the old zip() loop would have stored only the first 2 chunks without complaint
    monkeypatch.setattr(ing, "embed_documents", lambda inputs: [[0.0] * ing.EMBED_DIMS] * 2)
    data = [{"chunk_id": f"c{i}", "clause_id": "1", "section_title": "S", "text": "t"} for i in range(3)]
    with pytest.raises(SystemExit):
        ing.embed_all(data)


def test_wrong_dimension_embedding_is_fatal(monkeypatch):
    monkeypatch.setattr(ing, "embed_documents", lambda inputs: [[0.0] * 3] * len(inputs))
    data = [{"chunk_id": "c0", "clause_id": "1", "section_title": "S", "text": "t"}]
    with pytest.raises(SystemExit):
        ing.embed_all(data)


def test_verify_passes_when_everything_matches(monkeypatch):
    monkeypatch.setattr(ing, "EMBED_DIMS", 4)
    ing.verify_store(FakeCol(stored()), chunks())


def test_verify_detects_missing_chunk(monkeypatch):
    monkeypatch.setattr(ing, "EMBED_DIMS", 4)
    with pytest.raises(SystemExit):
        ing.verify_store(FakeCol(stored(2)), chunks(3))


def test_verify_detects_hash_mismatch(monkeypatch):
    monkeypatch.setattr(ing, "EMBED_DIMS", 4)
    with pytest.raises(SystemExit):
        ing.verify_store(FakeCol(stored(hash_fmt="DIFFERENT{}")), chunks())


def test_verify_detects_wrong_stored_dimensions(monkeypatch):
    monkeypatch.setattr(ing, "EMBED_DIMS", 4)
    with pytest.raises(SystemExit):
        ing.verify_store(FakeCol(stored(dims=3)), chunks())


def test_dry_run_writes_nothing(monkeypatch):
    monkeypatch.setattr(ing, "embed_documents", lambda inputs: [[0.0] * ing.EMBED_DIMS] * len(inputs))

    def no_mongo(*a, **k):
        raise AssertionError("dry run must not connect to MongoDB")
    monkeypatch.setattr(ing, "MongoClient", no_mongo)
    ing.main(["--dry-run"])
