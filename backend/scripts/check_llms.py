"""See which LLMs your keys can use, and time each one in JSON mode.
Run from backend/:  python -m scripts.check_llms"""
import time
import httpx
from app.core import config as C
from app.llm import router

SKIP = ("whisper", "guard", "tts", "embed", "moderation", "ocr", "transcribe", "vision", "image", "audio", "live")


def list_models(name, url, key):
    try:
        r = httpx.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=15)
        ids = sorted(m["id"] for m in r.json()["data"])
        ids = [i for i in ids if not any(s in i for s in SKIP)]
        print(f"\n{name} models your key can see:")
        for i in ids:
            print("   ", i)
    except Exception as e:
        print(f"\n{name}: could not list models ({type(e).__name__}: {str(e)[:100]})")


print("Keys found:", {"gemini": bool(C.GEMINI_API_KEY), "groq": bool(C.GROQ_API_KEY), "mistral": bool(C.MISTRAL_API_KEY)})
if C.GROQ_API_KEY:
    list_models("Groq", "https://api.groq.com/openai/v1/models", C.GROQ_API_KEY)
if C.MISTRAL_API_KEY:
    list_models("Mistral", "https://api.mistral.ai/v1/models", C.MISTRAL_API_KEY)

print("\nTiming the models in your current .env settings (JSON mode, like the real app):")
prompt = 'Return ONLY a JSON object: {"city": "Chennai", "code": "MAA"}'
for label, fn in router.chain():
    start = time.time()
    try:
        out = fn(prompt, True, 0)
        print(f"  OK    {label}: {time.time() - start:.1f}s -> {out.strip()[:60]!r}")
    except Exception as e:
        print(f"  FAIL  {label}: {type(e).__name__}: {str(e)[:110]}")