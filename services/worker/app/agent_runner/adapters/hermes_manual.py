import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..types import AgentRun, RunResult, RunStatus

logger = logging.getLogger(__name__)


def build_hermes_payload(run: AgentRun, prompt: str, prompt_path: Optional[str]) -> dict:
    return {
        "run_id": run.id,
        "job_id": run.job_id,
        "command_id": run.command_id,
        "source": run.source,
        "agent_role": run.agent_role,
        "skills": run.skills,
        "workflow": run.workflow,
        "runner_mode": run.runner_mode,
        "prompt": prompt,
        "prompt_path": prompt_path,
        "rag_results_count": run.rag_results_count,
        "rag_top_path": run.rag_top_path,
        "created_at": run.created_at,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }


async def run(run: AgentRun, prompt: str, artifact_dir: str, push_event=None) -> RunResult:
    try:
        art = Path(artifact_dir)
        art.mkdir(parents=True, exist_ok=True)

        prompt_path = art / f"{run.id}.prompt.md"
        prompt_path.write_text(prompt, encoding="utf-8")

        payload = build_hermes_payload(run, prompt, str(prompt_path))
        payload_path = art / f"{run.id}.hermes-payload.json"
        payload_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info(
            "hermes_manual: payload ready for manual execution at %s", payload_path
        )
        return RunResult(
            status=RunStatus.WAITING_FOR_HERMES,
            prompt_path=str(prompt_path),
        )
    except Exception as e:
        logger.error("hermes_manual: failed: %s", e)
        return RunResult(status=RunStatus.FAILED, error_message=str(e))
