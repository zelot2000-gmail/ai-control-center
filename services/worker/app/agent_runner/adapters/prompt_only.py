import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from ..types import AgentRun, RunResult, RunStatus

logger = logging.getLogger(__name__)


async def run(run: AgentRun, prompt: str, artifact_dir: str, push_event=None) -> RunResult:
    try:
        art = Path(artifact_dir)
        art.mkdir(parents=True, exist_ok=True)

        prompt_path = art / f"{run.id}.prompt.md"
        prompt_path.write_text(prompt, encoding="utf-8")

        meta_path = art / f"{run.id}.meta.json"
        meta_path.write_text(
            json.dumps(
                {
                    "run_id": run.id,
                    "job_id": run.job_id,
                    "command_id": run.command_id,
                    "agent_role": run.agent_role,
                    "runner_mode": run.runner_mode,
                    "created_at": run.created_at,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        logger.info("prompt_only: saved prompt to %s", prompt_path)
        return RunResult(
            status=RunStatus.COMPLETED_PROMPT_READY,
            prompt_path=str(prompt_path),
        )
    except Exception as e:
        logger.error("prompt_only: failed to save prompt: %s", e)
        return RunResult(status=RunStatus.FAILED, error_message=str(e))
