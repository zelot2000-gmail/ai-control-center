import asyncio
import json
import logging
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import httpx

from ..config import load_effective_provider_config
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


_SYSTEM_PROMPT = (
    "You are Hermes Agent Runner inside AI Control Center. "
    "Return a concise final report with Summary, Issues Found, Recommendations, "
    "Next Actions, and Verification Status."
)


def _build_openai_payload(run: AgentRun, prompt: str, model: str, temperature) -> dict:
    payload: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    }
    if temperature is not None:
        payload["temperature"] = temperature
    return payload


def _is_temperature_error(resp: httpx.Response) -> bool:
    """Return True if response indicates the model rejected the `temperature` param."""
    if resp.status_code != 400:
        return False
    try:
        body = resp.json()
    except Exception:
        body = None
    if isinstance(body, dict):
        err = body.get("error") or {}
        if isinstance(err, dict):
            if err.get("param") == "temperature":
                return True
            code = (err.get("code") or "").lower()
            msg = (err.get("message") or "").lower()
            if "temperature" in msg and (
                code in ("unsupported_value", "unsupported_parameter")
                or "unsupported" in msg
                or "does not support" in msg
                or "only the default" in msg
            ):
                return True
    text = (resp.text or "").lower()
    if "temperature" in text and ("unsupported" in text or "does not support" in text):
        return True
    return False


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


async def _post_with_retry(
    url: str,
    payload: dict,
    headers: dict,
    *,
    timeout_seconds: float,
    retry_attempts: int,
    retry_backoff_seconds: float,
) -> httpx.Response:
    """POST with retry on network errors, timeouts, 5xx, and 429.
    4xx (other than 429) are not retried.
    Raises on final failure.
    """
    max_attempts = max(1, retry_attempts + 1)
    last_exc: Optional[Exception] = None
    for attempt in range(max_attempts):
        is_last = attempt == max_attempts - 1
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                resp = await client.post(url, json=payload, headers=headers)
            should_retry = resp.status_code == 429 or resp.status_code >= 500
            if should_retry and not is_last:
                logger.warning(
                    "hermes_http: HTTP %d, retrying (%d/%d) in %.1fs",
                    resp.status_code, attempt + 2, max_attempts, retry_backoff_seconds,
                )
                await asyncio.sleep(retry_backoff_seconds)
                continue
            return resp
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
            last_exc = exc
            if not is_last:
                logger.warning(
                    "hermes_http: %s, retrying (%d/%d) in %.1fs",
                    exc, attempt + 2, max_attempts, retry_backoff_seconds,
                )
                await asyncio.sleep(retry_backoff_seconds)
                continue
    if last_exc:
        raise last_exc
    raise RuntimeError("hermes_http: _post_with_retry exhausted without response")


async def _do_fallback(
    run: AgentRun,
    prompt: str,
    artifact_dir: str,
    push_event: Optional[Callable],
    *,
    fallback_mode: str,
    error: str = "",
    provider: str = "",
    request_format: str = "",
) -> RunResult:
    fallback = fallback_mode or "hermes_manual"
    fallback_reason = error[:500] if error else "hermes_http fallback (reason unset)"
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
    result.hermes_provider = provider
    result.hermes_request_format = request_format
    if not result.error_message and error:
        result.error_message = f"Hermes failed: {error[:200]} → fallback {fallback}"
    return result


def _human_http_reason(status: int, body_text: str) -> str:
    """Build a clear fallback_reason from an upstream HTTP failure."""
    body = (body_text or "").strip()
    try:
        j = json.loads(body) if body else None
    except Exception:
        j = None
    detail = ""
    if isinstance(j, dict):
        err = j.get("error")
        if isinstance(err, dict):
            detail = (err.get("message") or err.get("code") or "")[:200]
    if not detail:
        detail = body[:200]

    if status == 400:
        return f"OpenAI HTTP 400: {detail or 'bad request'}"
    if status == 401:
        return f"OpenAI HTTP 401: invalid API key{(' — ' + detail) if detail else ''}"
    if status == 403:
        return f"OpenAI HTTP 403: forbidden{(' — ' + detail) if detail else ''}"
    if status == 404:
        return f"OpenAI HTTP 404: model not found{(' — ' + detail) if detail else ''}"
    if status == 429:
        return f"OpenAI HTTP 429: quota/rate limit{(' — ' + detail) if detail else ''}"
    if status >= 500:
        return f"OpenAI HTTP {status}: upstream error{(' — ' + detail) if detail else ''}"
    return f"OpenAI HTTP {status}{(': ' + detail) if detail else ''}"


async def run(
    run: AgentRun,
    prompt: str,
    artifact_dir: str,
    push_event: Optional[Callable] = None,
) -> RunResult:
    # ── Load effective config at runtime (respects Save from /settings) ──────
    cfg = load_effective_provider_config()
    api_url        = cfg["hermes_api_url"]
    api_key        = cfg["hermes_api_key"]
    model          = cfg["hermes_model"]
    request_format = cfg["hermes_request_format"]
    fallback_mode  = cfg["hermes_fallback_mode"]
    timeout_s      = cfg["hermes_timeout_seconds"]
    retry_attempts = cfg["hermes_retry_attempts"]
    retry_backoff  = cfg["hermes_retry_backoff_seconds"]
    temperature    = cfg["hermes_temperature"]
    provider       = cfg["hermes_provider"]

    logger.info(
        "hermes_http: cfg provider=%s format=%s url=%s model=%s api_key_set=%s key_len=%d temp=%s source=%s",
        provider, request_format, _mask_endpoint_url(api_url), model,
        bool(api_key), len(api_key or ""), temperature, cfg["runtime_config_source"],
    )

    art = Path(artifact_dir)
    art.mkdir(parents=True, exist_ok=True)

    masked_endpoint = _mask_endpoint_url(api_url)

    prompt_path = art / f"{run.id}.prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    async def _push(action: str, msg: str = "") -> None:
        if push_event:
            try:
                await push_event(action, msg)
            except Exception:
                pass

    # ── No URL → immediate fallback with clear reason ────────────────────────
    if not api_url:
        reason = "HERMES_API_URL not configured (set in /settings or .env)"
        logger.warning("hermes_http: %s → fallback to %s", reason, fallback_mode)
        result = await _do_fallback(
            run, prompt, artifact_dir, push_event,
            fallback_mode=fallback_mode, error=reason,
        )
        result.hermes_endpoint = masked_endpoint
        return result

    # ── Build payload and select endpoint ────────────────────────────────────
    if request_format == "openai_compatible":
        payload = _build_openai_payload(run, prompt, model, temperature)
        post_url = api_url
        post_label = masked_endpoint
    else:  # native
        payload = _build_v1_payload(run, prompt, str(prompt_path))
        post_url = f"{api_url.rstrip('/')}/run"
        post_label = f"{masked_endpoint}/run"

    # ── Save payload ──────────────────────────────────────────────────────────
    payload_path = art / f"{run.id}.hermes-payload.json"
    payload_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    await _push("hermes_http_payload_saved", f"Payload saved format={request_format} run_id={run.id}")

    # NOTE: API key is never logged — only used in Authorization header
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    await _push(
        "hermes_http_requested",
        f"POST {post_label} format={request_format} provider={provider} run_id={run.id}",
    )

    post_kwargs = dict(
        timeout_seconds=timeout_s,
        retry_attempts=retry_attempts,
        retry_backoff_seconds=retry_backoff,
    )

    # ── HTTP request (with retry) ─────────────────────────────────────────────
    try:
        resp = await _post_with_retry(post_url, payload, headers, **post_kwargs)
    except httpx.TimeoutException:
        err = f"Connection timeout after {timeout_s}s (attempts={max(1, retry_attempts + 1)})"
        logger.error("hermes_http: %s", err)
        await _push("hermes_http_failed", err)
        result = await _do_fallback(
            run, prompt, artifact_dir, push_event,
            fallback_mode=fallback_mode, error=err,
            provider=provider, request_format=request_format,
        )
        result.hermes_endpoint = masked_endpoint
        return result
    except Exception as e:
        err = f"Connection error: {type(e).__name__}: {e}"
        logger.error("hermes_http: %s", err)
        await _push("hermes_http_failed", err)
        result = await _do_fallback(
            run, prompt, artifact_dir, push_event,
            fallback_mode=fallback_mode, error=err,
            provider=provider, request_format=request_format,
        )
        result.hermes_endpoint = masked_endpoint
        return result

    http_status = resp.status_code
    await _push("hermes_http_payload_sent", f"HTTP {http_status}")

    # ── Temperature-unsupported retry ────────────────────────────────────────
    if (
        request_format == "openai_compatible"
        and "temperature" in payload
        and _is_temperature_error(resp)
    ):
        logger.warning(
            "hermes_http: model rejected temperature, retrying without (run=%s)", run.id,
        )
        await _push(
            "hermes_http_temperature_retry",
            "Model rejected temperature; retrying without it",
        )
        payload.pop("temperature", None)
        payload_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        try:
            resp = await _post_with_retry(post_url, payload, headers, **post_kwargs)
        except httpx.TimeoutException:
            err = f"Connection timeout after {timeout_s}s on temperature-retry"
            logger.error("hermes_http: %s", err)
            await _push("hermes_http_failed", err)
            result = await _do_fallback(
                run, prompt, artifact_dir, push_event,
                fallback_mode=fallback_mode, error=err,
            )
            result.hermes_endpoint = masked_endpoint
            return result
        except Exception as e:
            err = f"Connection error on temperature-retry: {type(e).__name__}: {e}"
            logger.error("hermes_http: %s", err)
            await _push("hermes_http_failed", err)
            result = await _do_fallback(
                run, prompt, artifact_dir, push_event,
                fallback_mode=fallback_mode, error=err,
            )
            result.hermes_endpoint = masked_endpoint
            return result
        http_status = resp.status_code
        await _push(
            "hermes_http_payload_sent",
            f"HTTP {http_status} (after temperature-retry)",
        )

    if http_status not in (200, 201, 202):
        reason = _human_http_reason(http_status, resp.text or "")
        logger.error("hermes_http: %s", reason)
        await _push("hermes_http_failed", reason)
        result = await _do_fallback(
            run, prompt, artifact_dir, push_event,
            fallback_mode=fallback_mode, error=reason,
            provider=provider, request_format=request_format,
        )
        result.hermes_endpoint = masked_endpoint
        result.hermes_http_status = http_status
        return result

    # ── Parse response ────────────────────────────────────────────────────────
    response_received_at = datetime.now(timezone.utc).isoformat()
    response_path = art / f"{run.id}.hermes-response.json"

    try:
        data = resp.json()
    except Exception:
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
        reason = f"Non-JSON response from provider (HTTP {http_status})"
        result = await _do_fallback(
            run, prompt, artifact_dir, push_event,
            fallback_mode=fallback_mode, error=reason,
            provider=provider, request_format=request_format,
        )
        result.hermes_endpoint = masked_endpoint
        result.hermes_http_status = http_status
        result.hermes_response_format = "non_json"
        result.response_received_at = response_received_at
        result.status = RunStatus.HERMES_RESPONSE_UNRECOGNIZED
        return result

    fmt = _detect_response_format(data)

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

    if fmt == "unrecognized":
        reason = f"Provider response format unrecognized (HTTP {http_status})"
        logger.warning("hermes_http: %s for run %s", reason, run.id)
        await _push("hermes_http_failed", reason)
        result = await _do_fallback(
            run, prompt, artifact_dir, push_event,
            fallback_mode=fallback_mode, error=reason,
            provider=provider, request_format=request_format,
        )
        result.hermes_endpoint = masked_endpoint
        result.hermes_http_status = http_status
        result.hermes_response_format = fmt
        result.response_received_at = response_received_at
        result.status = RunStatus.HERMES_RESPONSE_UNRECOGNIZED
        return result

    final_report, summary, vstat = _extract_report(data)

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
            hermes_provider=provider,
            hermes_request_format=request_format,
        )

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
        hermes_provider=provider,
        hermes_request_format=request_format,
    )
