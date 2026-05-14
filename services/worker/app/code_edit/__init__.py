"""Self-modify code workflow — service layer for /code-edit/* endpoints.

Module layout:
- policy.py:    allowlist / blocklist / risk / approval phrases
- git_ops.py:   thin git subprocess wrappers
- patcher.py:   apply / reverse / dry-run unified diffs
- verifier.py:  per-area verification (compileall, docker compose config, …)
- planner.py:   provider-driven diff generation with fallback
- (this file): persistence + high-level service functions used by main.py
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from . import git_ops, patcher, planner, policy, verifier
from .policy import WORKSPACE_ROOT

logger = logging.getLogger(__name__)

# All artifacts live under /app/data/code-edits/<task_id>/
CODE_EDIT_DIR = Path("/app/data/code-edits")
CODE_EDIT_DIR.mkdir(parents=True, exist_ok=True)


# ── Status constants (mirror docs/wiki state machine) ──────────────────────
class EditStatus:
    PATCH_PROPOSED        = "patch_proposed"
    PATCH_APPLIED         = "patch_applied"
    VERIFICATION_PASSED   = "verification_passed"
    VERIFICATION_FAILED   = "verification_failed"
    WAITING_COMMIT_APPROVAL = "waiting_commit_approval"
    COMMITTED             = "committed"
    ROLLED_BACK           = "rolled_back"
    BLOCKED               = "blocked"


@dataclass
class CodeEditTask:
    task_id: str
    instruction: str
    files_to_change: List[str]
    risk_level: int
    status: str
    plan_text: str = ""
    patch_source: str = "none"      # "user_supplied" | "provider" | "none"
    provider_error: str = ""
    verification_overall: str = "UNKNOWN"
    commit_hash: str = ""
    branch: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ── Persistence helpers ───────────────────────────────────────────────────

def task_dir(task_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_\-]", "_", task_id)[:64]
    p = CODE_EDIT_DIR / safe
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_state(task: CodeEditTask) -> None:
    task.updated_at = datetime.now(timezone.utc).isoformat()
    if not task.created_at:
        task.created_at = task.updated_at
    p = task_dir(task.task_id) / "task.json"
    p.write_text(json.dumps(task.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def load_state(task_id: str) -> Optional[CodeEditTask]:
    p = task_dir(task_id) / "task.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return CodeEditTask(**data)
    except Exception as e:
        logger.warning("code_edit: cannot load state for %s: %s", task_id, e)
        return None


# ── Service-level operations called by endpoints ──────────────────────────

async def plan(task_id: str, instruction: str, files_hint: List[str],
               user_patch: Optional[str] = None) -> dict:
    """Stage 1: produce a plan + saved unified diff.

    Auto-generate via provider; if that fails AND `user_patch` is supplied,
    fall back to user-provided diff. Always policy-check before saving.
    """
    files_hint = [f for f in files_hint if f]

    plan_out = planner.PlanOutput("", "", "none", "")

    if user_patch and planner.looks_like_unified_diff(user_patch):
        plan_out = planner.PlanOutput(
            plan_text="User supplied unified diff.",
            unified_diff=user_patch,
            source="user_supplied",
        )
    else:
        # Try provider
        plan_out = await planner.generate_via_provider(instruction, files_hint)
        # Fallback to user patch if provider failed and user supplied one
        if not plan_out.unified_diff and user_patch and planner.looks_like_unified_diff(user_patch):
            plan_out = planner.PlanOutput(
                plan_text=f"Provider failed ({plan_out.provider_error}); using user-supplied diff.",
                unified_diff=user_patch,
                source="user_supplied",
            )

    # If still no diff — record as proposed with empty patch and require user input
    if not plan_out.unified_diff:
        files_from_diff: List[str] = []
        risk = policy.classify_risk(files_hint or [])
        task = CodeEditTask(
            task_id=task_id,
            instruction=instruction,
            files_to_change=files_hint,
            risk_level=risk,
            status=EditStatus.PATCH_PROPOSED,
            plan_text=plan_out.plan_text or "No patch generated.",
            patch_source="none",
            provider_error=plan_out.provider_error,
        )
        save_state(task)
        return {
            "task_id": task_id,
            "status": EditStatus.PATCH_PROPOSED,
            "files_to_change": files_hint,
            "risk_level": risk,
            "patch_path": "",
            "plan_text": task.plan_text,
            "patch_source": "none",
            "provider_error": plan_out.provider_error,
            "message": "No diff yet — supply patch_unified in /code-edit/plan body or fix provider config",
        }

    # Extract real files from the diff & policy-check
    files_in_diff = patcher.extract_files_from_diff(plan_out.unified_diff)
    files_combined = sorted(set(files_in_diff) | set(map(policy.normalize, files_hint)))

    pol = policy.evaluate(files_in_diff or files_combined, plan_out.unified_diff)
    if not pol.allowed:
        task = CodeEditTask(
            task_id=task_id,
            instruction=instruction,
            files_to_change=files_combined,
            risk_level=pol.risk_level,
            status=EditStatus.BLOCKED,
            plan_text=plan_out.plan_text,
            patch_source=plan_out.source,
            provider_error=plan_out.provider_error,
        )
        save_state(task)
        return {
            "task_id": task_id,
            "status": EditStatus.BLOCKED,
            "files_to_change": files_combined,
            "risk_level": pol.risk_level,
            "patch_path": "",
            "plan_text": task.plan_text,
            "patch_source": plan_out.source,
            "blocked_reason": pol.reason,
            "blocked_paths": pol.blocked_paths,
            "out_of_allowlist": pol.out_of_allowlist,
            "secret_hits": pol.secret_hits,
        }

    # Save artifacts
    tdir = task_dir(task_id)
    fwd, _rev = patcher.save_patch_files(tdir, plan_out.unified_diff)
    (tdir / "plan.md").write_text(plan_out.plan_text or "", encoding="utf-8")

    task = CodeEditTask(
        task_id=task_id,
        instruction=instruction,
        files_to_change=files_in_diff or files_combined,
        risk_level=pol.risk_level,
        status=EditStatus.PATCH_PROPOSED,
        plan_text=plan_out.plan_text,
        patch_source=plan_out.source,
        provider_error=plan_out.provider_error,
    )
    save_state(task)

    return {
        "task_id": task_id,
        "status": EditStatus.PATCH_PROPOSED,
        "files_to_change": task.files_to_change,
        "risk_level": pol.risk_level,
        "patch_path": str(fwd),
        "plan_text": task.plan_text,
        "patch_source": plan_out.source,
        "required_apply_phrase": policy.required_approval_phrase(pol.risk_level, "apply"),
        "required_commit_phrase": policy.required_approval_phrase(pol.risk_level, "commit"),
    }


def apply(task_id: str, approval_phrase: str = "") -> dict:
    """Stage 2: apply the saved forward.patch and run verification."""
    if not git_ops.workspace_exists():
        return {
            "status": "error",
            "message": (
                "Workspace not available at /workspace. "
                "Did you mount the project into the worker? See infra/docker/docker-compose.wsl.yml."
            ),
        }

    task = load_state(task_id)
    if not task:
        return {"status": "error", "message": f"task {task_id} not found"}

    tdir = task_dir(task_id)
    forward = patcher.load_patch(tdir, "forward.patch")
    if not forward:
        return {"status": "error", "message": "no forward.patch saved for this task"}

    needed = policy.required_approval_phrase(task.risk_level, "apply")
    if needed and approval_phrase.strip() != needed:
        return {
            "status": EditStatus.BLOCKED,
            "message": f"approval phrase required: {needed}",
            "required_apply_phrase": needed,
        }

    # Re-check working tree (clean except for known artifact paths)
    clean, dirty = git_ops.is_working_tree_clean(allow_artifact_paths=True)
    if not clean:
        return {
            "status": EditStatus.BLOCKED,
            "message": "working tree not clean — refusing apply",
            "dirty_paths": dirty[:10],
        }

    # Dry-run first
    dry = patcher.dry_run(forward)
    if not dry.ok:
        return {
            "status": EditStatus.BLOCKED,
            "message": "patch dry-run failed; refusing apply",
            "stderr": dry.stderr[:400],
        }

    # Apply
    out = patcher.apply(forward)
    if not out.ok:
        task.status = EditStatus.VERIFICATION_FAILED
        save_state(task)
        return {
            "status": EditStatus.VERIFICATION_FAILED,
            "message": "git apply failed",
            "stderr": out.stderr[:400],
        }

    # Verify
    v = verifier.run_verification(task.files_to_change)
    task.verification_overall = v.overall
    task.status = (
        EditStatus.WAITING_COMMIT_APPROVAL if v.overall in ("PASS", "WARNING")
        else EditStatus.VERIFICATION_FAILED
    )
    save_state(task)

    (tdir / "verification.json").write_text(
        json.dumps({
            "overall": v.overall,
            "steps": [s.__dict__ for s in v.steps],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    files_changed = task.files_to_change
    diff_stat = git_ops.diff_stat().stdout

    return {
        "status": task.status,
        "files_changed": files_changed,
        "diff_summary": diff_stat.strip(),
        "verification_status": v.overall,
        "verification_steps": [
            {"name": s.name, "ok": s.ok, "skipped": s.skipped,
             "exit_code": s.exit_code, "skip_reason": s.skip_reason}
            for s in v.steps
        ],
        "required_commit_phrase": policy.required_approval_phrase(task.risk_level, "commit"),
    }


def commit(task_id: str, approval_phrase: str = "", commit_message: str = "") -> dict:
    """Stage 3: stage allowlisted paths and commit. No --no-verify, no force."""
    task = load_state(task_id)
    if not task:
        return {"status": "error", "message": f"task {task_id} not found"}

    if task.status not in (EditStatus.WAITING_COMMIT_APPROVAL,
                           EditStatus.PATCH_APPLIED,
                           EditStatus.VERIFICATION_PASSED):
        return {
            "status": EditStatus.BLOCKED,
            "message": f"task not in commit-ready state (current: {task.status})",
        }

    needed = policy.required_approval_phrase(task.risk_level, "commit")
    if needed and approval_phrase.strip() != needed:
        return {
            "status": EditStatus.BLOCKED,
            "message": f"approval phrase required: {needed}",
            "required_commit_phrase": needed,
        }

    # Re-scan files & staged diff for secrets one more time before commit
    paths = list(task.files_to_change)
    staged_diff = git_ops.diff_for_paths(paths).stdout
    secret_hits = policy.scan_patch_for_secrets(staged_diff)
    if secret_hits:
        return {
            "status": EditStatus.BLOCKED,
            "message": "secret pattern detected in working-tree diff — refusing commit",
            "secret_hits": secret_hits,
        }

    # Stage only allowlisted paths
    stageable = [p for p in paths if not policy.path_in_blocklist(p)]
    if not stageable:
        return {"status": EditStatus.BLOCKED, "message": "no allowlisted paths to commit"}

    rs = git_ops.stage_paths(stageable)
    if not rs.ok:
        return {"status": "error", "message": f"git add failed: {rs.stderr[:200]}"}

    msg = (commit_message or "").strip()
    if not msg:
        first_file = stageable[0] if stageable else "files"
        short = (task.instruction or "")[:60].replace("\n", " ")
        msg = f"feat(self-modify): {short} ({first_file})\n\ntask_id: {task_id}"

    rc = git_ops.commit(msg)
    if not rc.ok:
        return {"status": "error", "message": f"git commit failed: {rc.stderr[:200]}"}

    task.commit_hash = git_ops.head_commit()
    task.branch = git_ops.current_branch()
    task.status = EditStatus.COMMITTED
    save_state(task)

    return {
        "status": EditStatus.COMMITTED,
        "commit_hash": task.commit_hash,
        "branch": task.branch,
        "files_changed": stageable,
    }


def rollback(task_id: str, approval_phrase: str = "") -> dict:
    """Apply reverse.patch to undo a previously applied patch."""
    if approval_phrase.strip() != "ROLLBACK PATCH":
        return {
            "status": EditStatus.BLOCKED,
            "message": "approval phrase required: ROLLBACK PATCH",
        }

    task = load_state(task_id)
    if not task:
        return {"status": "error", "message": f"task {task_id} not found"}

    tdir = task_dir(task_id)
    rev = patcher.load_patch(tdir, "reverse.patch")
    if not rev:
        return {"status": "error", "message": "no reverse.patch available"}

    out = patcher.reverse(rev)
    if not out.ok:
        return {"status": "error", "message": f"reverse apply failed: {out.stderr[:300]}"}

    task.status = EditStatus.ROLLED_BACK
    save_state(task)
    return {
        "status": EditStatus.ROLLED_BACK,
        "files_restored": task.files_to_change,
    }
