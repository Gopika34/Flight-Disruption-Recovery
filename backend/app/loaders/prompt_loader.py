from app.core.config import PROMPT_DIR

def load_prompt(filename):
    path = PROMPT_DIR / filename

    if not path.is_file():
        raise FileNotFoundError(
            f"Prompt file not found: {path}"
        )

    return path.read_text(encoding="utf-8")