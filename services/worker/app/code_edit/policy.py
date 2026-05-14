"""Policy enforcement for self-modify code workflow.

Single source of truth for:
- which paths are editable (allowlist)
- which paths must never be touched (blocklist)
- which approval phrases are required at each risk level
- secret scanning (block any patch that introduces an API-key-shaped string)
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Iterable, List

# Project root inside the worker container — driven by AICC_WORKSPACE_ROOT env var
WORKSPACE_ROOT = os.getenv("AICC_WORKSPACE_ROOT", "/workspace")

# ── Allowlist (relative to WORKSPACE_ROOT) ─────────────────────────────────
ALLOWLIST_PREFIXES: tuple[str, ...] = (
    "apps/web/pages/",
    "apps/web/components/",
    "apps/web/layouts/",
    "services/worker/app/",
    "services/mobile-gateway/app/",
    "services/rag-api/app/",
    "core/workflows/",
    "core/skills/",
    "docs/wiki/",
    "docs/releases/",
)

# Exact-path allowlist (single files)
ALLOWLIST_EXACT: frozenset[str] = frozenset({
    "infra/docker/docker-compose.wsl.yml",
    "infra/nginx/default.conf",
    ".env.example",
    ".gitignore",
})

# ── Blocklist (absolute deny — wins over allowlist) ────────────────────────
BLOCKLIST_PREFIXES: tuple[str, ...] = (
    "data/",
    "node_modules/",
    ".git/",
    "apps/web/.output/",
    "apps/web/dist/",
    "apps/web/.nuxt/",
)

BLOCKLIST_EXACT: frozenset[str] = frozenset({
    ".env",
    ".env.local",
})

# Filename pattern blocks (anywhere in tree)
BLOCKLIST_SUFFIX_REGEX = re.compile(
    r"(?:^|/)(?:"
    r".*\.key$|"
    r".*\.pem$|"
    r"id_rsa.*$|"
    r"__pycache__/.*|"
    r".*\.pyc$|"
    r"provider-settings\.local\.json$"
    r")"
)

# Secret patterns — reject patch if NEW content (lines starting with '+') matches
_SECRET_REGEXES: tuple[re.Pattern, ...] = (
    re.compile(r"sk-[A-Za-z0-9]{20,}"),                    # OpenAI / sk-style keys
    re.compile(r"Bearer\s+[A-Za-z0-9_\-]{20,}"),           # Bearer tokens (case-sensitive)
    re.compile(r"-----BEGIN\s+(?:RSA\s+|EC\s+|OPENSSH\s+)?PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),                       # AWS access keys
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),                   # GitHub PAT
)


@dataclass
class PolicyResult:
    allowed: bool
    reason: str = ""
    risk_level: int = 1
    blocked_paths: List[str] = field(default_factory=list)
    out_of_allowlist: List[str] = field(default_factory=list)
    secret_hits: List[str] = field(default_factory=list)


def normalize(p: str) -> str:
    """Normalize a relative path: forward slashes, no leading './' or '/'."""
    if not p:
        return ""
    s = p.replace("\\", "/").lstrip("./").lstrip("/")
    # Collapse "../" segments — any remaining ".." after normalization is suspicious
    parts = PurePosixPath(s).parts
    return "/".join(parts)


def path_in_allowlist(rel_path: str) -> bool:
    n = normalize(rel_path)
    if n in ALLOWLIST_EXACT:
        return True
    return any(n.startswith(pref) for pref in ALLOWLIST_PREFIXES)


def path_in_blocklist(rel_path: str) -> bool:
    n = normalize(rel_path)
    if not n:
        return True
    if ".." in n.split("/"):  # path traversal attempt
        return True
    if n in BLOCKLIST_EXACT:
        return True
    if any(n.startswith(pref) for pref in BLOCKLIST_PREFIXES):
        return True
    if BLOCKLIST_SUFFIX_REGEX.search("/" + n):
        return True
    return False


def classify_risk(files: Iterable[str]) -> int:
    """Heuristic risk classification (1..5) based on which areas are touched."""
    risk = 1
    for raw in files:
        n = normalize(raw)
        # Level 5: any blocklist hit elevates to max (will be blocked anyway)
        if path_in_blocklist(n):
            return 5
        # Level 4: infra / .gitignore
        if n in ALLOWLIST_EXACT and n in ("infra/docker/docker-compose.wsl.yml",
                                          "infra/nginx/default.conf",
                                          ".gitignore"):
            risk = max(risk, 4)
        # Level 3: backend code
        elif n.startswith(("services/worker/app/",
                           "services/mobile-gateway/app/",
                           "services/rag-api/app/")):
            risk = max(risk, 3)
        # Level 3: frontend logic files (.vue, .ts, .js) in pages/components
        elif n.startswith(("apps/web/pages/", "apps/web/components/", "apps/web/layouts/")):
            # CSS-only / md-only inside the same dirs stay at level 2
            if n.endswith((".css", ".scss", ".md")):
                risk = max(risk, 2)
            else:
                risk = max(risk, 3)
        # Level 1: docs/.env.example
        elif n.startswith(("docs/", "core/")) or n == ".env.example":
            risk = max(risk, 1)
    return risk


def scan_patch_for_secrets(unified_diff: str) -> List[str]:
    """Return list of secret-match strings found on '+' lines of the diff."""
    hits: List[str] = []
    for line in unified_diff.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for pat in _SECRET_REGEXES:
            m = pat.search(line)
            if m:
                # Don't echo the actual match into logs/reports — just the pattern label
                hits.append(f"{pat.pattern[:30]}…")
                break
    return hits


def required_approval_phrase(risk: int, action: str) -> str:
    """Return the required approval phrase for an action at a given risk level.
    action ∈ {"apply", "commit"}. Returns "" if no approval needed.
    """
    if risk >= 5:
        return "CONFIRM DANGEROUS"
    if action == "apply" and risk >= 3:
        return "APPLY PATCH"
    if action == "commit" and risk >= 3:
        return "COMMIT CHANGES"
    return ""


def evaluate(files: Iterable[str], unified_diff: str = "") -> PolicyResult:
    """Run full policy check over the set of files and the diff content."""
    files_list = [normalize(f) for f in files if f]
    blocked = [f for f in files_list if path_in_blocklist(f)]
    not_allowed = [f for f in files_list
                   if f not in blocked and not path_in_allowlist(f)]

    secret_hits: List[str] = []
    if unified_diff:
        secret_hits = scan_patch_for_secrets(unified_diff)

    if blocked:
        return PolicyResult(
            allowed=False,
            reason=f"blocklist: {', '.join(blocked[:3])}",
            risk_level=5,
            blocked_paths=blocked,
            out_of_allowlist=not_allowed,
            secret_hits=secret_hits,
        )
    if not_allowed:
        return PolicyResult(
            allowed=False,
            reason=f"outside allowlist: {', '.join(not_allowed[:3])}",
            risk_level=classify_risk(files_list),
            blocked_paths=blocked,
            out_of_allowlist=not_allowed,
            secret_hits=secret_hits,
        )
    if secret_hits:
        return PolicyResult(
            allowed=False,
            reason=f"secret pattern detected in patch ({len(secret_hits)} match)",
            risk_level=5,
            blocked_paths=[],
            out_of_allowlist=[],
            secret_hits=secret_hits,
        )

    return PolicyResult(
        allowed=True,
        reason="",
        risk_level=classify_risk(files_list),
        blocked_paths=[],
        out_of_allowlist=[],
        secret_hits=[],
    )
