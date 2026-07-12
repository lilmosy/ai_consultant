"""Thin Anthropic wrapper: JSON-returning calls with retries and light logging."""
from __future__ import annotations
import json
import re
import time
from typing import Any

import anthropic

from . import config

_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY missing — set it in .env")
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def _extract_json(text: str) -> Any:
    """Best-effort parse of a JSON value from model text (handles ```json fences / prose)."""
    text = text.strip()
    # strip code fences
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    # grab the outermost {...} or [...]
    for open_c, close_c in (("{", "}"), ("[", "]")):
        i, j = text.find(open_c), text.rfind(close_c)
        if i != -1 and j != -1 and j > i:
            try:
                return json.loads(text[i : j + 1])
            except Exception:
                continue
    # salvage: a truncated {"claims":[{...},{...},{trunc...  -> keep complete objects
    salvaged = _salvage_object_array(text)
    if salvaged is not None:
        return salvaged
    raise ValueError(f"Could not parse JSON from model output:\n{text[:500]}")


def _salvage_object_array(text: str) -> Any:
    """Recover complete `{...}` items from a truncated array (e.g. max_tokens cutoff).

    Returns {"claims": [...]} of the fully-closed objects, or None if nothing recoverable.
    """
    start = text.find("[")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    items: list[Any] = []
    obj_start = -1
    for k in range(start + 1, len(text)):
        ch = text[k]
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            if depth == 0:
                obj_start = k
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and obj_start != -1:
                frag = text[obj_start : k + 1]
                try:
                    items.append(json.loads(frag))
                except Exception:
                    pass
                obj_start = -1
    return {"claims": items} if items else None


def call_json(
    system: str,
    user: str,
    *,
    model: str | None = None,
    max_tokens: int = 4000,
    retries: int = 4,
) -> Any:
    """Call Claude and return parsed JSON. Retries on API and parse errors.

    Note: temperature is intentionally omitted — newer flagship models (opus-4-8)
    reject the `temperature` param (400 deprecated)."""
    model = model or config.MODEL_FAST
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = client().messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            return _extract_json(text)
        except (anthropic.APIStatusError, anthropic.APIConnectionError, anthropic.RateLimitError) as e:
            last_err = e
            time.sleep(min(2 ** attempt * 2, 30))
        except ValueError as e:  # parse failure — nudge with a stricter retry
            last_err = e
            user = user + "\n\n반드시 유효한 JSON만 출력하세요. 코드펜스/설명 없이 JSON 값 하나만."
            time.sleep(1)
    raise RuntimeError(f"call_json failed after {retries} tries: {last_err}")
