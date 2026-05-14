"""Thin, defensive wrappers around git/patch subprocess calls.

All commands run with cwd=WORKSPACE_ROOT. Never use destructive flags
(--no-verify, --hard, --force) unless caller passes `confirm_dangerous=True`.
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .policy import WORKSPACE_ROOT

logger = logging.getLogger(__name__)


@dataclass
class CmdResult:
    cmd: List[str]
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


def _run(args: List[str], *, cwd: str = WORKSPACE_ROOT, timeout: float = 30.0,
         stdin: Optional[str] = None) -> CmdResult:
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=stdin,
            check=False,
        )
        return CmdResult(args, proc.returncode, proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired:
        return CmdResult(args, 124, "", f"timeout after {timeout}s")
    except FileNotFoundError as e:
        return CmdResult(args, 127, "", f"command not found: {e}")
    except Exception as e:  # safety net
        return CmdResult(args, 1, "", f"{type(e).__name__}: {e}")


def workspace_exists() -> bool:
    return Path(WORKSPACE_ROOT).is_dir() and Path(WORKSPACE_ROOT, ".git").exists()


# ── Read-only helpers ─────────────────────────────────────────────────────

def status_porcelain() -> CmdResult:
    return _run(["git", "status", "--porcelain"])


def is_working_tree_clean(allow_artifact_paths: bool = True) -> tuple[bool, List[str]]:
    """Returns (clean, dirty_paths). If allow_artifact_paths is True,
    paths under known build/runtime artifact dirs do not count as dirty.
    """
    r = status_porcelain()
    if not r.ok:
        return False, [f"git status failed: {r.stderr}"]
    dirty: List[str] = []
    artifact_prefixes = ("data/", "apps/web/.output/", "apps/web/dist/", "apps/web/.nuxt/")
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        # Porcelain format: "XY path"; path may contain "->" for renames
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.strip('"')
        if allow_artifact_paths and any(path.startswith(p) for p in artifact_prefixes):
            continue
        dirty.append(path)
    return (len(dirty) == 0), dirty


def diff_stat() -> CmdResult:
    return _run(["git", "diff", "--stat"])


def diff_check() -> CmdResult:
    """git diff --check detects whitespace / conflict markers."""
    return _run(["git", "diff", "--check"])


def current_branch() -> str:
    r = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return r.stdout.strip() if r.ok else "(unknown)"


def head_commit() -> str:
    r = _run(["git", "rev-parse", "--short", "HEAD"])
    return r.stdout.strip() if r.ok else ""


# ── Patch ops ─────────────────────────────────────────────────────────────

def apply_patch(unified_diff: str, *, reverse: bool = False, check_only: bool = False) -> CmdResult:
    """Apply a unified diff using git apply. Set check_only=True to dry-run.
    We use `git apply` (not `patch`) for stricter validation and reverse support.
    """
    args = ["git", "apply", "--whitespace=nowarn"]
    if check_only:
        args.append("--check")
    if reverse:
        args.append("--reverse")
    args.append("-")  # read patch from stdin
    return _run(args, stdin=unified_diff, timeout=60.0)


def generate_reverse_patch(unified_diff: str) -> str:
    """Build a reverse diff by swapping ---/+++ headers and +/- on hunk lines.

    Not perfect for binary patches; for v1 we only support text patches.
    """
    out: list[str] = []
    in_hunk = False
    for line in unified_diff.splitlines(keepends=False):
        if line.startswith("--- "):
            out.append("+++ " + line[4:]); continue
        if line.startswith("+++ "):
            out.append("--- " + line[4:]); continue
        if line.startswith("@@"):
            in_hunk = True
            out.append(line); continue
        if not in_hunk:
            out.append(line); continue
        if line.startswith("+"):
            out.append("-" + line[1:])
        elif line.startswith("-"):
            out.append("+" + line[1:])
        else:
            out.append(line)
    return "\n".join(out) + ("\n" if unified_diff.endswith("\n") else "")


# ── Commit ops ────────────────────────────────────────────────────────────

def stage_paths(paths: List[str]) -> CmdResult:
    if not paths:
        return CmdResult(["git", "add"], 0, "", "no paths")
    return _run(["git", "add", "--"] + paths, timeout=30.0)


def commit(message: str, *, allow_empty: bool = False) -> CmdResult:
    args = ["git", "commit", "-m", message]
    if allow_empty:
        args.append("--allow-empty")
    return _run(args, timeout=30.0)


def diff_for_paths(paths: List[str], *, staged: bool = False) -> CmdResult:
    args = ["git", "diff"]
    if staged:
        args.append("--cached")
    args.append("--")
    args.extend(paths)
    return _run(args, timeout=15.0)
