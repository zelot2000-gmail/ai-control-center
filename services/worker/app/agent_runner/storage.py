import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from .config import AGENT_RUNS_FILE
from .types import AgentRun

logger = logging.getLogger(__name__)


def _load() -> dict:
    p = Path(AGENT_RUNS_FILE)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Failed to load agent-runs.json: %s", e)
            return {}
    return {}


def _save(runs: dict) -> None:
    p = Path(AGENT_RUNS_FILE)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(runs, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def save_run(run: AgentRun) -> None:
    runs = _load()
    runs[run.id] = run.to_dict()
    _save(runs)


def get_run(run_id: str) -> Optional[dict]:
    return _load().get(run_id)


def list_runs() -> List[dict]:
    return list(_load().values())


def get_runs_for_job(job_id: str) -> List[dict]:
    return [r for r in _load().values() if r.get("job_id") == job_id]


def update_run(run_id: str, **kwargs) -> Optional[dict]:
    runs = _load()
    if run_id not in runs:
        return None
    runs[run_id].update(kwargs)
    runs[run_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save(runs)
    return runs[run_id]
