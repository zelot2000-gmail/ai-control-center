import asyncio
import json
import logging
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import httpx

from ..config import (
    HERMES_API_KEY,
    HERMES_API_URL,
    HERMES_FALLBACK_MODE,
    HERMES_RETRY_ATTEMPTS,
    HERMES_RETRY_BACKOFF_SECONDS,
    HERMES_TIMEOUT_SECONDS,
)
from ..types import AgentRun, RunResult, RunStatus
from . import hermes_manual, prompt_only

logger = logging.getLogger(__name__)


def _normalize_vstat(v: str) -> str:
    """Normalize hermes verification_status → uppercase canonical. Empty → UNKNOWN."""
    v_lower = (v or "").lower().strip()
    if v_lower in ("pass", "passed", "ok", "success", "successful"):
        return "PASS"
    if v_lower in ("warning", "warn"):
        return "WARNING"
    if v_lower in ("fail", "failed", "error", "failed_check"):
        return "FAIL"
    return "UNKNOWN"


def _mask_endpoint_url(url: str) -> str:
    """Mask query-param secrets (token, api_key, key, secret) in URL."""
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        _SECRET_PARAMS = {"token", "api_key", "apikey", "key", "secret", "auth", "password"}
        masked = {k: (["***"] if k.lower() in _SECRET_PARAMS else v) for k, v in params.items()}
        new_query = urllib.parse.urlencode(masked, doseq=True)
        return urllib.parse.urlunparse(parsed._replace(query=new_query))
    except Exception:
        return url[:80] + ("..." if len(url) > 80 else "")


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


def _detect_response_format(data: dict) -> str:
    """Identify which response format hermes returned (A/B/C/D/E/unrecognized)."""
    if "final_report" in data:
        return "A"
    if "content" in data and isinstance(data["content"], str):
        return "B"
    msg = data.get("message") or {}
    if isinstance(msg, dict) and "content" in msg:
        return "C"
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        msg0 = (choices[0] or {}).get("message") or {}
        if isinstance(msg0, dict) and "content" in msg0:
            return "D"
    data_inner = data.get("data") or {}
    if isinstance(data_inner, dict) and "final_report" in data_inner:
        return "E"
    return "unrecognized"


def _extract_report(data: dict) -> tuple:
    """Returns (final_report, summary, verification_status). Empty strings = no report."""
    # Format A: {final_report, summary?, verification_status?}
    if "final_report" in data:
        return (
            data["final_report"],
            data.get("summary", ""),
            _normalize_vstat(data.get("verification_status", "")),
        )
    # Format B: {content: "..."}
    if "content" in data and isinstance(data["content"], str):
        return data["content"], "", "UNKNOWN"
    # Format C: {message: {content: "..."}}
    msg = data.get("message") or {}
    if isinstance(msg, dict) and "content" in msg:
        return msg["content"], "", "UNKNOWN"
    # Format D: OpenAI-style {choices: [{message: {content: "..."}}]}
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        msg0 = (choices[0] or {}).get("message") or {}
        if isinstance(msg0, dict) and "content" in msg0:
            return msg0["content"], "", "UNKNOWN"
    # Format E: {data: {final_report, summary?, verification_status?}}
    data_inner = data.get("data") or {}
    if isinstance(data_inner, dict) and "final_report" in data_inner:
        return (
            data_inner["final_report"],
            data_inner.get("summary", ""),
            _normalize_vstat(data_inner.get("verification_status", "")),
        )
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


async def _post_with_retry(url: str, payload: dict, headers: dict) -> httpx.Response:
    """POST with retry on network errors, timeouts, 5xx, and 429.
    4xx (other than 429) are not retried.
    Raises on final failure.
    """
    max_attempts = max(1, HERMES_RETRY_ATTEMPTS + 1)
    last_exc: Optional[Exception] = None
    for attempt in range(max_attempts):
        is_last = attempt == max_attempts - 1
        try:
            async with httpx.AsyncClient(timeout=HERMES_TIMEOUT_SECONDS) as client:
                resp = await client.post(url, json=payload, headers=headers)
            should_retry = resp.status_code == 429 or resp.status_code >= 500
            if should_retry and not is_last:
                logger.warning(
                    "hermes_http: HTTP %d, retrying (%d/%d) in %.1fs",
                    resp.status_code, attempt + 2, max_attempts, HERMES_RETRY_BACKOFF_SECONDS,
                )
                await asyncio.sleep(HERMES_RETRY_BACKOFF_SECONDS)
                continue
            return resp
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
            last_exc = exc
            if not is_last:
                logger.warning(
                    "hermes_http: %s, retrying (%d/%d) in %.1fs",
                    exc, attempt + 2, max_attempts, HERMES_RETRY_BACKOFF_SECONDS,
                )
                await asyncio.sleep(HERMES_RETRY_BACKOFF_SECONDS)
                continue
    if last_exc:
        raise last_exc
    raise RuntimeError("hermes_http: _post_with_retry exhausted without response")


async def _do_fallback(
    run: AgentRun,
    prompt: str,
    artifact_dir: str,
    push_event: Optional[Callable],
    error: str = "",
) -> RunResult:
    fallback = HERMES_FALLBACK_MODE
    fallback_reason = error[:200] if error else "hermes_http fallback"
    if push_event:
        try:
            await push_event(
                "hermes_http_fallback_manual",
                f"Falling back to {fallback}" + (f" (reason: {error[:120]})" if error else ""),
            )
        except Exception:
            pass
    logger.warning("hermes_http: fallback to %s error=%s", fallback, error[:200])

    if fallback == "prompt_only":
        result = await prompt_only.run(run, prompt, artifact_dir)
    else:
        result = await hermes_manual.run(run, prompt, artifact_dir)

    result.fallback_mode = fallback
    result.fallback_reason = fallback_reason
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

    masked_endpoint = _mask_endpoint_url(HERMES_API_URL)

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
    await _push("hermes_http_payload_saved", f"Payload saved run_id={run.id}")

    # NOTE: API key is never logged — only used in Authorization header
    headers = {"Content-Type": "application/json"}
    if HERMES_API_KEY:
        headers["Authorization"] = f"Bearer {HERMES_API_KEY}"

    await _push("hermes_http_requested", f"POST {masked_endpoint}/run run_id={run.id}")
    logger.info("hermes_http: POST %s/run run_id=%s", masked_endpoint, run.id)

    # ── HTTP request (with retry) ─────────────────────────────────────────────
    try:
        resp = await _post_with_retry(f"{HERMES_API_URL}/run", payload, headers)
    except httpx.TimeoutException:
        err = f"Timeout after {HERMES_TIMEOUT_SECONDS}s (attempts={max(1, HERMES_RETRY_ATTEMPTS + 1)})"
        logger.error("hermes_http: %s", err)
        await _push("hermes_http_failed", err)
        result = await _do_fallback(run, prompt, artifact_dir, push_event, error=err)
        result.hermes_endpoint = masked_endpoint
        return result
    except Exception as e:
        err = f"Connection error: {type(e).__name__}: {e}"
        logger.error("hermes_http: %s", err)
        await _push("hermes_http_failed", err)
        result = await _do_fallback(run, prompt, artifact_dir, push_event, error=err)
        result.hermes_endpoint = masked_endpoint
        return result

    http_status = resp.status_code
    await _push("hermes_http_payload_sent", f"HTTP {http_status}")

    if http_status not in (200, 201, 202):
        err = f"HTTP {http_status}: {resp.text[:200]}"
        logger.error("hermes_http: unexpected status %s", err)
        await _push("hermes_http_failed", err)
        result = await _do_fallback(run, prompt, artifact_dir, push_event, error=err)
        result.hermes_endpoint = masked_endpoint
        result.hermes_http_status = http_status
        return result

    # ── Parse response ────────────────────────────────────────────────────────
    response_received_at = datetime.now(timezone.utc).isoformat()
    response_path = art / f"{run.id}.hermes-response.json"

    try:
        data = resp.json()
    except Exception:
        # Non-JSON response
        response_path.write_text(
            json.dumps(
                {
                    "run_id": run.id,
                    "http_status": http_status,
                    "response_format": "non_json",
                    "received_at": response_received_at,
                    "raw_text": resp.text[:50000],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        await _push(
            "hermes_http_response_received",
            f"Non-JSON response (HTTP {http_status}) — saved as hermes-response.json",
        )
        logger.warning("hermes_http: non-JSON response for run %s", run.id)
        result = await _do_fallback(run, prompt, artifact_dir, push_event, error=f"Non-JSON response HTTP {http_status}")
        result.hermes_endpoint = masked_endpoint
        result.hermes_http_status = http_status
        result.hermes_response_format = "non_json"
        result.response_received_at = response_received_at
        result.status = RunStatus.HERMES_RESPONSE_UNRECOGNIZED
        return result

    fmt = _detect_response_format(data)

    # ── Save hermes-response.json ─────────────────────────────────────────────
    response_path.write_text(
        json.dumps(
            {
                "run_id": run.id,
                "http_status": http_status,
                "response_format": fmt,
                "received_at": response_received_at,
                "data": data,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    await _push(
        "hermes_http_response_received",
        f"Response received HTTP {http_status} format={fmt}",
    )
    await _push("hermes_http_response_saved", f"Response saved format={fmt}")
    logger.info("hermes_http: response format=%s run=%s", fmt, run.id)

    # ── Unrecognized format ───────────────────────────────────────────────────
    if fmt == "unrecognized":
        err = f"Response format unrecognized (HTTP {http_status})"
        logger.warning("hermes_http: %s for run %s", err, run.id)
        await _push("hermes_http_failed", err)
        result = await _do_fallback(run, prompt, artifact_dir, push_event, error=err)
        result.hermes_endpoint = masked_endpoint
        result.hermes_http_status = http_status
        result.hermes_response_format = fmt
        result.response_received_at = response_received_at
        result.status = RunStatus.HERMES_RESPONSE_UNRECOGNIZED
        return result

    final_report, summary, vstat = _extract_report(data)

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
            hermes_endpoint=masked_endpoint,
            hermes_http_status=http_status,
            hermes_response_format=fmt,
            response_received_at=response_received_at,
        )

    # ── 202 / queued — no report yet ─────────────────────────────────────────
    logger.info(
        "hermes_http: run %s submitted (HTTP %d), no report in response — waiting",
        run.id, http_status,
    )
    await _push(
        "hermes_http_payload_sent",
        f"Submitted (HTTP {http_status}), waiting for async report",
    )
    return RunResult(
        status=RunStatus.WAITING_HERMES,
        prompt_path=str(prompt_path),
        hermes_endpoint=masked_endpoint,
        hermes_http_status=http_status,
        hermes_response_format=fmt,
        response_received_at=response_received_at,
    )
