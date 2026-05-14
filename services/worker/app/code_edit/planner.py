"""Planner — turn natural-language instruction into a unified diff.

Strategy (v1):
1. If caller passes `patch_unified`, accept it as-is (skip provider).
2. Otherwise, call the configured provider (load_effective_provider_config)
   with a structured prompt asking for a unified diff.
3. Validate that the returned text looks like a unified diff; otherwise
   return an empty patch and let the caller decide (fall back to user input).

NEVER fabricates file paths — the prompt instructs the model to only modify
files the caller explicitly named, and ALL output is policy-checked downstream.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import httpx

from ..agent_runner.config import load_effective_provider_config
from .policy import WORKSPACE_ROOT, path_in_blocklist

logger = logging.getLogger(__name__)


@dataclass
class PlanOutput:
    plan_text: str
    unified_diff: str
    source: str            # "user_supplied" | "provider" | "none"
    provider_error: str = ""


_DIFF_SNIFF = re.compile(r"(?m)^(?:---\s.+\n\+\+\+\s.+\n)|^diff --git ")


def looks_like_unified_diff(text: str) -> bool:
    if not text:
        return False
    return bool(_DIFF_SNIFF.search(text))


def _safe_read_file_excerpt(rel_path: str, max_bytes: int = 8000) -> str:
    """Read a small excerpt of an allowlisted file to include as context.
    Hard-stops at max_bytes to keep prompt size bounded.
    """
    if path_in_blocklist(rel_path):
        return ""
    p = Path(WORKSPACE_ROOT) / rel_path
    if not p.is_file():
        return ""
    try:
        data = p.read_bytes()[:max_bytes]
        return data.decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("planner: cannot read %s: %s", rel_path, e)
        return ""


def _build_system_prompt() -> str:
    return (
        "You are the code-edit planner for AI Control Center. "
        "Your job is to produce a MINIMAL unified diff that implements the user's instruction. "
        "STRICT RULES:\n"
        "1. Output ONLY a valid unified diff in `diff --git` format, no prose, no fences.\n"
        "2. Modify only files the user listed under FILES. Never invent new file paths.\n"
        "3. Never include secrets, API keys, or tokens.\n"
        "4. Keep the diff small and focused — no unrelated reformatting.\n"
        "5. Preserve original indentation and line endings.\n"
    )


def _build_user_prompt(instruction: str, files: List[str]) -> str:
    parts = [f"INSTRUCTION:\n{instruction}\n", "FILES:"]
    if not files:
        parts.append("(none specified — refuse if you cannot infer a single safe file)")
    else:
        for f in files:
            excerpt = _safe_read_file_excerpt(f)
            parts.append(f"\n=== FILE: {f} ===")
            if excerpt:
                parts.append(excerpt)
            else:
                parts.append("(empty or unreadable)")
    parts.append(
        "\nReturn the unified diff now. Do not add markdown fences. "
        "Start with `diff --git ` or with `--- a/<path>` headers."
    )
    return "\n".join(parts)


async def generate_via_provider(instruction: str, files: List[str]) -> PlanOutput:
    """Call the active provider to produce a unified diff. Returns empty diff on any failure."""
    cfg = load_effective_provider_config()
    api_url = cfg.get("hermes_api_url") or ""
    api_key = cfg.get("hermes_api_key") or ""
    model = cfg.get("hermes_model") or ""
    req_fmt = cfg.get("hermes_request_format") or "openai_compatible"
    timeout = float(cfg.get("hermes_timeout_seconds") or 120)

    if not api_url or req_fmt != "openai_compatible":
        return PlanOutput(
            plan_text="(provider not configured for openai_compatible diff generation)",
            unified_diff="",
            source="none",
            provider_error="provider not openai_compatible or api_url missing",
        )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user",   "content": _build_user_prompt(instruction, files)},
        ],
    }
    # Omit temperature by default (some reasoning models reject non-default)
    if cfg.get("hermes_temperature") is not None:
        payload["temperature"] = cfg["hermes_temperature"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    logger.info(
        "code-edit planner: POST provider model=%s api_key_set=%s files=%d",
        model, bool(api_key), len(files),
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(api_url, json=payload, headers=headers)
    except Exception as e:
        return PlanOutput("", "", "none", f"provider connection error: {type(e).__name__}: {e}")

    if resp.status_code != 200:
        body = (resp.text or "")[:200]
        return PlanOutput("", "", "none", f"provider HTTP {resp.status_code}: {body}")

    try:
        data = resp.json()
    except Exception:
        return PlanOutput("", "", "none", "provider returned non-JSON")

    content = ""
    choices = data.get("choices") or []
    if isinstance(choices, list) and choices:
        msg = (choices[0] or {}).get("message") or {}
        if isinstance(msg, dict):
            content = msg.get("content") or ""

    # Strip markdown code fences if present
    content = _strip_fences(content)

    if not looks_like_unified_diff(content):
        return PlanOutput(
            plan_text=f"Provider returned non-diff output ({len(content)} chars).",
            unified_diff="",
            source="none",
            provider_error="response did not look like a unified diff",
        )

    return PlanOutput(
        plan_text=f"Generated via provider (model={model}, {len(content)} chars).",
        unified_diff=content,
        source="provider",
    )


def _strip_fences(text: str) -> str:
    """Remove triple-backtick fences wrapping the diff, if any."""
    if not text:
        return text
    s = text.strip()
    if s.startswith("```"):
        # Remove first fence line
        nl = s.find("\n")
        if nl != -1:
            s = s[nl + 1:]
        # Remove trailing fence
        if s.endswith("```"):
            s = s[:-3].rstrip()
    return s
