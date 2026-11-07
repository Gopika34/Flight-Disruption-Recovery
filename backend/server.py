
"""
Application server entry point.

Starts the FastAPI application using Uvicorn.
"""

import os
import logging

import uvicorn


def main():

    host = os.getenv("HOST", "0.0.0.0")

    port = int(os.getenv("PORT", "8000"))

    reload_enabled = (
        os.getenv("RELOAD", "false").lower() == "true"
    )

    log_level = os.getenv("LOG_LEVEL", "info").lower()

    logging.basicConfig(
        level=log_level.upper(),
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )

    print(
        f"Starting Flight Disruption Recovery Engine "
        f"on {host}:{port}",
        flush=True,
    )

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload_enabled,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
