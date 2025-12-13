import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_path)
        except Exception:
            pass


def get_env(name: str, default: str | None = None) -> str | None:
    load_env()
    return os.getenv(name, default)
