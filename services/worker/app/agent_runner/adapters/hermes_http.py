import logging
from pathlib import Path

import httpx

from ..config import HERMES_API_KEY, HERMES_API_URL, HERMES_TIMEOUT_MS
from ..types import AgentRun, RunResult, RunStatus
from . import hermes_manual

logger = logging.getLogger(__name__)


async def run(run: AgentRun, prompt: str, artifact_dir: str) -> RunResult:
    if not HERMES_API_URL:
        logger.warning(
            "hermes_http: HERMES_API_URL not configured, falling back to hermes_manual"
        )
        return await hermes_manual.run(run, prompt, artifact_dir)

    art = Path(artifact_dir)
    art.mkdir(parents=True, exist_ok=True)

    prompt_path = art / f"{run.id}.prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    payload = hermes_manual.build_hermes_payload(run, prompt, str(prompt_path))

    headers = {"Content-Type": "application/json"}
    if HERMES_API_KEY:
        headers["Authorization"] = f"Bearer {HERMES_API_KEY}"

    timeout = HERMES_TIMEOUT_MS / 1000.0

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{HERMES_API_URL}/run",
                json=payload,
                headers=headers,
            )

        if resp.status_code in (200, 201, 202):
            logger.info(
                "hermes_http: submitted run %s, status %d", run.id, resp.status_code
            )
            return RunResult(
                status=RunStatus.COMPLETED,
                prompt_path=str(prompt_path),
            )

        logger.error(
            "hermes_http: unexpected status %d — %s", resp.status_code, resp.text[:200]
        )
        return RunResult(
            status=RunStatus.FAILED,
            prompt_path=str(prompt_path),
            error_message=f"Hermes returned HTTP {resp.status_code}",
        )

    except httpx.TimeoutException:
        err = f"Hermes request timed out after {HERMES_TIMEOUT_MS}ms"
        logger.error("hermes_http: %s", err)
        return RunResult(
            status=RunStatus.FAILED,
            prompt_path=str(prompt_path),
            error_message=err,
        )
    except Exception as e:
        logger.error("hermes_http: request failed: %s", e)
        return RunResult(
            status=RunStatus.FAILED,
            prompt_path=str(prompt_path),
            error_message=str(e),
        )
