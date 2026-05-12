import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, List, Optional

from .adapters import hermes_http, hermes_manual, prompt_only
from .config import AGENT_RUNNER_ARTIFACT_DIR, AGENT_RUNNER_MODE
from .prompt_builder import build_agent_prompt
from .storage import save_run, update_run
from .types import AgentRun, RunnerMode, RunStatus

logger = logging.getLogger(__name__)

PushEventFn = Callable[..., Awaitable[None]]


def _pick_adapter(mode: str):
    if mode == RunnerMode.HERMES_HTTP:
        return hermes_http.run
    if mode == RunnerMode.HERMES_MANUAL:
        return hermes_manual.run
    return prompt_only.run


async def run_agent(
    task: dict,
    rag_results: Optional[List[dict]],
    push_event: PushEventFn,
) -> dict:
    """
    Orchestrate an agent run for the given task.
    Returns a dict with run_id, status, mode, prompt_path, error_message.
    Never raises — all errors are caught and returned as FAILED status.
    """
    mode = AGENT_RUNNER_MODE
    run = AgentRun.new(
        job_id=task.get("job_id", ""),
        task=task,
        runner_mode=mode,
        rag_results=rag_results,
    )
    run.status = RunStatus.QUEUED
    save_run(run)

    task_id = task.get("task_id", run.job_id)

    async def _push(action: str, message: str = "", **kw):
        try:
            await push_event(
                task_id,
                event_agent="agent-runner",
                event_action=action,
                event_message=message,
                **kw,
            )
        except Exception as exc:
            logger.warning("run_agent: push_event failed: %s", exc)

    await _push("agent_run_queued", f"AgentRun {run.id} queued (mode={mode})")

    try:
        run.status = RunStatus.PREPARING
        update_run(run.id, status=RunStatus.PREPARING)
        await _push("agent_run_preparing", "กำลังสร้าง prompt...")

        prompt = build_agent_prompt(
            run_id=run.id,
            job_id=run.job_id,
            source=run.source,
            command_id=run.command_id,
            agent_role=run.agent_role,
            skills=run.skills,
            input_text=run.input_text,
            workflow=run.workflow,
            rag_results=rag_results,
        )

        await _push("agent_run_prompt_built", "Prompt พร้อมแล้ว")

        adapter = _pick_adapter(mode)

        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc).isoformat()
        update_run(run.id, status=RunStatus.RUNNING, started_at=run.started_at)
        await _push("agent_run_started", f"เริ่มรัน adapter={mode}")

        result = await adapter(run, prompt, AGENT_RUNNER_ARTIFACT_DIR)

        run.status = result.status
        run.prompt_path = result.prompt_path or ""
        run.error_message = result.error_message or ""
        run.completed_at = datetime.now(timezone.utc).isoformat()
        update_run(
            run.id,
            status=result.status,
            prompt_path=run.prompt_path,
            error_message=run.error_message,
            completed_at=run.completed_at,
        )

        if result.status == RunStatus.FAILED:
            await _push(
                "agent_run_failed",
                result.error_message or "unknown error",
            )
        elif result.status == RunStatus.WAITING_FOR_HERMES:
            await _push(
                "agent_run_waiting_hermes",
                "รอ Hermes manual execution",
            )
        else:
            await _push("agent_run_completed", f"สำเร็จ status={result.status}")

    except Exception as exc:
        logger.exception("run_agent: unexpected error for run %s: %s", run.id, exc)
        run.status = RunStatus.FAILED
        run.error_message = str(exc)
        run.completed_at = datetime.now(timezone.utc).isoformat()
        update_run(
            run.id,
            status=RunStatus.FAILED,
            error_message=run.error_message,
            completed_at=run.completed_at,
        )
        await _push("agent_run_failed", str(exc))

    return {
        "agent_run_id": run.id,
        "agent_run_status": run.status,
        "agent_run_mode": run.runner_mode,
        "agent_prompt_path": run.prompt_path,
        "agent_error": run.error_message,
    }
