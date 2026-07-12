"""Central config: loads .env from the repo root (or the monorepo root) and exposes keys/models."""
from __future__ import annotations
import os
from pathlib import Path


def _load_env() -> None:
    """Load the first .env found walking up from this file. No-op if python-dotenv missing."""
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        cand = parent / ".env"
        if cand.exists():
            load_dotenv(cand, override=False)
    # also honor a plain .env in CWD
    if Path(".env").exists():
        load_dotenv(".env", override=False)


_load_env()

DART_API_KEY = os.getenv("DART_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Naver: prefer explicit ID/SECRET; fall back to the single NAVER_API_KEY as the client id.
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID") or os.getenv("NAVER_API_KEY", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

# Model routing. High-volume extraction/verification -> fast model; synthesis/critique -> flagship.
MODEL_FAST = os.getenv("AIC_MODEL_FAST", "claude-sonnet-5")
MODEL_SMART = os.getenv("AIC_MODEL_SMART", "claude-opus-4-8")

# Cost/latency guardrails for the demo
MAX_NEWS_ITEMS = int(os.getenv("AIC_MAX_NEWS", "30"))
MAX_DOC_CHARS = int(os.getenv("AIC_MAX_DOC_CHARS", "60000"))


def naver_ready() -> bool:
    return bool(NAVER_CLIENT_ID and NAVER_CLIENT_SECRET)


def require_dart() -> str:
    if not DART_API_KEY:
        raise RuntimeError("DART_API_KEY missing — set it in .env")
    return DART_API_KEY
