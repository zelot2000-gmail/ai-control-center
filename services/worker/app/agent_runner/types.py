import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, List


def normalize_verification_status(v: Optional[str]) -> str:
    """Normalize verification_status to uppercase canonical form.
    Returns '' if v is empty/None (meaning 'not set by user').
    Hermes responses use _normalize_vstat() in hermes_http.py which returns UNKNOWN for empty.
    """
    if not v:
        return ""
    v_lower = v.lower().strip()
    if v_lower in ("pass", "passed", "ok", "success", "successful"):
        return "PASS"
    if v_lower in ("warning", "warn"):
        return "WARNING"
    if v_lower in ("fail", "failed", "error", "failed_check"):
        return "FAIL"
    if v_lower == "unknown":
        return "UNKNOWN"
    return "UNKNOWN"


class RunnerMode:
    PROMPT_ONLY   = "prompt_only"
    HERMES_MANUAL = "hermes_manual"
    HERMES_HTTP   = "hermes_http"
    SHELL_SAFE    = "shell_safe"


class RunStatus:
    QUEUED                      = "queued"
    PREPARING                   = "preparing"
    RUNNING                     = "running"
    COMPLETED                   = "completed"
    COMPLETED_PROMPT_READY      = "completed_prompt_ready"
    COMPLETED_REPORT_SAVED      = "completed_report_saved"
    WAITING_FOR_HERMES          = "waiting_for_hermes_manual_execution"
    WAITING_HERMES              = "waiting_hermes"
    HERMES_MANUAL_PENDING       = "hermes_manual_pending"
    HERMES_RESPONSE_UNRECOGNIZED = "hermes_response_unrecognized"
    FAILED                      = "failed"
    SKIPPED_DISABLED            = "skipped_disabled"


@dataclass
class RunResult:
    status: str
    prompt_path: Optional[str] = None
    error_message: Optional[str] = None
    report_path: Optional[str] = None
    final_report: Optional[str] = None
    output_summary: Optional[str] = None
    verification_status: Optional[str] = None
    fallback_mode: Optional[str] = None
    fallback_reason: Optional[str] = None
    hermes_endpoint: str = ""
    hermes_http_status: int = 0
    hermes_response_format: str = ""
    response_received_at: Optional[str] = None
    hermes_provider: str = ""
    hermes_request_format: str = ""


@dataclass
class AgentRun:
    id: str
    job_id: str
    source: str
    agent_role: str
    runner_mode: str
    status: str
    skills: List[str]
    workflow: str
    input_text: str
    rag_results_count: int = 0
    rag_top_path: str = ""
    command_id: Optional[str] = None
    prompt_path: Optional[str] = None
    artifact_dir: str = ""
    report_path: str = ""
    report_saved_at: Optional[str] = None
    verification_status: str = ""
    output_summary: Optional[str] = None
    error_message: Optional[str] = None
    fallback_mode: str = ""
    fallback_reason: str = ""
    hermes_endpoint: str = ""
    hermes_http_status: int = 0
    hermes_response_format: str = ""
    response_received_at: Optional[str] = None
    hermes_provider: str = ""
    hermes_request_format: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def new(
        cls,
        job_id: str,
        task: dict,
        runner_mode: str,
        rag_results: Optional[List[dict]] = None,
    ) -> "AgentRun":
        agents = task.get("agents", [])
        agent_role = agents[0] if agents else "manager"
        rag = rag_results or []
        return cls(
            id=str(uuid.uuid4()),
            job_id=job_id,
            command_id=task.get("task_id"),
            source=task.get("source", "unknown"),
            agent_role=agent_role,
            runner_mode=runner_mode,
            status=RunStatus.QUEUED,
            skills=list(task.get("skills", [])),
            workflow=str(task.get("execution", {}).get("selected_workflow") or ""),
            input_text=(
                task.get("inputs", {}).get("optimized_text")
                or task.get("inputs", {}).get("text", "")
            ),
            rag_results_count=len(rag),
            rag_top_path=rag[0].get("path", "") if rag else "",
        )
