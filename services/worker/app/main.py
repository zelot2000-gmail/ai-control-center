import os
import json
import logging
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="Worker Service", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

HERMES_CLI_PATH = os.getenv("HERMES_CLI_PATH", "")
AGENTUNIVERSE_CLI_PATH = os.getenv("AGENTUNIVERSE_CLI_PATH", "")
MOBILE_GATEWAY_URL = os.getenv("MOBILE_GATEWAY_URL", "http://mobile-gateway:8088")
EXPORTS_DIR = Path("/app/data/exports")
AGENTS_MD_PATH = Path("/app/AGENTS.md")
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


def _read_attachment_context(attachment: dict, max_chars: int = 3000) -> str:
    stored_path = attachment.get("stored_path", "")
    filename    = attachment.get("filename") or attachment.get("safe_filename", "")
    _, ext = os.path.splitext(filename)
    if ext.lower() not in _TEXT_EXTENSIONS:
        return f"(binary file — {attachment.get('content_type', 'unknown type')} — cannot read as text)"
    try:
        p = Path(stored_path)
        if not p.exists():
            return "(file not found on disk)"
        text = p.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...(truncated)"
        return text
    except Exception as e:
        return f"(error reading file: {e})"


def _export_prompt(task: dict, skills_context: str, warnings: List[str]) -> Path:
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

    execution_context = _build_execution_context(task)

    # Build attachments section
    attachments = task.get("attachments") or []
    attachments_section = ""
    if attachments:
        lines = ["\n## Attachments\n"]
        for att in attachments:
            fn   = att.get("filename") or att.get("safe_filename", "?")
            ct   = att.get("content_type", "unknown")
            size = att.get("size", 0)
            path = att.get("stored_path", "")
            lines.append(f"- **{fn}** | {ct} | {size} bytes | `{path}`")
            _, ext = os.path.splitext(fn)
            if ext.lower() == ".md":
                lines.append(f"  > 💡 ไฟล์นี้สามารถ ingest เข้า RAG ได้")
            elif ext.lower() in {".log"}:
                lines.append(f"  > 💡 แนะนำ: ใช้ observer/log-review-workflow")
            elif ext.lower() in {".yaml", ".yml"} and "compose" in fn.lower():
                lines.append(f"  > 💡 แนะนำ: ใช้ devops/docker-deploy skill")
        lines.append("\n## Attachment Context\n")
        for att in attachments:
            fn = att.get("filename") or att.get("safe_filename", "?")
            ctx_text = _read_attachment_context(att)
            lines.append(f"### {fn}\n```\n{ctx_text}\n```\n")
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
        export_path = _export_prompt(task, skills_context, warnings)
    except Exception as e:
        logger.error("Export prompt failed: %s", e)
        await _push_progress(req.task_id, status="failed", current_step="เกิดข้อผิดพลาด")
        await _push_agent_activity(req.task_id, event_agent="worker", event_role="worker",
                                   event_action="export_failed", event_message=str(e))
        await _push_result(req.task_id, {"error": str(e), "processed_at": processed_at})
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")

    logger.info("Task exported: %s  warnings=%d", export_path, len(warnings))

    bridge = "hermes" if HERMES_CLI_PATH else ("agentuniverse" if AGENTUNIVERSE_CLI_PATH else "local-export")
    result = {
        "export_path": str(export_path),
        "agents": agents_list,
        "skills": task["skills"],
        "warnings": warnings,
        "bridge": bridge,
        "processed_at": processed_at,
    }

    # ── 6. Done ──────────────────────────────────────────────────────────────
    final_step = (
        "Prompt exported — รอ Agent processing"
        if bridge == "local-export"
        else "Export Prompt สำเร็จ"
    )
    await _push_progress(req.task_id, status="exported", progress=100)
    await _push_agent_activity(
        req.task_id,
        current_agent="manager", speaker_agent="manager",
        working_agent="",          # clear active worker
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
