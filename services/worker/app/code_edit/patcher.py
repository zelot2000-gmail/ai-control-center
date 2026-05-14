"""Patch lifecycle helpers.

Wraps git_ops for the code-edit endpoints. Owns the logic of:
- parsing files_to_change out of a unified diff (defensively)
- saving forward.patch / reverse.patch artifacts
- dry-run validating a patch before apply
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from . import git_ops
from .policy import normalize

logger = logging.getLogger(__name__)

_FILE_HEADER_RE = re.compile(r"^\+\+\+ (?:b/)?([^\t\n]+)")
_OLD_FILE_HEADER_RE = re.compile(r"^--- (?:a/)?([^\t\n]+)")


def extract_files_from_diff(unified_diff: str) -> List[str]:
    """Best-effort list of touched files. Uses '+++ b/path' lines; falls back to '--- a/path'.

    Returns normalized relative paths. Ignores `/dev/null` markers (new/delete sentinels).
    """
    seen: dict[str, bool] = {}
    for line in unified_diff.splitlines():
        m = _FILE_HEADER_RE.match(line)
        if m:
            p = m.group(1).strip()
            if p and p != "/dev/null":
                seen[normalize(p)] = True
            continue
        m2 = _OLD_FILE_HEADER_RE.match(line)
        if m2:
            p = m2.group(1).strip()
            if p and p != "/dev/null" and normalize(p) not in seen:
                # only add the old path if no corresponding new path showed up later
                seen.setdefault(normalize(p), True)
    return list(seen.keys())


@dataclass
class PatchOutcome:
    ok: bool
    stage: str            # "dry_run" | "apply" | "reverse"
    exit_code: int
    stdout: str
    stderr: str


def dry_run(unified_diff: str) -> PatchOutcome:
    r = git_ops.apply_patch(unified_diff, check_only=True)
    return PatchOutcome(r.ok, "dry_run", r.exit_code, r.stdout, r.stderr)


def apply(unified_diff: str) -> PatchOutcome:
    r = git_ops.apply_patch(unified_diff)
    return PatchOutcome(r.ok, "apply", r.exit_code, r.stdout, r.stderr)


def reverse(unified_diff: str) -> PatchOutcome:
    """Apply the patch in reverse — used by rollback."""
    r = git_ops.apply_patch(unified_diff, reverse=True)
    return PatchOutcome(r.ok, "reverse", r.exit_code, r.stdout, r.stderr)


def save_patch_files(task_dir: Path, forward_diff: str) -> Tuple[Path, Path]:
    """Save forward.patch and a synthesized reverse.patch into task_dir.
    Returns (forward_path, reverse_path).
    """
    task_dir.mkdir(parents=True, exist_ok=True)
    fwd = task_dir / "forward.patch"
    rev = task_dir / "reverse.patch"
    fwd.write_text(forward_diff, encoding="utf-8")
    rev.write_text(git_ops.generate_reverse_patch(forward_diff), encoding="utf-8")
    return fwd, rev


def load_patch(task_dir: Path, name: str = "forward.patch") -> str:
    p = task_dir / name
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")
