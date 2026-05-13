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
    Orchestrate an agent run. Never raises — all errors returned as FAILED.
    Returns dict with agent_run_id, status, mode, prompt_path, and optional
    final_report/verification_status/output_summary/report_path when
    hermes_http auto-saves a report.
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

    # Adapter-level push_event: action+message only (task_id is baked in above)
    async def _adapter_push(action: str, message: str = "") -> None:
        await _push(action, message)

    await _push("agent_run_queued", f"AgentRun {run.id} queued (mode={mode})")

    result = None
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

        result = await adapter(run, prompt, AGENT_RUNNER_ARTIFACT_DIR, push_event=_adapter_push)

        run.status = result.status
        run.prompt_path = result.prompt_path or ""
        run.error_message = result.error_message or ""
        run.completed_at = datetime.now(timezone.utc).isoformat()

        update_kwargs: dict = {
            "status": result.status,
            "prompt_path": run.prompt_path,
            "error_message": run.error_message,
            "completed_at": run.completed_at,
        }
        if result.report_path:
            update_kwargs["report_path"] = result.report_path
            update_kwargs["verification_status"] = result.verification_status or "UNKNOWN"
            update_kwargs["output_summary"] = result.output_summary or ""
            update_kwargs["report_saved_at"] = datetime.now(timezone.utc).isoformat()
        if result.fallback_mode:
            update_kwargs["fallback_mode"] = result.fallback_mode
        if result.fallback_reason:
            update_kwargs["fallback_reason"] = result.fallback_reason
        if result.hermes_endpoint:
            update_kwargs["hermes_endpoint"] = result.hermes_endpoint
        if result.hermes_http_status:
            update_kwargs["hermes_http_status"] = result.hermes_http_status
        if result.hermes_response_format:
            update_kwargs["hermes_response_format"] = result.hermes_response_format
        if result.response_received_at:
            update_kwargs["response_received_at"] = result.response_received_at
        update_run(run.id, **update_kwargs)

        # Status-specific push events
        if result.status == RunStatus.FAILED:
            await _push("agent_run_failed", result.error_message or "unknown error")
        elif result.status in (RunStatus.WAITING_FOR_HERMES, RunStatus.HERMES_MANUAL_PENDING):
            await _push("agent_run_waiting_hermes", "รอ Hermes manual execution")
        elif result.status == RunStatus.WAITING_HERMES:
            await _push("agent_run_waiting_hermes", "Submitted to Hermes, waiting for async response")
        elif result.status == RunStatus.HERMES_RESPONSE_UNRECOGNIZED:
            await _push("agent_run_failed", result.error_message or "Hermes response unrecognized")
        elif result.status == RunStatus.COMPLETED_REPORT_SAVED:
            # hermes_report_saved + task_completed_from_hermes already pushed inside hermes_http adapter
            pass
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
        # Populated only when hermes_http auto-saved a report
        "final_report": (result.final_report if result else None),
        "verification_status": (result.verification_status if result else None),
        "output_summary": (result.output_summary if result else None),
        "report_path": (result.report_path if result else None),
        "fallback_mode": (result.fallback_mode if result else None),
        "fallback_reason": (result.fallback_reason if result else None),
        "hermes_endpoint": (result.hermes_endpoint if result else ""),
        "hermes_http_status": (result.hermes_http_status if result else 0),
        "hermes_response_format": (result.hermes_response_format if result else ""),
        "response_received_at": (result.response_received_at if result else None),
    }
