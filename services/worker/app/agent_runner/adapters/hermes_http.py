import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import httpx

from ..config import (
    HERMES_API_KEY,
    HERMES_API_URL,
    HERMES_FALLBACK_MODE,
    HERMES_TIMEOUT_SECONDS,
)
from ..types import AgentRun, RunResult, RunStatus
from . import hermes_manual, prompt_only

logger = logging.getLogger(__name__)


def _build_v1_payload(run: AgentRun, prompt: str, prompt_path: str) -> dict:
    return {
        "run_id": run.id,
        "task_id": run.command_id or run.job_id,
        "source": run.source,
        "agent_role": run.agent_role,
        "skills": run.skills,
        "workflow": run.workflow,
        "prompt": prompt,
        "prompt_path": prompt_path,
        "metadata": {
            "rag_results_count": run.rag_results_count,
            "rag_top_path": run.rag_top_path,
            "environment": "",
            "mode": "",
            "risk_level": 1,
        },
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }


def _normalize_vstat(v: str) -> str:
    v_lower = (v or "").lower().strip()
    if "pass" in v_lower:
        return "pass"
    if "fail" in v_lower:
        return "fail"
    if v_lower:
        return "warning"
    return "warning"


def _extract_report(data: dict) -> tuple:
    """Returns (final_report, summary, verification_status). Empty strings = no report."""
    # Format A: {final_report, summary?, verification_status?}
    if "final_report" in data:
        return (
            data["final_report"],
            data.get("summary", ""),
            _normalize_vstat(data.get("verification_status", "")),
        )
    # Format B: {content}
    if "content" in data and isinstance(data["content"], str):
        return data["content"], "", "warning"
    # Format C: {message: {content}}
    msg = data.get("message") or {}
    if isinstance(msg, dict) and "content" in msg:
        return msg["content"], "", "warning"
    return "", "", ""


def _save_report_files(
    art: Path,
    run_id: str,
    final_report: str,
    summary: str,
    vstat: str,
    source: str = "hermes",
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    report_md = art / f"{run_id}.report.md"
    report_json = art / f"{run_id}.report.json"
    report_md.write_text(final_report, encoding="utf-8")
    report_json.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "report_source": source,
                "final_report": final_report,
                "summary": summary,
                "verification_status": vstat,
                "report_saved_at": now,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"report_md_path": str(report_md), "saved_at": now}


async def _do_fallback(
    run: AgentRun,
    prompt: str,
    artifact_dir: str,
    push_event: Optional[Callable],
    error: str = "",
) -> RunResult:
    fallback = HERMES_FALLBACK_MODE
    if push_event:
        try:
            await push_event(
                "hermes_http_fallback_manual",
                f"Falling back to {fallback}" + (f" (reason: {error[:120]})" if error else ""),
            )
        except Exception:
            pass
    logger.warning("hermes_http: fallback to %s error=%s", fallback, error[:120])

    if fallback == "prompt_only":
        result = await prompt_only.run(run, prompt, artifact_dir)
    else:
        result = await hermes_manual.run(run, prompt, artifact_dir)

    result.fallback_mode = fallback
    if not result.error_message and error:
        result.error_message = f"Hermes failed: {error[:120]} → fallback {fallback}"
    return result


async def run(
    run: AgentRun,
    prompt: str,
    artifact_dir: str,
    push_event: Optional[Callable] = None,
) -> RunResult:
    art = Path(artifact_dir)
    art.mkdir(parents=True, exist_ok=True)

    prompt_path = art / f"{run.id}.prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    async def _push(action: str, msg: str = "") -> None:
        if push_event:
            try:
                await push_event(action, msg)
            except Exception:
                pass

    # ── No URL → immediate fallback ──────────────────────────────────────────
    if not HERMES_API_URL:
        logger.warning("hermes_http: HERMES_API_URL not set → fallback to %s", HERMES_FALLBACK_MODE)
        return await _do_fallback(run, prompt, artifact_dir, push_event, error="HERMES_API_URL not configured")

    # ── Save payload ──────────────────────────────────────────────────────────
    payload = _build_v1_payload(run, prompt, str(prompt_path))
    payload_path = art / f"{run.id}.hermes-payload.json"
    payload_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # NOTE: API key is never logged
    headers = {"Content-Type": "application/json"}
    if HERMES_API_KEY:
        headers["Authorization"] = f"Bearer {HERMES_API_KEY}"

    await _push("hermes_http_requested", f"POST {HERMES_API_URL}/run run_id={run.id}")
    logger.info("hermes_http: POST %s/run run_id=%s", HERMES_API_URL, run.id)

    # ── HTTP request ──────────────────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=HERMES_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{HERMES_API_URL}/run",
                json=payload,
                headers=headers,
            )
    except httpx.TimeoutException:
        err = f"Timeout after {HERMES_TIMEOUT_SECONDS}s"
        logger.error("hermes_http: %s", err)
        await _push("hermes_http_failed", err)
        return await _do_fallback(run, prompt, artifact_dir, push_event, error=err)
    except Exception as e:
        err = f"Connection error: {e}"
        logger.error("hermes_http: %s", err)
        await _push("hermes_http_failed", err)
        return await _do_fallback(run, prompt, artifact_dir, push_event, error=str(e))

    await _push("hermes_http_payload_sent", f"HTTP {resp.status_code}")

    if resp.status_code not in (200, 201, 202):
        err = f"HTTP {resp.status_code}: {resp.text[:200]}"
        logger.error("hermes_http: unexpected status %s", err)
        await _push("hermes_http_failed", err)
        return await _do_fallback(run, prompt, artifact_dir, push_event, error=err)

    # ── Parse response ────────────────────────────────────────────────────────
    try:
        data = resp.json()
    except Exception:
        raw_path = art / f"{run.id}.hermes-raw.txt"
        raw_path.write_text(resp.text[:50000], encoding="utf-8")
        await _push(
            "hermes_http_response_received",
            f"Non-JSON response (HTTP {resp.status_code}) saved as raw",
        )
        logger.warning("hermes_http: non-JSON response for run %s", run.id)
        return RunResult(
            status=RunStatus.HERMES_RESPONSE_UNRECOGNIZED,
            prompt_path=str(prompt_path),
            error_message=f"Hermes returned non-JSON (HTTP {resp.status_code})",
        )

    final_report, summary, vstat = _extract_report(data)
    await _push(
        "hermes_http_response_received",
        f"Report present={bool(final_report)} verification={vstat or 'none'}",
    )

    # ── Auto-save report ──────────────────────────────────────────────────────
    if final_report:
        report_info = _save_report_files(art, run.id, final_report, summary, vstat)
        await _push("hermes_report_saved", f"Report saved verification={vstat}")
        await _push("task_completed_from_hermes", "Task completed from Hermes HTTP response")
        logger.info("hermes_http: report saved run=%s verification=%s", run.id, vstat)
        return RunResult(
            status=RunStatus.COMPLETED_REPORT_SAVED,
            prompt_path=str(prompt_path),
            report_path=report_info["report_md_path"],
            final_report=final_report,
            output_summary=summary or final_report[:200],
            verification_status=vstat,
        )

    # ── 202 / queued — no report yet ─────────────────────────────────────────
    logger.info(
        "hermes_http: run %s submitted (HTTP %d), no report in response — waiting",
        run.id, resp.status_code,
    )
    await _push(
        "hermes_http_payload_sent",
        f"Submitted (HTTP {resp.status_code}), waiting for async report",
    )
    return RunResult(
        status=RunStatus.WAITING_HERMES,
        prompt_path=str(prompt_path),
    )
