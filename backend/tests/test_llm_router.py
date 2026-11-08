import os
os.environ.setdefault("GEMINI_API_KEY", "dummy")
import pytest
from app.llm import router
from app.rag import generation


@pytest.fixture(autouse=True)
def reset():
    router._down_until.clear()


def fake_chain(monkeypatch, *links):
    monkeypatch.setattr(router, "chain", lambda: list(links))


def boom(*a):
    raise RuntimeError("429 quota")


def test_falls_through_to_next_provider(monkeypatch):
    fake_chain(monkeypatch, ("a", boom), ("b", lambda p, j, t: "hello "))
    assert router.complete("hi") == "hello"


def test_failed_provider_is_skipped_next_time(monkeypatch):
    calls = []
    def a(*x):
        calls.append(1); raise RuntimeError("slow")
    fake_chain(monkeypatch, ("a", a), ("b", lambda p, j, t: "ok"))
    router.complete("1")
    after_first = len(calls)                    # includes the retry attempts on the first request
    router.complete("2")
    assert len(calls) == after_first            # second request skipped the cooling provider


def test_bad_json_moves_on_without_cooldown(monkeypatch):
    fake_chain(monkeypatch, ("a", lambda p, j, t: "not json"), ("b", lambda p, j, t: '{"x": 1}'))
    assert router.complete("hi", json_mode=True, validate=generation._json_from) == {"x": 1}
    assert "a" not in router._down_until


def test_all_cooling_providers_are_still_tried(monkeypatch):
    state = {"up": False}
    def a(*x):
        if not state["up"]:
            raise RuntimeError("down")
        return "back"
    fake_chain(monkeypatch, ("a", a))
    with pytest.raises(RuntimeError):
        router.complete("1")
    state["up"] = True
    assert router.complete("2") == "back"


def test_all_fail_gives_clear_error(monkeypatch):
    fake_chain(monkeypatch, ("a", boom), ("b", boom))
    with pytest.raises(RuntimeError, match="All LLM providers failed"):
        router.complete("hi")


def test_extract_facts_merges_and_filters(monkeypatch):
    monkeypatch.setattr(generation, "complete",
                        lambda *a, **k: {"type": "cancellation", "notice_hours": 3, "junk": 1, "reason": None})
    out = generation.extract_facts("x", {"origin": "MAA"})
    assert out == {"origin": "MAA", "type": "cancellation", "notice_hours": 3}


def test_chain_only_includes_providers_with_keys(monkeypatch):
    monkeypatch.setattr(router.C, "GEMINI_API_KEY", None)
    monkeypatch.setattr(router.C, "GROQ_API_KEY", "k")
    monkeypatch.setattr(router.C, "MISTRAL_API_KEY", None)
    labels = [l for l, _ in router.chain()]
    assert labels == [f"groq:{router.C.GROQ_MODEL}"]