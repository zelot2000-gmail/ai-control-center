import os
import re
import uuid
import json
import logging
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Header, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="Mobile Gateway", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

TTO_URL = os.getenv("TTO_URL", "http://tto-api:8091")
ENVIRONMENT = os.getenv("ENVIRONMENT", "wsl")
GATEWAY_SECRET = os.getenv("MOBILE_GATEWAY_SECRET", "")

TASKS_FILE   = "/app/data/tasks.json"
UPLOADS_DIR  = Path("/app/data/uploads")

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {
    # text
    ".txt", ".md", ".log", ".json", ".yaml", ".yml", ".csv",
    # document
    ".pdf", ".doc", ".docx",
    # spreadsheet
    ".xls", ".xlsx",
    # presentation
    ".ppt", ".pptx",
    # image
    ".jpg", ".jpeg", ".png", ".webp", ".gif",
}


def _require_secret(x_gateway_secret: Optional[str] = Header(None)):
    if GATEWAY_SECRET and x_gateway_secret != GATEWAY_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing X-Gateway-Secret")


def _load_tasks() -> dict:
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_tasks(tasks: dict):
    os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2, default=str)


def _assess_risk(text: str, target: str, environment: str) -> int:
    text_lower = text.lower()
    if environment == "production":
        if any(k in text_lower for k in ["deploy", "delete", "remove", "drop", "destroy"]):
            return 5
        if any(k in text_lower for k in ["restart", "rebuild", "update"]):
            return 4
        return 3
    if any(k in text_lower for k in ["delete", "remove", "drop", "destroy", "rm -rf"]):
        return 5
    if any(k in text_lower for k in ["deploy", "production"]):
        return 4
    if any(k in text_lower for k in ["restart", "rebuild", "staging"]):
        return 3
    if any(k in text_lower for k in ["write", "create", "edit", "fix", "build"]):
        return 2
    return 1


# Supported command sources: dashboard | mobile | chatgpt | chatgpt-mobile | webhook | manual | activepieces
_VALID_SOURCES = {
    "dashboard", "mobile", "chatgpt", "chatgpt-mobile",
    "webhook", "manual", "activepieces", "unknown",
}

_WIKI_KEYWORDS = [
    "llm wiki", "wiki", "docs/wiki", "sop", "adr",
    "knowledge base", "knowledge", "ความรู้", "เอกสารระบบ",
    "serena mcp ต่างจาก rag", "ต่างจาก rag",
]

_CODE_INTEL_KEYWORDS = [
    "serena", "code intelligence", "refactor", "impact analysis",
    "code review", "วิเคราะห์ code", "serena mcp",
]


def _select_agents(text: str) -> List[str]:
    text_lower = text.lower()
    agents = ["manager"]
    if any(k in text_lower for k in ["โค้ด", "code", "fix", "bug", "api", "เขียน"]):
        agents.append("programmer")
    if any(k in text_lower for k in ["docker", "deploy", "build", "container"]):
        agents.append("devops")
    if any(k in text_lower for k in ["ตรวจ", "check", "health", "status", "log"]):
        agents.append("observer")
    if any(k in text_lower for k in ["ingest", "document", "rag", "search", "เอกสาร"]):
        agents.append("rag-curator")
    # Wiki/knowledge lookup → rag-curator + manager
    if any(k in text_lower for k in _WIKI_KEYWORDS):
        if "rag-curator" not in agents:
            agents.append("rag-curator")
    if any(k in text_lower for k in ["research", "ทดลอง", "poc", "r&d"]):
        agents.append("research")
    if any(k in text_lower for k in ["security", "secret", "permission"]):
        agents.append("security")
    if any(k in text_lower for k in ["backup", "ssl", "server", "cwp"]):
        agents.append("administrator")
    # Code intelligence: serena/refactor/impact analysis → programmer + qa
    if any(k in text_lower for k in _CODE_INTEL_KEYWORDS):
        if "programmer" not in agents:
            agents.append("programmer")
        if "qa" not in agents:
            agents.append("qa")
    return list(set(agents))


def _select_skills(agents: List[str], text: str = "") -> List[str]:
    skill_map = {
        "programmer": "programmer",
        "devops": "docker-deploy",
        "observer": "observer-monitor",
        "rag-curator": "rag-ingest",
        "research": "research-development",
        "security": "security-check",
        "administrator": "cwp-server-admin",
        "manager": "mobile-command",
        "qa": "qa-verify",
        "designer": "design-system",
    }
    skills = [skill_map[a] for a in agents if a in skill_map]
    text_lower = text.lower()
    # Add llm-wiki when wiki/knowledge keywords present
    if any(k in text_lower for k in _WIKI_KEYWORDS):
        if "llm-wiki" not in skills:
            skills.append("llm-wiki")
    # Add serena-mcp when code intelligence keywords present
    if any(k in text_lower for k in _CODE_INTEL_KEYWORDS):
        if "serena-mcp" not in skills:
            skills.append("serena-mcp")
    return skills


_WORKFLOW_KEYWORDS = [
    "health", "ตรวจ service", "docker ps", "backup", "ingest", "verify",
    "readiness", "lint", "test", "log collection", "สำรอง", "ตรวจสอบ service",
]
_AGENT_KEYWORDS = [
    "วิเคราะห์", "debug", "root cause", "ออกแบบ", "เปรียบเทียบ",
    "research", "r&d", "refactor", "investigate", "ทดลอง", "poc",
]
_HYBRID_KEYWORDS = [
    "deploy", "staging", "production", "restart", "ssl", "firewall",
    "database", "release", "rollout", "browser qa", "ui review",
    "refactor", "code intelligence", "serena", "impact analysis", "code review",
]
_WORKFLOW_MAP = {
    "ingest": "rag-ingest-workflow",
    "เอกสาร": "rag-ingest-workflow",
    "health": "docker-health-check-workflow",
    "ตรวจ service": "docker-health-check-workflow",
    "docker ps": "docker-health-check-workflow",
    "backup": "backup-workflow",
    "สำรอง": "backup-workflow",
    "browser qa": "browser-qa-workflow",
    "ui test": "browser-qa-workflow",
    "deploy": "deployment-workflow",
    "staging": "deployment-workflow",
    "security": "security-review-workflow",
    "log": "log-review-workflow",
    "rag quality": "rag-evaluation-workflow",
    "prod readiness": "prod-readiness-workflow",
    # code intelligence
    "serena mcp": "code-intelligence-workflow",
    "serena": "code-intelligence-workflow",
    "code intelligence": "code-intelligence-workflow",
    "refactor": "code-intelligence-workflow",
    "impact analysis": "code-intelligence-workflow",
    "code review": "code-intelligence-workflow",
    "วิเคราะห์ code": "code-intelligence-workflow",
    # wiki / knowledge lookup
    "llm wiki": "wiki-ingest-workflow",
    "wiki": "wiki-ingest-workflow",
    "ingest wiki": "wiki-ingest-workflow",
    "docs/wiki": "wiki-ingest-workflow",
    "sop": "wiki-ingest-workflow",
    "adr": "wiki-ingest-workflow",
    "ความรู้": "wiki-ingest-workflow",
    "เอกสารระบบ": "wiki-ingest-workflow",
}


def _classify_execution(text: str, risk: int) -> dict:
    t = text.lower()
    if risk >= 4:
        mode = "hybrid"
        autonomy = 5 if risk == 5 else 4
        reason = f"Risk level {risk} requires hybrid mode with approval"
    elif any(k in t for k in _CODE_INTEL_KEYWORDS):
        # Code intelligence always forces hybrid + code-intelligence-workflow
        mode = "hybrid"
        autonomy = 3
        reason = "Code intelligence task: Serena MCP + impact analysis required"
    elif any(k in t for k in _WIKI_KEYWORDS):
        # Wiki/knowledge lookup — workflow if simple, hybrid if analysis needed
        if any(k in t for k in _AGENT_KEYWORDS):
            mode = "hybrid"
            autonomy = 3
            reason = "Wiki knowledge task with analysis: RAG lookup + agent reasoning"
        else:
            mode = "workflow"
            autonomy = 2
            reason = "Wiki/knowledge lookup task: RAG search from docs/wiki"
    elif any(k in t for k in _HYBRID_KEYWORDS):
        mode = "hybrid"
        autonomy = 4 if "production" in t else 3
        reason = "Structured task with decision points requiring agent judgment"
    elif any(k in t for k in _AGENT_KEYWORDS):
        mode = "agent"
        autonomy = 3
        reason = "Open-ended task requiring dynamic reasoning"
    else:
        mode = "workflow"
        autonomy = 2 if risk >= 2 else 1
        reason = "Predictable task with defined steps"

    selected_workflow = None
    for keyword, wf_id in _WORKFLOW_MAP.items():
        if keyword in t:
            selected_workflow = wf_id
            break

    return {
        "mode": mode,
        "autonomy_level": autonomy,
        "selected_workflow": selected_workflow,
        "reason_for_mode": reason,
    }


class TaskRequest(BaseModel):
    source: str = "unknown"
    user: str = "unknown"
    text: str
    target_system: Optional[str] = None
    environment: str = "wsl"
    mode: str = "plan-only"
    attachments: Optional[List[dict]] = []


class ApprovalRequest(BaseModel):
    phrase: str
    approver: str = "unknown"


class StatusUpdateRequest(BaseModel):
    status: str


class ResultUpdateRequest(BaseModel):
    result: dict


class ProgressUpdateRequest(BaseModel):
    status: Optional[str] = None
    progress: Optional[int] = None
    current_step: Optional[str] = None
    step_name: Optional[str] = None
    step_status: Optional[str] = None


class AgentActivityEvent(BaseModel):
    agent: str
    role: str = "worker"
    action: str
    message: str = ""


class AgentActivityRequest(BaseModel):
    current_agent: Optional[str] = None
    speaker_agent: Optional[str] = None
    working_agent: Optional[str] = None
    current_step: Optional[str] = None
    active_agents: Optional[List[str]] = None
    event: Optional[AgentActivityEvent] = None


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mobile-gateway", "version": "0.1.0"}


@app.post("/uploads")
async def upload_file(file: UploadFile = File(...)):
    _, ext = os.path.splitext(file.filename or "")
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type '{ext}' not allowed")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(400, "File too large (max 10 MB)")

    safe_name = re.sub(r"[^a-zA-Z0-9._\-]", "_", os.path.basename(file.filename or "file"))
    file_id   = str(uuid.uuid4())
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    stored_path = UPLOADS_DIR / f"{file_id}_{safe_name}"
    stored_path.write_bytes(content)

    logger.info("Uploaded: %s (%d bytes) → %s", file.filename, len(content), stored_path)
    return {
        "file_id":      file_id,
        "filename":     file.filename,
        "safe_filename": safe_name,
        "content_type": file.content_type,
        "size":         len(content),
        "stored_path":  str(stored_path),
    }


@app.post("/tasks", dependencies=[Depends(_require_secret)])
async def create_task(req: TaskRequest):
    task_id = str(uuid.uuid4())
    optimized_text = req.text

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            tto_resp = await client.post(
                f"{TTO_URL}/optimize",
                json={"text": req.text},
            )
            if tto_resp.status_code == 200:
                optimized_text = tto_resp.json().get("optimized_text", req.text)
    except Exception as e:
        logger.warning("TTO unavailable, using raw text: %s", str(e))

    risk = _assess_risk(req.text, req.target_system or "", req.environment)
    agents = _select_agents(req.text)
    skills = _select_skills(agents, req.text)
    execution = _classify_execution(req.text, risk)

    status = "pending"
    approval_phrase = None
    if risk >= 3 and req.mode != "plan-only":
        status = "waiting_approval"
        approval_phrase = {3: "CONFIRM STAGING", 4: "CONFIRM DEPLOY", 5: "CONFIRM DANGEROUS"}.get(risk)

    task = {
        "task_id": task_id,
        "source": req.source,
        "user": req.user,
        "intent": optimized_text[:200],
        "target": req.target_system,
        "risk": risk,
        "agents": agents,
        "skills": skills,
        "inputs": {"text": req.text, "optimized_text": optimized_text},
        "constraints": {"environment": req.environment, "mode": req.mode},
        "workflow": ["plan", "build", "verify", "report"],
        "attachments": req.attachments or [],
        "required_output": "mobile-report",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "progress": 0,
        "current_step": "Task created",
        "steps": [{"name": "created", "label": "รับคำสั่งแล้ว", "progress": 0, "status": "done"}],
        "result": None,
        "current_agent": agents[0] if agents else "manager",
        "speaker_agent": "manager",
        "working_agent": None,
        "active_agents": ["manager"],
        "agent_events": [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": "manager",
                "role": "speaker",
                "action": "task_created",
                "message": "รับคำสั่งและสร้าง task แล้ว",
            },
            *[
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "agent": "worker",
                    "role": "worker",
                    "action": "file_uploaded",
                    "message": f"ไฟล์ {att.get('filename', att.get('safe_filename', '?'))} ถูกอัพโหลดเรียบร้อย ({att.get('size', 0)} bytes)",
                }
                for att in (req.attachments or [])
            ],
        ],
        "execution": execution,
        "accountability": {
            "owner_agent": agents[0] if agents else "manager",
            "responsible_agents": agents,
            "approver": None,
            "approval_required": status == "waiting_approval",
            "approval_phrase": approval_phrase,
            "decision_log": [],
            "tool_usage_log": [],
            "command_validation_log": [],
            "verification_log": [],
            "error_log": [],
            "rollback_required": False,
            "rollback_plan": None,
        },
    }

    tasks = _load_tasks()
    tasks[task_id] = task
    _save_tasks(tasks)

    logger.info(
        "Task created: %s risk=%d mode=%s workflow=%s agents=%s",
        task_id, risk, execution["mode"], execution.get("selected_workflow"), agents,
    )

    return {
        "task_id": task_id,
        "status": status,
        "risk_level": risk,
        "agents": agents,
        "skills": skills,
        "execution": execution,
        "approval_required": status == "waiting_approval",
        "approval_phrase": approval_phrase,
    }


@app.get("/tasks")
async def list_tasks():
    tasks = _load_tasks()
    return {"tasks": list(tasks.values()), "count": len(tasks)}


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    tasks = _load_tasks()
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]


@app.patch("/tasks/{task_id}/status")
async def update_task_status(task_id: str, req: StatusUpdateRequest):
    tasks = _load_tasks()
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    tasks[task_id]["status"] = req.status
    tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_tasks(tasks)
    logger.info("Task %s status → %s", task_id, req.status)
    return {"task_id": task_id, "status": req.status}


@app.patch("/tasks/{task_id}/result")
async def update_task_result(task_id: str, req: ResultUpdateRequest):
    tasks = _load_tasks()
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    existing = tasks[task_id].get("result") or {}
    existing.update(req.result)
    tasks[task_id]["result"] = existing
    tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_tasks(tasks)
    logger.info("Task %s result updated", task_id)
    return {"task_id": task_id, "result": req.result}


@app.patch("/tasks/{task_id}/progress")
async def update_task_progress(task_id: str, req: ProgressUpdateRequest):
    tasks = _load_tasks()
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    t = tasks[task_id]
    if req.status is not None:
        t["status"] = req.status
    if req.progress is not None:
        t["progress"] = req.progress
    if req.current_step is not None:
        t["current_step"] = req.current_step
    if req.step_name and req.step_status:
        steps = t.get("steps", [])
        for step in steps:
            if step["name"] == req.step_name:
                step["status"] = req.step_status
                if req.progress is not None:
                    step["progress"] = req.progress
                break
        else:
            steps.append({
                "name": req.step_name,
                "label": req.current_step or req.step_name,
                "progress": req.progress or 0,
                "status": req.step_status,
            })
        t["steps"] = steps
    t["updated_at"] = datetime.now(timezone.utc).isoformat()
    tasks[task_id] = t
    _save_tasks(tasks)
    logger.info("Task %s progress → %s%% status=%s", task_id, t.get("progress"), t.get("status"))
    return {"task_id": task_id, "status": t.get("status"), "progress": t.get("progress")}


@app.patch("/tasks/{task_id}/agent-activity")
async def update_agent_activity(task_id: str, req: AgentActivityRequest):
    tasks = _load_tasks()
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    t = tasks[task_id]
    if req.current_agent is not None:
        t["current_agent"] = req.current_agent
    if req.speaker_agent is not None:
        t["speaker_agent"] = req.speaker_agent
    if req.working_agent is not None:
        t["working_agent"] = req.working_agent if req.working_agent else None
    if req.current_step is not None:
        t["current_step"] = req.current_step
    if req.active_agents is not None:
        existing = set(t.get("active_agents") or [])
        existing.update(req.active_agents)
        t["active_agents"] = list(existing)
    if req.event is not None:
        events = t.get("agent_events") or []
        events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": req.event.agent,
            "role": req.event.role,
            "action": req.event.action,
            "message": req.event.message,
        })
        t["agent_events"] = events
    t["updated_at"] = datetime.now(timezone.utc).isoformat()
    tasks[task_id] = t
    _save_tasks(tasks)
    logger.info("Task %s agent-activity → current=%s", task_id, t.get("current_agent"))
    return {"task_id": task_id, "current_agent": t.get("current_agent")}


class SaveReportRequest(BaseModel):
    report: str
    report_source: str = "claude"  # claude | hermes | agentuniverse | manual
    report_summary: Optional[str] = None
    verification_status: Optional[str] = None  # pass | warning | fail
    issues_found: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    next_actions: Optional[List[str]] = None


@app.post("/tasks/{task_id}/run-agent")
async def run_agent_task(task_id: str):
    tasks = _load_tasks()
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    t = tasks[task_id]
    if t.get("status") not in ("exported",):
        raise HTTPException(
            status_code=400,
            detail=f"Task must be 'exported' to run agent (current: '{t.get('status')}')",
        )
    t["status"] = "agent_running"
    t["progress"] = 10
    t["current_step"] = "กำลังเตรียมส่ง Prompt ให้ Agent"
    events = t.get("agent_events") or []
    events.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "manager",
        "role": "speaker",
        "action": "agent_run_requested",
        "message": "Prompt พร้อมแล้ว กรุณา Copy ไปให้ Claude/Hermes ประมวลผล",
    })
    t["agent_events"] = events
    t["updated_at"] = datetime.now(timezone.utc).isoformat()
    tasks[task_id] = t
    _save_tasks(tasks)
    logger.info("Task %s agent_run_requested (fallback-manual)", task_id)
    return {
        "task_id": task_id,
        "status": "agent_running",
        "bridge": "fallback-manual",
        "message": "กรุณา Copy Prompt ไปให้ Claude/Hermes ประมวลผล",
    }


@app.post("/tasks/{task_id}/save-report")
async def save_report(task_id: str, req: SaveReportRequest):
    tasks = _load_tasks()
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    t = tasks[task_id]
    if t.get("status") not in ("agent_running", "exported"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot save report when status is '{t.get('status')}'",
        )
    result = t.get("result") or {}
    result["final_report"] = req.report
    result["report_source"] = req.report_source
    result["report_saved_at"] = datetime.now(timezone.utc).isoformat()
    if req.report_summary is not None:
        result["report_summary"] = req.report_summary
    if req.verification_status is not None:
        result["verification_status"] = req.verification_status
    result["issues_found"] = req.issues_found or []
    result["recommendations"] = req.recommendations or []
    result["next_actions"] = req.next_actions or []
    t["result"] = result
    t["status"] = "completed"
    t["progress"] = 100
    t["current_step"] = "Agent ทำงานเสร็จแล้ว — มี Final Report"
    events = t.get("agent_events") or []
    now = datetime.now(timezone.utc).isoformat()
    events.append({
        "timestamp": now,
        "agent": req.report_source,
        "role": "worker",
        "action": "final_report_saved",
        "message": f"บันทึก Final Report จาก {req.report_source} แล้ว",
    })
    events.append({
        "timestamp": now,
        "agent": "system",
        "role": "system",
        "action": "task_completed",
        "message": f"Task เสร็จสมบูรณ์ — Final Report จาก {req.report_source}",
    })
    t["agent_events"] = events
    t["updated_at"] = datetime.now(timezone.utc).isoformat()
    tasks[task_id] = t
    _save_tasks(tasks)
    logger.info("Task %s completed — final_report saved from %s", task_id, req.report_source)
    return {
        "task_id": task_id,
        "status": "completed",
        "message": "บันทึก Final Report เรียบร้อย",
    }


@app.post("/approvals/{task_id}")
async def approve_task(task_id: str, req: ApprovalRequest):
    tasks = _load_tasks()
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]
    risk = task.get("risk", 1)
    required = {3: "CONFIRM STAGING", 4: "CONFIRM DEPLOY", 5: "CONFIRM DANGEROUS"}.get(risk, "")

    if req.phrase.strip() != required:
        raise HTTPException(status_code=403, detail=f"Invalid approval phrase. Required: {required}")

    task["status"] = "approved"
    task["approved_by"] = req.approver
    task["approved_at"] = datetime.now(timezone.utc).isoformat()
    tasks[task_id] = task
    _save_tasks(tasks)

    logger.info("Task approved: %s by %s", task_id, req.approver)
    return {"task_id": task_id, "status": "approved", "message": "Task approved and ready for execution"}
