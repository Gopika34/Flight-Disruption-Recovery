"""
Central LLM router.

Features:
- Gemini, Groq and Mistral support.
- Configurable provider priority.
- Multiple Gemini model fallback.
- Retry with exponential backoff and jitter.
- Provider cooldown after failures.
- Timeout handling.
- JSON response support.
- Output validation.
- Provider status reporting.
"""

import random
import threading
import time

import httpx

from google import genai
from google.genai import types

from app.core import config as C


# --------------------------------------------------
# STATE
# --------------------------------------------------

_down_until = {}
_failure_counts = {}
_last_errors = {}

_state_lock = threading.Lock()
_gemini = None


# --------------------------------------------------
# GEMINI CLIENT
# --------------------------------------------------

def _gemini_client():
    global _gemini

    if _gemini is None:
        _gemini = genai.Client(
            api_key=C.GEMINI_API_KEY,
            http_options=types.HttpOptions(
                timeout=int(C.LLM_TIMEOUT_S * 1000),
                retry_options=types.HttpRetryOptions(
                    attempts=1
                ),
            ),
        )

    return _gemini


# --------------------------------------------------
# PROVIDER CALLS
# --------------------------------------------------

def _call_gemini(model, prompt, json_mode, temperature):

    config = {
        "temperature": temperature,
    }

    if json_mode:
        config["response_mime_type"] = "application/json"

    response = _gemini_client().models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(**config),
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response")

    return response.text


def _call_openai_style(
    url,
    key,
    model,
    prompt,
    json_mode,
    temperature,
):
    """
    Shared implementation for Groq and Mistral.
    Both expose OpenAI-compatible chat completions APIs.
    """

    body = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }

    if json_mode:
        body["response_format"] = {
            "type": "json_object"
        }

    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=C.LLM_TIMEOUT_S,
    )

    response.raise_for_status()

    data = response.json()

    content = data["choices"][0]["message"]["content"]

    if not content or not content.strip():
        raise RuntimeError("Provider returned an empty response")

    return content


def _call_groq(model, prompt, json_mode, temperature):

    return _call_openai_style(
        url="https://api.groq.com/openai/v1/chat/completions",
        key=C.GROQ_API_KEY,
        model=model,
        prompt=prompt,
        json_mode=json_mode,
        temperature=temperature,
    )


def _call_mistral(model, prompt, json_mode, temperature):

    return _call_openai_style(
        url="https://api.mistral.ai/v1/chat/completions",
        key=C.MISTRAL_API_KEY,
        model=model,
        prompt=prompt,
        json_mode=json_mode,
        temperature=temperature,
    )


# --------------------------------------------------
# PROVIDER CHAIN
# --------------------------------------------------

def chain():
    """
    Returns providers in configured priority order.

    Each entry:
        (provider_label, callable)
    """

    links = []

    for name in C.LLM_ORDER:

        name = name.strip().lower()

        if name == "gemini" and C.GEMINI_API_KEY:

            for model in C.GEMINI_MODELS:

                links.append(
                    (
                        f"gemini:{model}",
                        lambda p, j, t, m=model:
                            _call_gemini(m, p, j, t),
                    )
                )

        elif name == "groq" and C.GROQ_API_KEY:

            links.append(
                (
                    f"groq:{C.GROQ_MODEL}",
                    lambda p, j, t:
                        _call_groq(C.GROQ_MODEL, p, j, t),
                )
            )

        elif name == "mistral" and C.MISTRAL_API_KEY:

            links.append(
                (
                    f"mistral:{C.MISTRAL_MODEL}",
                    lambda p, j, t:
                        _call_mistral(C.MISTRAL_MODEL, p, j, t),
                )
            )

    return links


# --------------------------------------------------
# FAILURE CLASSIFICATION
# --------------------------------------------------

def _status_code(error):

    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code

    return (
        getattr(error, "code", None)
        or getattr(error, "status_code", None)
    )


def _retryable(error):

    if isinstance(error, (httpx.TimeoutException,
                          httpx.NetworkError,
                          httpx.RemoteProtocolError)):
        return True

    status = _status_code(error)

    if status is None:
        # SDK/network errors without an HTTP status.
        return True

    # Rate limits, temporary failures and request timeouts.
    return status in (408, 409, 425, 429) or status >= 500


# --------------------------------------------------
# RETRY
# --------------------------------------------------

def _call_with_retry(label, fn, prompt, json_mode, temperature):

    attempts = max(1, C.LLM_RETRIES)

    for attempt in range(attempts):

        try:

            started = time.monotonic()

            result = fn(
                prompt,
                json_mode,
                temperature,
            )

            elapsed = time.monotonic() - started

            print(
                f"[llm] {label} responded in {elapsed:.2f}s",
                flush=True,
            )

            return result

        except Exception as error:

            retryable = _retryable(error)

            print(
                f"[llm] {label} attempt "
                f"{attempt + 1}/{attempts} failed: "
                f"{type(error).__name__}: {str(error)[:180]}",
                flush=True,
            )

            if not retryable:
                raise

            if attempt + 1 >= attempts:
                raise

            delay = (
                C.LLM_RETRY_BASE_S * (2 ** attempt)
                + random.uniform(0, 0.5)
            )

            time.sleep(delay)


# --------------------------------------------------
# PROVIDER HEALTH
# --------------------------------------------------

def _mark_failed(label, error):

    with _state_lock:

        _down_until[label] = (
            time.monotonic() + C.LLM_COOLDOWN_S
        )

        _failure_counts[label] = (
            _failure_counts.get(label, 0) + 1
        )

        _last_errors[label] = (
            f"{type(error).__name__}: {str(error)[:180]}"
        )


def _mark_success(label):

    with _state_lock:

        _down_until.pop(label, None)
        _failure_counts[label] = 0
        _last_errors.pop(label, None)


def provider_status():

    now = time.monotonic()

    configured = chain()

    results = []

    for label, _ in configured:

        remaining = max(
            0,
            int(_down_until.get(label, 0) - now),
        )

        entry = {
            "provider": label,
            "available_for_attempt": remaining == 0,
        }
        if detailed:
            entry.update({
                "cooldown_remaining_seconds": remaining,
                "consecutive_failures": _failure_counts.get(label, 0),
                "last_error": _last_errors.get(label),
            })
        results.append(entry)

    out = {"providers": results, "provider_count": len(results)}
    if detailed:
        out["configured_order"] = C.LLM_ORDER
    return out


# --------------------------------------------------
# MAIN ROUTER
# --------------------------------------------------

def complete(
    prompt,
    json_mode=False,
    temperature=0.0,
    validate=None,
):
    """
    Send a prompt through the configured LLM providers.

    1. Try healthy providers first.
    2. Retry transient failures.
    3. Move to the next provider.
    4. Validate the response.
    5. Return the first valid result.
    """

    links = chain()

    if not links:
        raise RuntimeError(
            "No LLM providers configured. "
            "Check GEMINI_API_KEY, GROQ_API_KEY and MISTRAL_API_KEY."
        )

    now = time.monotonic()

    healthy = []
    cooling = []

    for link in links:

        label = link[0]

        if _down_until.get(label, 0) <= now:
            healthy.append(link)
        else:
            cooling.append(link)

    # Try healthy providers first.
    # Cooling providers are still eligible as a last resort.
    ordered = healthy + cooling

    errors = []

    for label, fn in ordered:

        try:

            raw = _call_with_retry(
                label,
                fn,
                prompt,
                json_mode,
                temperature,
            )

            # A response that cannot be validated is not usable.
            try:

                result = (
                    validate(raw)
                    if validate
                    else raw.strip()
                )

                if result is None:
                    raise ValueError("Validator returned None")

            except Exception as error:

                errors.append(
                    f"{label}: invalid output: {str(error)[:120]}"
                )

                print(
                    f"[llm] {label} returned invalid output; "
                    "moving to next provider",
                    flush=True,
                )

                continue

            _mark_success(label)

            print(
                f"[llm] SUCCESS: {label}",
                flush=True,
            )

            return result

        except Exception as error:

            _mark_failed(label, error)

            errors.append(
                f"{label}: {type(error).__name__}: "
                f"{str(error)[:120]}"
            )

            print(
                f"[llm] PROVIDER FAILED: {label}; "
                "moving to next provider",
                flush=True,
            )

    raise RuntimeError(
        "All LLM providers failed. "
        + " | ".join(errors)
    )
    

# --------------------------------------------------
# STREAMING PROVIDER CALLS
# --------------------------------------------------

def _stream_gemini(model, prompt, temperature):
    response_stream = _gemini_client().models.generate_content_stream(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature
        ),
    )

    for response in response_stream:
        if response.text:
            yield response.text


def _stream_openai_style(url, key, model, prompt, temperature):
    """
    Streaming chat completions for Groq and Mistral.
    """

    body = {
        "model": model,
        "temperature": temperature,
        "stream": True,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }

    with httpx.stream(
        "POST",
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=C.LLM_TIMEOUT_S,
    ) as response:

        response.raise_for_status()

        for line in response.iter_lines():

            if not line or not line.startswith("data:"):
                continue

            data = line[5:].strip()

            if data == "[DONE]":
                break

            try:
                payload = __import__("json").loads(data)
                content = (
                    payload["choices"][0]["delta"].get("content")
                )

                if content:
                    yield content

            except (ValueError, KeyError, IndexError, TypeError):
                continue


def _stream_provider_chain(prompt, temperature):
    """
    Return streaming providers in configured priority order.
    """

    providers = []

    for name in C.LLM_ORDER:

        name = name.strip().lower()

        if name == "gemini" and C.GEMINI_API_KEY:

            for model in C.GEMINI_MODELS:
                providers.append((
                    f"gemini:{model}",
                    lambda m=model: _stream_gemini(
                        m, prompt, temperature
                    ),
                ))

        elif name == "groq" and C.GROQ_API_KEY:

            providers.append((
                f"groq:{C.GROQ_MODEL}",
                lambda: _stream_openai_style(
                    "https://api.groq.com/openai/v1/chat/completions",
                    C.GROQ_API_KEY,
                    C.GROQ_MODEL,
                    prompt,
                    temperature,
                ),
            ))

        elif name == "mistral" and C.MISTRAL_API_KEY:

            providers.append((
                f"mistral:{C.MISTRAL_MODEL}",
                lambda: _stream_openai_style(
                    "https://api.mistral.ai/v1/chat/completions",
                    C.MISTRAL_API_KEY,
                    C.MISTRAL_MODEL,
                    prompt,
                    temperature,
                ),
            ))

    return providers


def stream_complete(prompt, temperature=0.2):
    """
    Stream the first usable provider's response.

    Retries and provider fallback are allowed before
    the first text chunk is sent.

    After text has been sent, a provider failure raises
    an error instead of mixing two different answers.
    """

    providers = _stream_provider_chain(prompt, temperature)

    if not providers:
        raise RuntimeError("No LLM streaming providers configured.")

    now = time.monotonic()

    healthy = []
    cooling = []

    for label, factory in providers:

        if _down_until.get(label, 0) <= now:
            healthy.append((label, factory))
        else:
            cooling.append((label, factory))

    errors = []

    for label, factory in healthy + cooling:

        attempts = max(1, C.LLM_RETRIES)

        for attempt in range(attempts):

            iterator = None
            first_chunk = None

            try:
                print(f"[llm-stream] Trying {label}", flush=True)

                iterator = iter(factory())

                # Get the first chunk before committing to this provider.
                first_chunk = next(iterator, None)

                if not first_chunk:
                    raise RuntimeError(
                        "Provider returned an empty stream."
                    )

                _mark_success(label)

                print(
                    f"[llm-stream] SUCCESS: {label}",
                    flush=True,
                )

                yield first_chunk

                # Once output has started, never switch providers.
                for chunk in iterator:
                    if chunk:
                        yield chunk

                return

            except Exception as error:

                if first_chunk:
                    _mark_failed(label, error)

                    raise RuntimeError(
                        f"{label} failed after streaming began. "
                        "The partial answer was not replaced."
                    ) from error

                retryable = _retryable(error)

                print(
                    f"[llm-stream] {label} attempt "
                    f"{attempt + 1}/{attempts} failed: "
                    f"{type(error).__name__}: {str(error)[:180]}",
                    flush=True,
                )

                if not retryable or attempt + 1 >= attempts:
                    _mark_failed(label, error)
                    errors.append(f"{label}: {str(error)[:150]}")
                    break

                delay = (
                    C.LLM_RETRY_BASE_S * (2 ** attempt)
                    + random.uniform(0, 0.5)
                )

                time.sleep(delay)

    raise RuntimeError(
        "All LLM streaming providers failed. "
        + " | ".join(errors)
    )
