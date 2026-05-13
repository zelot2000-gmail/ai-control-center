import os
import re
import json
import logging
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent_runner import (
    AGENT_RUNNER_ENABLED,
    AGENT_RUNNER_ARTIFACT_DIR,
    AGENT_RUNNER_MODE,
    run_agent,
    get_run,
    get_runs_for_job,
    list_runs as list_agent_runs,
    update_run as update_agent_run,
)
from app.agent_runner.types import normalize_verification_status

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="Worker Service", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

HERMES_CLI_PATH = os.getenv("HERMES_CLI_PATH", "")
AGENTUNIVERSE_CLI_PATH = os.getenv("AGENTUNIVERSE_CLI_PATH", "")
MOBILE_GATEWAY_URL = os.getenv("MOBILE_GATEWAY_URL", "http://mobile-gateway:8088")
RAG_API_URL = os.getenv("RAG_API_URL", "http://rag-api:8090")
EXPORTS_DIR = Path("/app/data/exports")
AGENTS_MD_PATH = Path("/app/AGENTS.md")

# Ensure data directories and JSON files exist at import time (safe on re-import)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
Path(AGENT_RUNNER_ARTIFACT_DIR).mkdir(parents=True, exist_ok=True)
_agent_runs_file = Path("/app/data/agent-runs.json")
_agent_runs_file.parent.mkdir(parents=True, exist_ok=True)
if not _agent_runs_file.exists():
    _agent_runs_file.write_text("{}", encoding="utf-8")
SKILLS_INDEX_PATH = Path("/app/core/skills/index.json")
WORKFLOWS_INDEX_PATH = Path("/app/core/workflows/index.json")

OBSERVER_HEALTH_TARGETS = [
    ("mobile-gateway", "http://mobile-gateway:8088/health"),
    ("rag-api",        "http://rag-api:8090/health"),
    ("tto-api",        "http://tto-api:8091/health"),
    ("rtk-bridge",     "http://rtk-bridge:8092/health"),
    ("webhook-gateway","http://webhook-gateway:8093/health"),
    ("observer",       "http://observer:8094/health"),
    ("worker",         "http://worker:8095/health"),
    ("qdrant",         "http://qdrant:6333/healthz"),
]


def _can_run_agent(task: dict, runner_mode: str) -> dict:
    risk = task.get("risk", 1)
    constraints = task.get("constraints") or {}
    env = constraints.get("environment", "wsl") if isinstance(constraints, dict) else "wsl"
    mode = constraints.get("mode", "plan-only") if isinstance(constraints, dict) else "plan-only"
    already_approved = task.get("approval_status", "") == "approved"

    if env == "production" and not already_approved:
        return {
            "allowed": False,
            "reason": "Agent Runner ไม่รัน environment=production โดยตรง — ต้องได้รับ approval",
            "approval_required": True,
            "approval_phrase": "CONFIRM DANGEROUS",
            "blocked_status": "blocked_approval_required",
        }

    if mode == "execute" and not already_approved:
        return {
            "allowed": False,
            "reason": "mode=execute ต้องได้รับ approval ก่อนรัน Agent",
            "approval_required": True,
            "approval_phrase": "APPROVE AGENT EXECUTE",
            "blocked_status": "blocked_approval_required",
        }

    if risk >= 3 and not already_approved:
        phrase = {3: "CONFIRM STAGING", 4: "CONFIRM DEPLOY", 5: "CONFIRM DANGEROUS"}.get(risk, "CONFIRM STAGING")
        return {
            "allowed": False,
            "reason": f"Risk level {risk} ต้องได้รับ approval ก่อนรัน Agent",
            "approval_required": True,
            "approval_phrase": phrase,
            "blocked_status": "blocked_approval_required",
        }

    if runner_mode == "hermes_http" and risk > 1 and not already_approved:
        return {
            "allowed": False,
            "reason": "hermes_http mode + risk > 1 ต้องได้รับ approval ก่อน",
            "approval_required": True,
            "approval_phrase": "APPROVE HERMES HTTP",
            "blocked_status": "blocked_approval_required",
        }

    return {
        "allowed": True,
        "reason": "ผ่าน approval gate",
        "approval_required": False,
        "approval_phrase": "",
        "blocked_status": "",
    }


def _generate_execution_reason(task: dict, mode: str, autonomy: int) -> str:
    intent = task.get("intent", "").lower()
    risk = task.get("risk", 1)
    agents = task.get("agents", [])
    workflow = task.get("workflow", [])
    agents_str = ", ".join(agents) if agents else "manager"

    health_keywords = ["health", "ตรวจ", "สุขภาพ", "check", "monitor", "status"]
    if mode == "workflow" and any(k in intent for k in health_keywords):
        return (
            "งานนี้เป็น health check แบบ read-only "
            "มีขั้นตอนชัดเจน "
            f"จึงใช้ Workflow Mode และ autonomy level {autonomy}"
        )
    if mode == "workflow":
        return (
            f"งานนี้มีขั้นตอนชัดเจน ({len(workflow)} steps) risk={risk} "
            f"เหมาะกับ Workflow Mode autonomy level {autonomy}"
        )
    if mode == "agent":
        return (
            f"งานนี้ต้องการ reasoning หลายรอบ "
            f"(risk={risk}, agents={agents_str}) "
            f"จึงใช้ Agent Mode autonomy level {autonomy}"
        )
    if mode == "hybrid":
        return (
            f"งานนี้มีโครงสร้างชัดเจนแต่ต้องการ judgment บางจุด "
            f"(risk={risk}, agents={agents_str}) "
            f"จึงใช้ Hybrid Mode autonomy level {autonomy}"
        )
    return f"mode={mode}, risk={risk}, autonomy={autonomy}"


def _load_agents_md() -> str:
    if AGENTS_MD_PATH.exists():
        return AGENTS_MD_PATH.read_text(encoding="utf-8")
    return "AGENTS.md not found"


def normalize_task(task: dict) -> dict:
    """Normalize task schema — handle variants from mobile-gateway or manual input."""
    # intent: str or dict → str
    intent = task.get("intent", "")
    if isinstance(intent, dict):
        intent = intent.get("text", str(intent))
    intent = str(intent).strip()

    # agents: list or dict → list
    agents_raw = task.get("agents", [])
    if isinstance(agents_raw, dict):
        agents = [k for k, v in agents_raw.items() if v]
    elif isinstance(agents_raw, list):
        agents = [str(a) for a in agents_raw]
    else:
        agents = []

    # skills: list or dict → list
    skills_raw = task.get("skills", [])
    if isinstance(skills_raw, dict):
        skills = [k for k, v in skills_raw.items() if v]
    elif isinstance(skills_raw, list):
        skills = [str(s) for s in skills_raw]
    else:
        skills = []

    # inputs: must be dict
    inputs = task.get("inputs") or {}
    if not isinstance(inputs, dict):
        inputs = {"text": str(inputs)}

    # constraints: fallback defaults
    constraints = task.get("constraints") or {}
    if not isinstance(constraints, dict):
        constraints = {}
    constraints.setdefault("environment", "wsl")
    constraints.setdefault("mode", "plan-only")

    # risk: accept both "risk" and "risk_level"
    risk = task.get("risk") or task.get("risk_level") or 1
    try:
        risk = int(risk)
    except (TypeError, ValueError):
        risk = 1

    # workflow: default if missing
    workflow = task.get("workflow") or ["plan", "build", "verify", "report"]
    if not isinstance(workflow, list) or not workflow:
        workflow = ["plan", "build", "verify", "report"]

    return {
        **task,
        "intent": intent,
        "agents": agents,
        "skills": skills,
        "inputs": inputs,
        "constraints": constraints,
        "risk": risk,
        "workflow": workflow,
    }


async def _push_status(task_id: str, status: str) -> None:
    """Fire-and-forget: update task status in mobile-gateway."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.patch(
                f"{MOBILE_GATEWAY_URL}/tasks/{task_id}/status",
                json={"status": status},
            )
    except Exception as e:
        logger.warning("Failed to push status '%s' for %s: %s", status, task_id, e)


async def _push_agent_activity(
    task_id: str,
    *,
    current_agent: Optional[str] = None,
    speaker_agent: Optional[str] = None,
    working_agent: Optional[str] = None,
    current_step: Optional[str] = None,
    active_agents: Optional[List[str]] = None,
    event_agent: Optional[str] = None,
    event_role: str = "worker",
    event_action: Optional[str] = None,
    event_message: str = "",
) -> None:
    body: dict = {}
    if current_agent is not None:
        body["current_agent"] = current_agent
    if speaker_agent is not None:
        body["speaker_agent"] = speaker_agent
    if working_agent is not None:
        body["working_agent"] = working_agent
    if current_step is not None:
        body["current_step"] = current_step
    if active_agents is not None:
        body["active_agents"] = active_agents
    if event_agent and event_action:
        body["event"] = {
            "agent": event_agent,
            "role": event_role,
            "action": event_action,
            "message": event_message,
        }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.patch(
                f"{MOBILE_GATEWAY_URL}/tasks/{task_id}/agent-activity",
                json=body,
            )
    except Exception as e:
        logger.warning("Failed to push agent activity for %s: %s", task_id, e)


async def _push_progress(
    task_id: str,
    *,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    current_step: Optional[str] = None,
    step_name: Optional[str] = None,
    step_status: Optional[str] = None,
) -> None:
    body: dict = {}
    if status is not None:
        body["status"] = status
    if progress is not None:
        body["progress"] = progress
    if current_step is not None:
        body["current_step"] = current_step
    if step_name is not None:
        body["step_name"] = step_name
    if step_status is not None:
        body["step_status"] = step_status
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.patch(
                f"{MOBILE_GATEWAY_URL}/tasks/{task_id}/progress",
                json=body,
            )
    except Exception as e:
        logger.warning("Failed to push progress for %s: %s", task_id, e)


async def _push_result(task_id: str, result: dict) -> None:
    """Fire-and-forget: update task result in mobile-gateway."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.patch(
                f"{MOBILE_GATEWAY_URL}/tasks/{task_id}/result",
                json={"result": result},
            )
    except Exception as e:
        logger.warning("Failed to push result for %s: %s", task_id, e)


async def _rag_wiki_search(query: str, limit: int = 5) -> Tuple[list, Optional[str]]:
    """Search docs/wiki via RAG API. Returns (results, error_message)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{RAG_API_URL}/search/wiki",
                json={"query": query, "limit": limit},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("results", []), None
            return [], f"HTTP {resp.status_code}"
    except Exception as e:
        return [], str(e)


_COMPARISON_RE = re.compile(
    r"\bต่างจาก\b|\bvs\.?\b|\bเปรียบเทียบ\b|\bdifference\b|\bcompare\b",
    re.IGNORECASE,
)
_TECH_TERM_RE = re.compile(r"\b[A-Z][A-Za-z0-9]*(?:[\s\-][A-Z][A-Za-z0-9]+)*\b")


def _build_rag_queries(text: str) -> List[str]:
    """Build multi-query list from task text for better RAG recall.

    Splits comparison phrases, extracts tech terms, and generates pairwise
    queries so the embedding search has multiple entry points.
    """
    queries: List[str] = [text]

    tech_terms: List[str] = list(dict.fromkeys(
        t.strip() for t in _TECH_TERM_RE.findall(text)
        if len(t.strip()) >= 2
    ))

    if _COMPARISON_RE.search(text):
        # Pairwise comparison queries
        for i in range(len(tech_terms)):
            for j in range(i + 1, len(tech_terms)):
                queries.append(f"{tech_terms[i]} {tech_terms[j]}")
                queries.append(f"{tech_terms[i]} vs {tech_terms[j]}")
        # Individual term queries as fallback
        queries.extend(tech_terms)
    else:
        queries.extend(tech_terms)

    # Deduplicate preserving order
    seen: set = set()
    result: List[str] = []
    for q in queries:
        key = q.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(q.strip())
    return result


async def _rag_wiki_search_multi(
    queries: List[str],
    limit_per_query: int = 5,
    total_limit: int = 5,
) -> Tuple[List[dict], Optional[str]]:
    """Run multiple RAG queries, dedupe by (path, heading_path), sort by score desc."""
    best: dict = {}  # key=(path, heading_path) → highest-score result
    last_error: Optional[str] = None

    for query in queries:
        results, error = await _rag_wiki_search(query, limit=limit_per_query)
        if error:
            last_error = error
            continue
        for r in results:
            key = (r.get("path", ""), r.get("heading_path", ""))
            if key not in best or r.get("score", 0) > best[key].get("score", 0):
                best[key] = r

    if not best:
        return [], last_error

    merged = sorted(best.values(), key=lambda r: r.get("score", 0), reverse=True)
    return merged[:total_limit], None


def load_skill_context(skill_names: List[str]) -> Tuple[str, List[str]]:
    """Load SKILL.md for each skill. Returns (context_markdown, warnings)."""
    warnings: List[str] = []
    context_parts: List[str] = []

    if not SKILLS_INDEX_PATH.exists():
        warnings.append(f"skills/index.json not found at {SKILLS_INDEX_PATH}")
        return "", warnings

    try:
        index = json.loads(SKILLS_INDEX_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        warnings.append(f"Failed to parse skills/index.json: {e}")
        return "", warnings

    skill_map = {s["id"]: s for s in index.get("skills", [])}

    for skill_id in skill_names:
        if skill_id not in skill_map:
            warnings.append(f"Skill '{skill_id}' not found in index")
            continue
        skill_file = Path(f"/app/{skill_map[skill_id]['file']}")
        if not skill_file.exists():
            warnings.append(f"SKILL.md missing: {skill_file}")
            continue
        try:
            content = skill_file.read_text(encoding="utf-8")
            context_parts.append(f"### {skill_id}\n{content}")
        except Exception as e:
            warnings.append(f"Failed to read {skill_file}: {e}")

    return "\n\n".join(context_parts), warnings


def _load_skills_index() -> dict:
    if SKILLS_INDEX_PATH.exists():
        return json.loads(SKILLS_INDEX_PATH.read_text(encoding="utf-8"))
    return {"skills": []}


def _load_skill_md(skill_id: str) -> str:
    skills = _load_skills_index().get("skills", [])
    for s in skills:
        if s["id"] == skill_id:
            skill_path = Path(f"/app/{s['file']}")
            if skill_path.exists():
                return skill_path.read_text(encoding="utf-8")
    return f"SKILL.md for {skill_id} not found"


def _load_workflows_index() -> dict:
    if WORKFLOWS_INDEX_PATH.exists():
        return json.loads(WORKFLOWS_INDEX_PATH.read_text(encoding="utf-8"))
    return {"workflows": []}


def _load_workflow_md(workflow_id: str) -> str:
    workflows = _load_workflows_index().get("workflows", [])
    for wf in workflows:
        if wf["id"] == workflow_id:
            wf_path = Path(f"/app/{wf['file']}")
            if wf_path.exists():
                return wf_path.read_text(encoding="utf-8")
    return f"Workflow {workflow_id} not found"


def _get_workflow_steps(workflow_id: str) -> List[str]:
    workflows = _load_workflows_index().get("workflows", [])
    for wf in workflows:
        if wf["id"] == workflow_id:
            return wf.get("steps", [])
    return []


def _build_execution_context(task: dict) -> str:
    execution = task.get("execution", {})
    mode = execution.get("mode", "workflow")
    selected_workflow = execution.get("selected_workflow")
    autonomy = execution.get("autonomy_level", 1)
    reason = execution.get("reason_for_mode", "")

    if not reason:
        reason = _generate_execution_reason(task, mode, autonomy)

    ctx = f"\n\n## Execution Mode\n"
    ctx += f"- **Mode**: {mode}\n"
    ctx += f"- **Autonomy Level**: {autonomy}\n"
    ctx += f"- **Reason**: {reason}\n"

    if selected_workflow:
        wf_content = _load_workflow_md(selected_workflow)
        steps = _get_workflow_steps(selected_workflow)
        ctx += f"- **Selected Workflow**: {selected_workflow}\n"
        ctx += f"\n### Workflow Steps\n"
        ctx += "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
        if mode == "workflow":
            ctx += f"\n\n### Workflow Definition\n{wf_content}"
        elif mode == "hybrid":
            ctx += f"\n\n> Hybrid mode: follow workflow steps, use agent judgment at marked decision points\n"
            ctx += f"\n### Workflow Reference\n{wf_content}"
    elif mode == "agent":
        ctx += "\n> Agent mode: use dynamic reasoning, explain every tool call, do not take production actions without approval\n"

    accountability = task.get("accountability", {})
    if accountability:
        ctx += f"\n\n## Accountability\n"
        ctx += f"- Owner: {accountability.get('owner_agent', 'manager')}\n"
        ctx += f"- Agents: {', '.join(accountability.get('responsible_agents', []))}\n"
        ctx += f"- Approval required: {accountability.get('approval_required', False)}\n"
        if accountability.get("approval_phrase"):
            ctx += f"- Approval phrase needed: `{accountability['approval_phrase']}`\n"
        ctx += f"- Rollback plan: {accountability.get('rollback_plan', 'N/A')}\n"

    return ctx


_TEXT_EXTENSIONS = {".txt", ".md", ".log", ".json", ".yaml", ".yml", ".csv"}

_SECRET_RE = re.compile(
    r'(?i)(?:password|passwd|pwd|api_key|apikey|api-key|secret_key|secretkey|secret|token)'
    r'\s*[:=]\s*\S+'
    r'|bearer\s+[A-Za-z0-9\-._~+/=]{8,}'
)


def _mask_value(m: re.Match) -> str:
    s = m.group(0)
    for sep in ('=', ':'):
        idx = s.find(sep)
        if idx != -1:
            return s[:idx + 1] + '***MASKED***'
    return '***MASKED***'


def _detect_and_mask(text: str) -> Tuple[str, bool]:
    """Return (masked_text, has_secrets)."""
    has_secrets = bool(_SECRET_RE.search(text))
    if has_secrets:
        text = _SECRET_RE.sub(_mask_value, text)
    return text, has_secrets


_CLASSIFY_MAP: dict = {
    # text
    ".txt":  ("text",         "text-extract",          ["manager", "rag-curator", "observer"], ["mobile-command", "rag-ingest"]),
    ".md":   ("text",         "text-extract",          ["manager", "rag-curator"],             ["rag-ingest", "llm-wiki"]),
    ".log":  ("text",         "text-extract",          ["observer", "manager"],                ["observer-monitor"]),
    ".csv":  ("text",         "text-extract",          ["manager", "research"],                ["research-development"]),
    ".json": ("text",         "text-extract",          ["manager", "devops"],                  ["devops"]),
    ".yaml": ("text",         "text-extract",          ["manager", "devops"],                  ["devops"]),
    ".yml":  ("text",         "text-extract",          ["manager", "devops"],                  ["devops"]),
    # document
    ".pdf":  ("document",     "document-extract",      ["rag-curator", "manager", "qa"],       ["rag-ingest", "llm-wiki"]),
    ".doc":  ("document",     "document-extract",      ["rag-curator", "manager", "qa"],       ["rag-ingest", "llm-wiki"]),
    ".docx": ("document",     "document-extract",      ["rag-curator", "manager", "qa"],       ["rag-ingest", "llm-wiki"]),
    # spreadsheet
    ".xls":  ("spreadsheet",  "spreadsheet-extract",   ["manager", "qa", "research"],          ["research-development"]),
    ".xlsx": ("spreadsheet",  "spreadsheet-extract",   ["manager", "qa", "research"],          ["research-development"]),
    # presentation
    ".ppt":  ("presentation", "presentation-extract",  ["designer", "manager", "research"],    ["design-system", "research-development"]),
    ".pptx": ("presentation", "presentation-extract",  ["designer", "manager", "research"],    ["design-system", "research-development"]),
    # image
    ".jpg":  ("image",        "vision-required",       ["designer", "qa"],                     ["design-system", "browser-devtools"]),
    ".jpeg": ("image",        "vision-required",       ["designer", "qa"],                     ["design-system", "browser-devtools"]),
    ".png":  ("image",        "vision-required",       ["designer", "qa"],                     ["design-system", "browser-devtools"]),
    ".webp": ("image",        "vision-required",       ["designer", "qa"],                     ["design-system", "browser-devtools"]),
    ".gif":  ("image",        "vision-required",       ["designer", "qa"],                     ["design-system", "browser-devtools"]),
}


def classify_attachment(filename: str, content_type: str = "") -> dict:
    """Return category/analysis_mode/agents/skills for a file."""
    _, ext = os.path.splitext((filename or "").lower())
    row = _CLASSIFY_MAP.get(ext)
    if row:
        cat, mode, agents, skills = row
        return {"category": cat, "analysis_mode": mode, "recommended_agents": agents, "recommended_skills": skills}
    return {"category": "unknown", "analysis_mode": "unsupported", "recommended_agents": ["manager"], "recommended_skills": []}


def _enhance_skills_for_attachments(skills: List[str], attachments: List[dict]) -> List[str]:
    skill_set = set(skills)
    for att in attachments:
        fn = att.get("filename") or att.get("safe_filename", "")
        info = classify_attachment(fn, att.get("content_type", ""))
        skill_set.update(info["recommended_skills"])
        # Extra: .log with compose hints
        _, ext = os.path.splitext(fn.lower())
        if ext in {".yaml", ".yml"} and "compose" in fn.lower():
            skill_set.add("docker-deploy")
    return list(skill_set)


def _enhance_agents_for_attachments(agents: List[str], attachments: List[dict]) -> List[str]:
    agent_set = set(agents)
    for att in attachments:
        fn = att.get("filename") or att.get("safe_filename", "")
        info = classify_attachment(fn, att.get("content_type", ""))
        agent_set.update(info["recommended_agents"])
    return list(agent_set)


_CONTEXT_INSTRUCTIONS: dict = {
    "document": (
        "Document file detected.\n"
        "Analysis mode: document-extract\n"
        "Use document parser or RAG ingestion workflow.\n"
        "If parser is not available, ask user to convert to PDF/text or run extraction tool."
    ),
    "spreadsheet": (
        "Spreadsheet file detected.\n"
        "Analysis mode: spreadsheet-extract\n"
        "Required analysis:\n"
        "- sheet names\n"
        "- columns\n"
        "- row counts\n"
        "- summary\n"
        "- anomalies"
    ),
    "presentation": (
        "Presentation file detected.\n"
        "Analysis mode: presentation-extract\n"
        "Required analysis:\n"
        "- slide count\n"
        "- titles\n"
        "- key messages\n"
        "- design issues\n"
        "- improvement suggestions"
    ),
    "image": (
        "Image file detected.\n"
        "Analysis mode: vision-required\n"
        "Required analysis:\n"
        "- describe visible content\n"
        "- detect text/logo/layout\n"
        "- assess quality\n"
        "- design/QA recommendations"
    ),
}


def _read_attachment_context(attachment: dict, max_chars: int = 3000) -> Tuple[str, bool]:
    """Return (content_or_instructions, has_secrets)."""
    fn = attachment.get("filename") or attachment.get("safe_filename", "")
    info = classify_attachment(fn, attachment.get("content_type", ""))
    category = info["category"]

    if category == "text":
        stored_path = attachment.get("stored_path", "")
        try:
            p = Path(stored_path)
            if not p.exists():
                return ("(file not found on disk)", False)
            text = p.read_text(encoding="utf-8", errors="replace")
            if len(text) > max_chars:
                text = text[:max_chars] + "\n...(truncated)"
            return _detect_and_mask(text)
        except Exception as e:
            return (f"(error reading file: {e})", False)

    instructions = _CONTEXT_INSTRUCTIONS.get(category)
    if instructions:
        return (instructions, False)
    return (f"(unsupported file type — {attachment.get('content_type', 'unknown')})", False)


def _export_prompt(task: dict, skills_context: str, warnings: List[str], rag_results: Optional[List[dict]] = None) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    task_id = task.get("task_id", "unknown")
    export_path = EXPORTS_DIR / f"{task_id}.prompt.md"

    agents = task.get("agents", [])
    skills = task.get("skills", [])
    inputs = task.get("inputs", {})
    constraints = task.get("constraints", {})
    workflow = task.get("workflow", ["plan", "build", "verify", "report"])

    agents_md = "\n".join(f"- {a}" for a in agents) if agents else "- (none)"
    skills_md = "\n".join(f"- {s}" for s in skills) if skills else "- (none)"
    workflow_md = "\n".join(f"- {s}" for s in workflow)
    warnings_md = "\n".join(f"- ⚠️ {w}" for w in warnings) if warnings else "- (none)"

    observer_section = ""
    if "observer-monitor" in skills:
        lines = ["## Observer Health Plan"]
        for name, url in OBSERVER_HEALTH_TARGETS:
            lines.append(f"- Check {name}: {url}")
        observer_section = "\n".join(lines)

    rag_section = ""
    if any(s in skills for s in ("llm-wiki", "rag-ingest")):
        rag_section = "\n## RAG Lookup Plan\n"
        rag_section += "- ใช้ RAG Search Results ด้านล่างก่อนตอบ\n"
        rag_section += "- ถ้ามี ADR/SOP ภายใน ให้เชื่อ internal wiki ก่อน generic knowledge\n"
        rag_section += "- เวลา final report ให้ cite path เช่น: `docs/wiki/mcp/serena-mcp.md`\n"
        rag_section += "- ถ้า RAG results ไม่พอ ให้บอกว่าข้อมูลใน wiki ยังไม่พอ\n"

        rag_section += "\n## RAG Search Results\n"
        if not rag_results:
            rag_section += "\n> ⚠️ ไม่พบผลลัพธ์ที่เกี่ยวข้อง — wiki อาจยังไม่ได้ ingest หรือ rag-api ไม่ตอบสนอง\n"
        else:
            for i, r in enumerate(rag_results, 1):
                title = r.get("title", "Untitled")
                path = r.get("path", "?")
                category = r.get("category", "?")
                heading = r.get("heading_path", "")
                score = r.get("score", 0)
                tags = r.get("tags", [])
                snippet = r.get("snippet", "")
                rag_section += f"\n### {i}. {title}\n"
                rag_section += f"- path: `{path}`\n"
                rag_section += f"- category: {category}\n"
                if heading:
                    rag_section += f"- heading: {heading}\n"
                rag_section += f"- score: {score:.3f}\n"
                if tags:
                    tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
                    rag_section += f"- tags: {tags_str}\n"
                if snippet:
                    rag_section += f"- snippet:\n{snippet}\n"

    serena_section = ""
    if "serena-mcp" in skills:
        serena_section = """\n## Code Intelligence Plan (Serena MCP)

**ก่อนแก้ไฟล์ใดๆ ต้องทำ 4 ขั้นตอนนี้ก่อนเสมอ:**

1. `find_symbol(name)` — หา definition ของ function/class ที่เกี่ยวข้อง
2. `find_references(symbol)` — หาทุกที่ที่ symbol ถูกใช้ใน codebase
3. `impact_analysis(symbol)` — ประเมินว่าถ้าแก้ X จะกระทบอะไรบ้าง
4. `search_codebase(pattern)` — หาไฟล์ที่เกี่ยวข้องทั้งหมด

**กฎบังคับ:**
- ❌ ห้ามแก้ไฟล์โดยไม่มี impact analysis ก่อน
- ❌ ห้ามอ่านทั้ง repo — อ่านเฉพาะไฟล์ที่ Serena ระบุว่า relevant
- ❌ ห้าม deploy ผ่าน Serena MCP
- ❌ ห้ามรัน destructive command
- ✅ Refactor ใหญ่ (>5 files) → QA Agent verify ก่อน merge
- ✅ Security-sensitive code (auth/secret/permission) → Security Agent ตรวจก่อน
- ✅ Library/dependency ใหม่ → R&D Agent ประเมิน adoption status ก่อน

**Output ที่ต้องการจาก Serena:**
```yaml
serena_result:
  symbols_found: []
  files_relevant: []
  impact_report:
    affected_files: []
    breaking_change: false
    risk_level: 1
  plan_approved: false
```"""

    execution_context = _build_execution_context(task)

    # Build attachments section
    attachments = task.get("attachments") or []
    attachments_section = ""
    if attachments:
        attachment_has_secrets = False
        lines = ["\n## Attachments\n"]
        for att in attachments:
            fn   = att.get("filename") or att.get("safe_filename", "?")
            ct   = att.get("content_type", "unknown")
            size = att.get("size", 0)
            path = att.get("stored_path", "")
            info = classify_attachment(fn, ct)
            lines.append(f"- **{fn}**")
            lines.append(f"  - content_type: {ct}")
            lines.append(f"  - size: {size} bytes")
            lines.append(f"  - stored_path: `{path}`")
            lines.append(f"  - category: {info['category']}")
            lines.append(f"  - analysis_mode: {info['analysis_mode']}")
            lines.append(f"  - recommended_agents: {', '.join(info['recommended_agents'])}")
            lines.append(f"  - recommended_skills: {', '.join(info['recommended_skills']) or '(none)'}")
        lines.append("\n## Attachment Context\n")
        for att in attachments:
            fn = att.get("filename") or att.get("safe_filename", "?")
            ctx_text, has_sec = _read_attachment_context(att)
            if has_sec:
                attachment_has_secrets = True
            lines.append(f"### {fn}")
            if has_sec:
                lines.append("> ⚠️ **Possible secret detected and masked** — กรุณาตรวจสอบก่อนแชร์")
            lines.append(f"```\n{ctx_text}\n```\n")
        if attachment_has_secrets:
            warnings.append("Possible secret detected and masked in attachment")
        attachments_section = "\n".join(lines)

    content = f"""# Task: {task_id}

## Intent
{task.get('intent', '')}

## Source
- source: {task.get('source', 'unknown')}
- user: {task.get('user', 'unknown')}
- target: {task.get('target', 'unknown')}
- risk: {task.get('risk', 1)}

## Agents
{agents_md}

## Skills
{skills_md}

## Context
Text: {inputs.get('text', '')}
Optimized Text: {inputs.get('optimized_text', inputs.get('text', ''))}

## Constraints
Environment: {constraints.get('environment', 'wsl')}
Mode: {constraints.get('mode', 'plan-only')}

## Workflow
{workflow_md}
{execution_context}
{observer_section}
{serena_section}
{rag_section}

## Skills Context
{skills_context if skills_context else '(no skill files loaded)'}

## Warnings
{warnings_md}

## Instructions
Follow AGENTS.md: Plan -> Build -> Verify -> Report.
Use Workflow-first, Agent-when-needed, Hybrid by design.
Respect Risk Policy and Approval Policy.
Log every tool call in tool_usage_log.
Respond in Thai, readable on mobile.
{attachments_section}"""
    export_path.write_text(content, encoding="utf-8")
    return export_path


class TaskRequest(BaseModel):
    task_id: str


@app.get("/health")
async def health():
    wf_index = _load_workflows_index()
    return {
        "status": "ok",
        "service": "worker",
        "version": "0.1.0",
        "hermes_cli": "available" if HERMES_CLI_PATH else "fallback-export",
        "agentuniverse_cli": "available" if AGENTUNIVERSE_CLI_PATH else "fallback-export",
        "workflows_loaded": len(wf_index.get("workflows", [])),
    }


@app.get("/workflows")
async def list_workflows():
    index = _load_workflows_index()
    return {
        "count": len(index.get("workflows", [])),
        "philosophy": index.get("philosophy", ""),
        "workflows": [
            {
                "id": wf["id"],
                "name": wf["name"],
                "mode": wf["mode"],
                "autonomy_level": wf["autonomy_level"],
                "risk_level": wf["risk_level"],
                "approval_required": wf["approval_required"],
                "steps": wf.get("steps", []),
            }
            for wf in index.get("workflows", [])
        ],
    }


@app.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    content = _load_workflow_md(workflow_id)
    steps = _get_workflow_steps(workflow_id)
    if "not found" in content:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return {"workflow_id": workflow_id, "steps": steps, "content": content}


def _sync_hermes_report(task_id: str, result: dict, agent_run_info: dict) -> None:
    """Copy hermes report data into result dict for _push_result sync."""
    result["final_report"] = agent_run_info.get("final_report")
    result["report_source"] = "hermes"
    result["report_saved_at"] = datetime.now(timezone.utc).isoformat()
    result["report_summary"] = agent_run_info.get("output_summary") or ""
    raw_vstat = agent_run_info.get("verification_status") or ""
    result["verification_status"] = normalize_verification_status(raw_vstat) or "UNKNOWN"
    result["issues_found"] = []
    result["recommendations"] = []
    result["next_actions"] = []


@app.post("/process-task")
async def process_task(req: TaskRequest):
    processed_at = datetime.now(timezone.utc).isoformat()

    # ── 1. Worker received ───────────────────────────────────────────────────
    await _push_progress(req.task_id, status="running", progress=10)
    await _push_agent_activity(
        req.task_id,
        current_agent="manager", speaker_agent="manager", working_agent="manager",
        current_step="Manager รับงานและกำลังจัดประเภท",
        active_agents=["manager"],
        event_agent="manager", event_role="speaker",
        event_action="task_received",
        event_message="Manager รับงานและกำลังจัดประเภท",
    )

    # ── 2. Fetch task from Mobile Gateway ───────────────────────────────────
    await _push_progress(req.task_id, progress=20, current_step="กำลังดึงรายละเอียด Task")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{MOBILE_GATEWAY_URL}/tasks/{req.task_id}")
    except httpx.ConnectError as e:
        logger.error("Cannot reach mobile-gateway: %s", e)
        await _push_progress(req.task_id, status="failed", current_step="เกิดข้อผิดพลาด")
        await _push_agent_activity(req.task_id, event_agent="manager", event_role="speaker",
                                   event_action="error", event_message=f"เชื่อมต่อ gateway ไม่ได้: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Cannot reach mobile-gateway at {MOBILE_GATEWAY_URL}: {e}",
        )
    except httpx.RequestError as e:
        logger.error("mobile-gateway request failed: %s", e)
        await _push_progress(req.task_id, status="failed", current_step="เกิดข้อผิดพลาด")
        await _push_agent_activity(req.task_id, event_agent="manager", event_role="speaker",
                                   event_action="error", event_message=str(e))
        raise HTTPException(status_code=502, detail=f"mobile-gateway request error: {e}")

    if resp.status_code == 404:
        await _push_progress(req.task_id, status="failed", current_step="ไม่พบ Task")
        raise HTTPException(
            status_code=404,
            detail=f"Task '{req.task_id}' not found in mobile-gateway",
        )
    if resp.status_code != 200:
        await _push_progress(req.task_id, status="failed", current_step="เกิดข้อผิดพลาด")
        raise HTTPException(
            status_code=502,
            detail=f"mobile-gateway returned {resp.status_code} for task {req.task_id}",
        )

    raw_task = resp.json()

    # ── 3. Normalize + load skills ───────────────────────────────────────────
    task = normalize_task(raw_task)
    task["processed_at"] = processed_at

    # Enhance agents + skills based on attachment file types
    if task.get("attachments"):
        task["agents"] = _enhance_agents_for_attachments(task.get("agents", []), task["attachments"])
        task["skills"] = _enhance_skills_for_attachments(task.get("skills", []), task["attachments"])
        logger.info("After attachment enhancement — agents=%s skills=%s", task["agents"], task["skills"])

    agents_list: List[str] = task["agents"]
    has_observer = "observer" in agents_list
    primary_worker = "observer" if has_observer else (agents_list[0] if agents_list else "manager")

    logger.info(
        "Processing task: %s agents=%s skills=%s risk=%s",
        req.task_id, agents_list, task["skills"], task["risk"],
    )

    await _push_progress(req.task_id, progress=40)
    if has_observer:
        await _push_agent_activity(
            req.task_id,
            current_agent="observer", speaker_agent="manager", working_agent="observer",
            current_step="Observer กำลังเตรียมตรวจ health service",
            active_agents=agents_list,
            event_agent="observer", event_role="worker",
            event_action="prepare_health_check",
            event_message="Observer กำลังเตรียมตรวจ health service",
        )
    else:
        await _push_agent_activity(
            req.task_id,
            current_agent="manager", working_agent="manager",
            current_step="Manager กำลังโหลด Agent, Skill และ Workflow",
            active_agents=agents_list,
            event_agent="manager", event_role="worker",
            event_action="load_skills",
            event_message="Manager กำลังโหลด Agent, Skill และ Workflow",
        )
    skills_context, warnings = load_skill_context(task["skills"])

    if HERMES_CLI_PATH:
        logger.info("Hermes CLI adapter not yet implemented — using export fallback")
    if AGENTUNIVERSE_CLI_PATH:
        logger.info("agentUniverse CLI adapter not yet implemented — using export fallback")

    # ── 3.5. RAG Wiki Lookup ─────────────────────────────────────────────────
    rag_results: Optional[List[dict]] = None
    if any(s in task["skills"] for s in ("llm-wiki", "rag-ingest")):
        await _push_progress(req.task_id, current_step="ค้นหา LLM Wiki ผ่าน RAG...")
        await _push_agent_activity(
            req.task_id,
            current_agent="rag-curator", working_agent="rag-curator",
            current_step="ค้นหา LLM Wiki จาก docs/wiki ผ่าน RAG",
            active_agents=agents_list,
            event_agent="rag-curator", event_role="worker",
            event_action="rag_lookup_started",
            event_message="กำลังค้น LLM Wiki จาก docs/wiki ผ่าน RAG",
        )
        raw_query = (
            task.get("inputs", {}).get("optimized_text")
            or task.get("inputs", {}).get("text", "")
        ).strip()
        queries = _build_rag_queries(raw_query)
        logger.info(
            "RAG multi-query for task %s: %d queries — %s",
            req.task_id, len(queries), queries[:4],
        )
        rag_results, rag_error = await _rag_wiki_search_multi(queries)
        if rag_error and not rag_results:
            warnings.append(f"RAG search failed: {rag_error}")
            logger.warning("RAG search failed for task %s: %s", req.task_id, rag_error)
            await _push_agent_activity(
                req.task_id,
                event_agent="rag-curator", event_role="worker",
                event_action="rag_lookup_failed",
                event_message=f"ค้น LLM Wiki ไม่สำเร็จ: {rag_error}",
            )
            rag_results = []
        else:
            if not rag_results:
                warnings.append("No relevant wiki results found")
            await _push_agent_activity(
                req.task_id,
                event_agent="rag-curator", event_role="worker",
                event_action="rag_lookup_completed",
                event_message=f"ค้น LLM Wiki สำเร็จ พบ {len(rag_results)} รายการ จาก {len(queries)} queries",
            )
        logger.info("RAG lookup: %d results for task %s", len(rag_results), req.task_id)

    # ── 4. Build context ─────────────────────────────────────────────────────
    await _push_progress(req.task_id, progress=60)
    await _push_agent_activity(
        req.task_id,
        current_agent=primary_worker, working_agent=primary_worker,
        current_step=f"กำลังรวม Context สำหรับ Agent",
        event_agent=primary_worker, event_role="worker",
        event_action="build_context",
        event_message="กำลังรวม Context สำหรับ Agent",
    )

    # ── 5. Export prompt ─────────────────────────────────────────────────────
    await _push_progress(req.task_id, status="exporting", progress=80)
    await _push_agent_activity(
        req.task_id,
        current_agent="manager", working_agent="worker",
        current_step="Worker กำลังสร้าง Prompt สำหรับ Agent",
        event_agent="worker", event_role="worker",
        event_action="export_prompt",
        event_message="Worker กำลังสร้าง Prompt สำหรับ Agent",
    )
    try:
        export_path = _export_prompt(task, skills_context, warnings, rag_results=rag_results)
    except Exception as e:
        logger.error("Export prompt failed: %s", e)
        await _push_progress(req.task_id, status="failed", current_step="เกิดข้อผิดพลาด")
        await _push_agent_activity(req.task_id, event_agent="worker", event_role="worker",
                                   event_action="export_failed", event_message=str(e))
        await _push_result(req.task_id, {"error": str(e), "processed_at": processed_at})
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")

    logger.info("Task exported: %s  warnings=%d", export_path, len(warnings))

    # Fire attachment_context_built event if task has attachments
    if task.get("attachments"):
        await _push_agent_activity(
            req.task_id,
            event_agent="worker", event_role="worker",
            event_action="attachment_context_built",
            event_message=f"สร้าง Attachment Context จาก {len(task['attachments'])} ไฟล์แล้ว",
        )

    bridge = "hermes" if HERMES_CLI_PATH else ("agentuniverse" if AGENTUNIVERSE_CLI_PATH else "local-export")
    result = {
        "export_path": str(export_path),
        "agents": agents_list,
        "skills": task["skills"],
        "warnings": warnings,
        "bridge": bridge,
        "processed_at": processed_at,
        "rag_results_count": len(rag_results) if rag_results is not None else 0,
        "rag_top_path": rag_results[0].get("path", "") if rag_results else "",
        "agent_run_id": None,
        "agent_run_status": None,
        "agent_run_mode": None,
        "approval_required": False,
        "approval_phrase": None,
        "agent_approval_reason": None,
    }

    # ── 5.5. Agent Runner ────────────────────────────────────────────────────
    if AGENT_RUNNER_ENABLED:
        task_for_runner = {**task, "job_id": req.task_id}
        gate = _can_run_agent(task_for_runner, AGENT_RUNNER_MODE)

        await _push_agent_activity(
            req.task_id,
            event_agent="agent-runner", event_role="worker",
            event_action="agent_runner_gate_checked",
            event_message=f"ตรวจสอบ approval gate: allowed={gate['allowed']} — {gate['reason']}",
        )

        if not gate["allowed"]:
            result["agent_run_status"] = "blocked_approval_required"
            result["approval_required"] = True
            result["approval_phrase"] = gate["approval_phrase"]
            result["agent_approval_reason"] = gate["reason"]
            warnings.append(f"Agent Runner blocked: {gate['reason']}")
            await _push_agent_activity(
                req.task_id,
                event_agent="agent-runner", event_role="worker",
                event_action="agent_runner_blocked_approval_required",
                event_message=f"Agent Runner ถูก block — {gate['reason']} (phrase required: {gate['approval_phrase']})",
            )
            logger.info(
                "Agent runner BLOCKED for task %s: %s (phrase=%s)",
                req.task_id, gate["reason"], gate["approval_phrase"],
            )
        else:
            agent_run_info = await run_agent(task_for_runner, rag_results, _push_agent_activity)
            result["agent_run_id"] = agent_run_info.get("agent_run_id")
            result["agent_run_status"] = agent_run_info.get("agent_run_status")
            result["agent_run_mode"] = agent_run_info.get("agent_run_mode")
            result["agent_prompt_path"] = agent_run_info.get("agent_prompt_path")
            for _f in ("fallback_mode", "fallback_reason", "hermes_endpoint",
                       "hermes_http_status", "hermes_response_format", "response_received_at"):
                _v = agent_run_info.get(_f)
                if _v is not None:
                    result[_f] = _v
            logger.info(
                "Agent runner: run_id=%s status=%s fallback=%s",
                result["agent_run_id"],
                result["agent_run_status"],
                agent_run_info.get("fallback_mode"),
            )

            # ── Hermes auto-report: sync task to completed ───────────────────
            if agent_run_info.get("final_report") and result["agent_run_status"] == "completed_report_saved":
                _sync_hermes_report(req.task_id, result, agent_run_info)

    # ── 6. Done ──────────────────────────────────────────────────────────────
    hermes_completed = (
        AGENT_RUNNER_ENABLED
        and result.get("agent_run_status") == "completed_report_saved"
        and result.get("final_report")
    )
    if hermes_completed:
        # Task already completed via hermes auto-report
        final_step = "Hermes ประมวลผลเสร็จแล้ว — มี Final Report"
        await _push_progress(req.task_id, status="completed", progress=100, current_step=final_step)
        await _push_agent_activity(
            req.task_id,
            current_agent="manager", speaker_agent="manager",
            working_agent="",
            current_step=final_step,
            event_agent="manager", event_role="speaker",
            event_action="task_completed_from_hermes",
            event_message=final_step,
        )
    else:
        final_step = (
            "Prompt exported — รอ Agent processing"
            if bridge == "local-export"
            else "Export Prompt สำเร็จ"
        )
        await _push_progress(req.task_id, status="exported", progress=100)
        await _push_agent_activity(
            req.task_id,
            current_agent="manager", speaker_agent="manager",
            working_agent="",
            current_step=final_step,
            event_agent="manager", event_role="speaker",
            event_action="task_complete",
            event_message=final_step,
        )
    await _push_result(req.task_id, result)

    return {
        "task_id": req.task_id,
        "status": "exported",
        "export_path": str(export_path),
        "agents": task["agents"],
        "skills": task["skills"],
        "warnings": warnings,
        "bridge": bridge,
        "processed_at": processed_at,
        "agent_run_id": result.get("agent_run_id"),
        "agent_run_status": result.get("agent_run_status"),
        "agent_run_mode": result.get("agent_run_mode"),
        "agent_prompt_path": result.get("agent_prompt_path"),
    }


@app.get("/exports/{task_id}")
async def get_export(task_id: str):
    export_path = EXPORTS_DIR / f"{task_id}.prompt.md"
    if not export_path.exists():
        raise HTTPException(status_code=404, detail=f"Export for task '{task_id}' not found")
    content = export_path.read_text(encoding="utf-8")
    return {
        "task_id": task_id,
        "export_path": str(export_path),
        "content": content,
    }


@app.get("/skills")
async def list_skills():
    return _load_skills_index()


@app.get("/skills/{skill_id}")
async def get_skill(skill_id: str):
    content = _load_skill_md(skill_id)
    return {"skill_id": skill_id, "content": content}


class AgentReportRequest(BaseModel):
    report_source: str = "manual"
    final_report: str
    verification_status: Optional[str] = None
    summary: Optional[str] = None
    issues_found: Optional[List[str]] = []
    recommendations: Optional[List[str]] = []
    next_actions: Optional[List[str]] = []


class AgentStatusRequest(BaseModel):
    status: str
    error_message: Optional[str] = None


@app.get("/agent-runs")
async def get_agent_runs():
    runs = list_agent_runs()
    return {"count": len(runs), "runs": runs}


@app.get("/agent-runs/{run_id}")
async def get_agent_run(run_id: str):
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Agent run '{run_id}' not found")
    return run


@app.get("/jobs/{job_id}/agent-runs")
async def get_job_agent_runs(job_id: str):
    runs = get_runs_for_job(job_id)
    return {"job_id": job_id, "count": len(runs), "runs": runs}


@app.get("/agent-runs/{run_id}/prompt")
async def get_agent_run_prompt(run_id: str):
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Agent run '{run_id}' not found")
    prompt_path = run.get("prompt_path", "")
    if not prompt_path:
        raise HTTPException(status_code=404, detail=f"No prompt file for run '{run_id}'")
    p = Path(prompt_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Prompt file not found: {prompt_path}")
    return {"run_id": run_id, "prompt_path": prompt_path, "content": p.read_text(encoding="utf-8")}


@app.patch("/agent-runs/{run_id}/status")
async def update_agent_run_status_endpoint(run_id: str, req: AgentStatusRequest):
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Agent run '{run_id}' not found")
    update_agent_run(run_id, status=req.status, error_message=req.error_message or "")
    return {"run_id": run_id, "status": req.status}


@app.post("/agent-runs/{run_id}/report")
async def save_agent_run_report(run_id: str, req: AgentReportRequest):
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Agent run '{run_id}' not found")

    now = datetime.now(timezone.utc).isoformat()
    vstat = normalize_verification_status(req.verification_status or "")
    art = Path(AGENT_RUNNER_ARTIFACT_DIR)
    art.mkdir(parents=True, exist_ok=True)

    report_md_path = art / f"{run_id}.report.md"
    report_json_path = art / f"{run_id}.report.json"

    report_md_path.write_text(req.final_report, encoding="utf-8")
    report_json_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "job_id": run.get("job_id"),
                "report_source": req.report_source,
                "verification_status": vstat,
                "summary": req.summary or "",
                "issues_found": req.issues_found or [],
                "recommendations": req.recommendations or [],
                "next_actions": req.next_actions or [],
                "report_saved_at": now,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    update_agent_run(
        run_id,
        status="completed_report_saved",
        output_summary=req.summary or req.final_report[:200],
        report_path=str(report_md_path),
        report_saved_at=now,
        verification_status=vstat,
        error_message="",
    )
    logger.info("Agent run %s report saved (verification=%s)", run_id, vstat)

    job_id = run.get("job_id", "")
    if job_id:
        await _push_agent_activity(
            job_id,
            event_agent="agent-runner", event_role="worker",
            event_action="agent_report_received",
            event_message=f"รับ report จาก {req.report_source}",
        )
        await _push_agent_activity(
            job_id,
            event_agent="agent-runner", event_role="worker",
            event_action="agent_report_saved",
            event_message=f"บันทึก report แล้ว — verification={req.verification_status or 'none'}",
        )
        await _push_result(
            job_id,
            {
                "final_report": req.final_report,
                "report_source": req.report_source,
                "report_saved_at": now,
                "report_summary": req.summary or "",
                "verification_status": vstat,
                "issues_found": req.issues_found or [],
                "recommendations": req.recommendations or [],
                "next_actions": req.next_actions or [],
                "agent_run_id": run_id,
                "agent_run_status": "completed_report_saved",
            },
        )
        await _push_progress(
            job_id,
            status="completed",
            progress=100,
            current_step="Agent Run Report บันทึกแล้ว",
        )
        await _push_agent_activity(
            job_id,
            current_agent="manager", speaker_agent="manager",
            working_agent="",
            event_agent="manager", event_role="speaker",
            event_action="task_completed_from_agent_report",
            event_message="Task เสร็จสมบูรณ์จาก Agent Run Report",
        )

    return {
        "run_id": run_id,
        "status": "completed_report_saved",
        "report_path": str(report_md_path),
        "verification_status": vstat,
        "job_id": job_id,
    }


@app.post("/agent-runs/from-task/{task_id}")
async def run_agent_from_task(task_id: str):
    if not AGENT_RUNNER_ENABLED:
        raise HTTPException(status_code=400, detail="Agent Runner is disabled")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{MOBILE_GATEWAY_URL}/tasks/{task_id}")
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
            resp.raise_for_status()
            task = resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot reach mobile-gateway: {e}")

    gate = _can_run_agent(task, AGENT_RUNNER_MODE)
    if not gate["allowed"]:
        raise HTTPException(
            status_code=403,
            detail=f"Agent Runner blocked: {gate['reason']} (phrase required: {gate['approval_phrase']})",
        )

    # Re-run RAG for additional context
    task_text = (task.get("inputs") or {}).get("text", "") or task.get("intent", "")
    rag_results: List[dict] = []
    if task_text:
        try:
            queries = _build_rag_queries(task_text)
            rag_results, _ = await _rag_wiki_search_multi(queries)
        except Exception:
            pass

    await _push_agent_activity(
        task_id,
        event_agent="agent-runner", event_role="worker",
        event_action="agent_runner_gate_checked",
        event_message=f"gate re-checked after approval: allowed (approval_status={task.get('approval_status', 'none')})",
    )
    await _push_agent_activity(
        task_id,
        event_agent="agent-runner", event_role="worker",
        event_action="agent_runner_started_after_approval",
        event_message="Agent Runner เริ่มทำงานหลังได้รับ approval",
    )

    task_for_runner = {**task, "job_id": task_id}
    agent_run_info = await run_agent(task_for_runner, rag_results, _push_agent_activity)

    logger.info(
        "Agent runner from-task: task=%s run_id=%s status=%s fallback=%s",
        task_id, agent_run_info.get("agent_run_id"), agent_run_info.get("agent_run_status"),
        agent_run_info.get("fallback_mode"),
    )

    # Hermes auto-report: sync task to completed
    if agent_run_info.get("final_report") and agent_run_info.get("agent_run_status") == "completed_report_saved":
        hermes_result: dict = {
            "agent_run_id": agent_run_info.get("agent_run_id"),
            "agent_run_status": agent_run_info.get("agent_run_status"),
        }
        for _f in ("fallback_mode", "fallback_reason", "hermes_endpoint",
                   "hermes_http_status", "hermes_response_format", "response_received_at"):
            _v = agent_run_info.get(_f)
            if _v is not None:
                hermes_result[_f] = _v
        _sync_hermes_report(task_id, hermes_result, agent_run_info)
        await _push_result(task_id, hermes_result)
        await _push_progress(
            task_id, status="completed", progress=100,
            current_step="Hermes ประมวลผลเสร็จแล้ว — มี Final Report",
        )
        await _push_agent_activity(
            task_id,
            current_agent="manager", speaker_agent="manager",
            working_agent="",
            event_agent="manager", event_role="speaker",
            event_action="task_completed_from_hermes",
            event_message="Task เสร็จสมบูรณ์จาก Hermes HTTP Response (after approval)",
        )

    return {
        "task_id": task_id,
        "agent_run_id": agent_run_info.get("agent_run_id"),
        "agent_run_status": agent_run_info.get("agent_run_status"),
        "agent_run_mode": agent_run_info.get("agent_run_mode"),
        "agent_prompt_path": agent_run_info.get("agent_prompt_path"),
        "final_report": agent_run_info.get("final_report"),
        "verification_status": agent_run_info.get("verification_status"),
        "fallback_mode": agent_run_info.get("fallback_mode"),
    }
