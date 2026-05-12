import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, List


class RunnerMode:
    PROMPT_ONLY   = "prompt_only"
    HERMES_MANUAL = "hermes_manual"
    HERMES_HTTP   = "hermes_http"
    SHELL_SAFE    = "shell_safe"


class RunStatus:
    QUEUED                 = "queued"
    PREPARING              = "preparing"
    RUNNING                = "running"
    COMPLETED              = "completed"
    COMPLETED_PROMPT_READY = "completed_prompt_ready"
    WAITING_FOR_HERMES     = "waiting_for_hermes_manual_execution"
    FAILED                 = "failed"
    SKIPPED_DISABLED       = "skipped_disabled"


@dataclass
class RunResult:
    status: str
    prompt_path: Optional[str] = None
    error_message: Optional[str] = None


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
    output_summary: Optional[str] = None
    error_message: Optional[str] = None
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
