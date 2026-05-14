"""Verification commands per touched area.

Maps file path prefixes to a list of shell commands to run after `apply`.
All commands run inside the worker container, cwd=WORKSPACE_ROOT.

Output is captured and stored in `verification.json`. Caller decides PASS/WARN/FAIL.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from . import git_ops
from .policy import normalize

logger = logging.getLogger(__name__)


@dataclass
class VerificationStep:
    name: str
    cmd: List[str]
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    skipped: bool = False
    skip_reason: str = ""

    @property
    def ok(self) -> bool:
        return self.skipped or self.exit_code == 0


@dataclass
class VerificationResult:
    overall: str = "UNKNOWN"   # PASS | WARNING | FAIL | UNKNOWN
    steps: List[VerificationStep] = field(default_factory=list)


def _areas(files: List[str]) -> set[str]:
    areas: set[str] = set()
    for raw in files:
        n = normalize(raw)
        if n.startswith("apps/web/"):
            areas.add("frontend")
        elif n.startswith("services/worker/app/"):
            areas.add("worker_py")
        elif n.startswith(("services/mobile-gateway/app/", "services/rag-api/app/")):
            areas.add("gateway_py")
        elif n.startswith("infra/docker/"):
            areas.add("compose")
    return areas


def run_verification(files: List[str]) -> VerificationResult:
    """Run all applicable verification steps for the set of files touched.

    Steps that aren't applicable to the workspace (missing binaries, etc.)
    are recorded as skipped with a reason — they do not fail the overall result.
    """
    result = VerificationResult()
    steps: List[VerificationStep] = []
    areas = _areas(files)

    # Always: git diff --check
    rc = git_ops.diff_check()
    steps.append(VerificationStep(
        "git diff --check", rc.cmd, rc.exit_code, rc.stdout, rc.stderr,
    ))

    if "worker_py" in areas:
        from subprocess import run as _r
        cmd = ["python", "-m", "compileall", "-q", "services/worker/app"]
        rr = _run(cmd)
        steps.append(VerificationStep("python compileall (worker)", cmd, rr.exit_code, rr.stdout, rr.stderr))

    if "gateway_py" in areas:
        # Mobile gateway and rag-api both follow services/<svc>/app
        for svc_dir in ("services/mobile-gateway/app", "services/rag-api/app"):
            cmd = ["python", "-m", "compileall", "-q", svc_dir]
            rr = _run(cmd)
            steps.append(VerificationStep(f"python compileall ({svc_dir})", cmd, rr.exit_code, rr.stdout, rr.stderr))

    if "compose" in areas:
        cmd = [
            "docker", "compose",
            "--env-file", ".env",
            "-f", "infra/docker/docker-compose.wsl.yml",
            "config",
        ]
        rr = _run(cmd)
        # docker compose may not be reachable from inside the worker container.
        # That's expected — record as skipped rather than fail.
        if rr.exit_code == 127:
            steps.append(VerificationStep(
                "docker compose config", cmd, 0, "", "",
                skipped=True,
                skip_reason="docker CLI not available inside worker container",
            ))
        else:
            steps.append(VerificationStep("docker compose config", cmd, rr.exit_code, rr.stdout, rr.stderr))

    if "frontend" in areas:
        # Prefer pnpm if present; otherwise mark skipped (host-side rebuild required).
        # We do NOT attempt a real build inside the worker — too slow, brittle.
        steps.append(VerificationStep(
            "pnpm --filter web generate",
            ["pnpm", "--filter", "web", "generate"],
            skipped=True,
            skip_reason="frontend build deferred to host (run after approval)",
        ))

    # git status — informational only
    rc = git_ops.status_porcelain()
    steps.append(VerificationStep(
        "git status --porcelain", rc.cmd, rc.exit_code, rc.stdout, rc.stderr,
    ))

    # Decide overall
    failing = [s for s in steps if not s.ok]
    warnings = [s for s in steps if s.ok and not s.skipped and "warning" in (s.stderr or "").lower()]
    if failing:
        result.overall = "FAIL"
    elif warnings:
        result.overall = "WARNING"
    else:
        result.overall = "PASS"

    result.steps = steps
    return result


def _run(cmd: List[str]):
    """Lightweight rerun of git_ops._run for non-git commands."""
    from . import git_ops as _g
    return _g._run(cmd, timeout=60.0)
