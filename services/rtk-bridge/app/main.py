import os
import re
import logging
import subprocess
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="RTK Bridge", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

RTK_CLI_PATH = os.getenv("RTK_CLI_PATH", "")
ALLOW_RUN_COMMAND = os.getenv("RTK_ALLOW_RUN_COMMAND", "false").lower() == "true"
WORKSPACE = os.getenv("RTK_WORKSPACE", "/workspace")

BLOCKED_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+\*",
    r"rm\s+-rf\s+~",
    r"mkfs",
    r"dd\s+if=",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bhalt\b",
    r"DROP\s+DATABASE",
    r"DROP\s+TABLE",
    r"docker\s+volume\s+rm",
    r"docker\s+system\s+prune",
    r"chmod\s+-R\s+777",
    r"chown\s+-R\s+root",
    r"iptables\s+-F",
    r"> /dev/sd",
    r"passwd\s+root",
    r"firewall-cmd\s+--complete-reload",
]

ALLOWED_COMMANDS = [
    "ls", "pwd", "cat", "head", "tail", "grep", "find", "echo",
    "wc", "diff", "mkdir", "touch", "cp", "mv", "python3",
    "docker ps", "docker logs", "docker stats", "docker inspect",
    "docker compose logs", "docker compose build",
    "git status", "git log", "git diff",
    "curl",
]

BLOCKED_PATH_PREFIXES = ["/etc", "/root", "/home", "/usr/bin", "/usr/sbin",
                          "/boot", "/sys", "/proc", "/bin", "/sbin"]


def _is_blocked(command: str) -> tuple[bool, str]:
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, f"Blocked pattern matched: {pattern}"
    for prefix in BLOCKED_PATH_PREFIXES:
        if prefix in command and not command.startswith("docker"):
            return True, f"Path restriction: {prefix} is not allowed"
    return False, ""


def _is_allowed(command: str) -> bool:
    cmd_lower = command.strip().lower()
    for allowed in ALLOWED_COMMANDS:
        if cmd_lower.startswith(allowed.lower()):
            return True
    return False


def _assess_risk(command: str) -> int:
    cmd_lower = command.lower()
    if any(k in cmd_lower for k in ["docker compose up", "docker compose down", "deploy"]):
        return 3
    if any(k in cmd_lower for k in ["docker compose build", "pip install", "mkdir", "cp", "mv"]):
        return 2
    return 1


def _plan_from_goal(goal: str) -> List[str]:
    goal_lower = goal.lower()
    if any(k in goal_lower for k in ["log", "ล็อก"]):
        return [f"docker logs aicc-rag-api --tail=100", "docker ps --format 'table {{.Names}}\\t{{.Status}}'"]
    if any(k in goal_lower for k in ["health", "สุขภาพ", "ตรวจ"]):
        return ["curl -sf http://127.0.0.1:8088/health", "curl -sf http://127.0.0.1:8090/health",
                "docker ps --format 'table {{.Names}}\\t{{.Status}}'"]
    if any(k in goal_lower for k in ["disk", "space", "พื้นที่"]):
        return ["df -h /", "docker system df"]
    return [f"ls -la {WORKSPACE}"]


class PlanRequest(BaseModel):
    goal: str
    workspace: str = WORKSPACE


class ValidateRequest(BaseModel):
    command: str
    workspace: str = WORKSPACE


class RunRequest(BaseModel):
    command: str
    workspace: str = WORKSPACE
    timeout_seconds: int = 30


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "rtk-bridge",
        "version": "0.1.0",
        "run_command_enabled": ALLOW_RUN_COMMAND,
        "rtk_cli": "available" if RTK_CLI_PATH else "fallback",
    }


@app.post("/plan-command")
async def plan_command(req: PlanRequest):
    planned = _plan_from_goal(req.goal)
    validated = []
    for cmd in planned:
        blocked, reason = _is_blocked(cmd)
        validated.append({
            "command": cmd,
            "is_safe": not blocked,
            "risk_level": _assess_risk(cmd) if not blocked else 5,
            "blocked_reason": reason if blocked else None,
        })
    return {
        "goal": req.goal,
        "planned_commands": validated,
        "workspace": req.workspace,
        "note": "Review and run each command individually via /validate-command",
    }


@app.post("/validate-command")
async def validate_command(req: ValidateRequest):
    blocked, reason = _is_blocked(req.command)
    if blocked:
        return {
            "command": req.command,
            "is_safe": False,
            "risk_level": 5,
            "blocked_reason": reason,
            "suggestions": ["Use a safer alternative or request approval"],
        }

    allowed = _is_allowed(req.command)
    risk = _assess_risk(req.command)

    return {
        "command": req.command,
        "is_safe": True,
        "is_in_allowlist": allowed,
        "risk_level": risk,
        "blocked_reason": None,
        "suggestions": [] if allowed else ["Command not in allowlist — review core/commands/command-allowlist.yaml"],
    }


@app.post("/run-command")
async def run_command(req: RunRequest):
    if not ALLOW_RUN_COMMAND:
        raise HTTPException(
            status_code=403,
            detail="run-command is disabled. Set RTK_ALLOW_RUN_COMMAND=true in dev environment only.",
        )

    blocked, reason = _is_blocked(req.command)
    if blocked:
        raise HTTPException(status_code=403, detail=f"Command blocked: {reason}")

    if not _is_allowed(req.command):
        raise HTTPException(status_code=403, detail="Command not in allowlist")

    if RTK_CLI_PATH:
        logger.info("RTK CLI adapter not yet implemented — using safe subprocess")

    try:
        result = subprocess.run(
            req.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=req.timeout_seconds,
            cwd=req.workspace if os.path.isdir(req.workspace) else "/tmp",
        )
        logger.info("RTK ran: %s exit=%d", req.command, result.returncode)
        return {
            "command": req.command,
            "exit_code": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
            "workspace": req.workspace,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
