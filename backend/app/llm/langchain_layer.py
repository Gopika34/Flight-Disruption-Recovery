
import logging

from collections.abc import Iterator

import httpx

from langchain_core.runnables import (
    RunnableLambda,
    RunnableGenerator,
)

from app.llm.router import (
    complete,
    stream_complete,
)

from app.rag.generation import build_explanation


logger = logging.getLogger(__name__)


# ==================================================
# 1. LANGCHAIN RETRY
# ==================================================

def create_retry_runnable(function):

    runnable = RunnableLambda(function)

    return runnable.with_retry(
        retry_if_exception_type=(
            TimeoutError,
            ConnectionError,
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RemoteProtocolError,
        ),
        wait_exponential_jitter=True,
        stop_after_attempt=3,
        exponential_jitter_params={
            "initial": 1,
            "max": 8,
            "exp_base": 2,
        },
    )


# ==================================================
# 2. MULTI-PROVIDER GENERATION
# ==================================================

def generate_explanation(data):

    logger.info(
        "Starting multi-provider explanation generation"
    )

    # Internally handles:
    # Gemini -> Groq -> Mistral
    # Provider-level retry and fallback.

    return complete(
        prompt=data["prompt"],
        temperature=0.2,
    )


# ==================================================
# 3. APPLICATION-LEVEL FALLBACK
# ==================================================

def fallback_explanation(data):

    logger.warning(
        "All LLM providers failed. "
        "Using deterministic explanation."
    )

    return build_explanation(data["plan"])


def create_explanation_chain():

    primary = RunnableLambda(
        generate_explanation
    )

    fallback = RunnableLambda(
        fallback_explanation
    )

    return primary.with_fallbacks(
        [fallback],
        exceptions_to_handle=(Exception,),
    )


# ==================================================
# 4. MULTI-PROVIDER STREAMING
# ==================================================

def stream_generator(input_iterator: Iterator[dict]):

    for data in input_iterator:

        prompt = data["prompt"]
        fallback = data.get("fallback")

        emitted = False

        try:

            for chunk in stream_complete(
                prompt,
                temperature=0.2,
            ):

                if chunk:
                    emitted = True
                    yield chunk

        except Exception:

            # Never switch to another response after
            # sending partial LLM output.

            if emitted:
                raise

            logger.exception(
                "All streaming providers failed. "
                "Using deterministic fallback."
            )

            if fallback:
                yield fallback
            else:
                raise
            

def stream_response(prompt, fallback=None):

    yield from stream_chain.stream({
        "prompt": prompt,
        "fallback": fallback,
    })