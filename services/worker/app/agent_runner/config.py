import os

AGENT_RUNNER_ENABLED: bool = os.getenv("AGENT_RUNNER_ENABLED", "false").lower() == "true"
AGENT_RUNNER_MODE: str = os.getenv("AGENT_RUNNER_MODE", "prompt_only")
HERMES_API_URL: str = os.getenv("HERMES_API_URL", "")
HERMES_API_KEY: str = os.getenv("HERMES_API_KEY", "")
HERMES_TIMEOUT_MS: int = int(os.getenv("HERMES_TIMEOUT_MS", "120000"))
AGENT_RUNNER_ARTIFACT_DIR: str = os.getenv("AGENT_RUNNER_ARTIFACT_DIR", "/app/data/agent-runs")
AGENT_RUNS_FILE: str = os.getenv("AGENT_RUNS_FILE", "/app/data/agent-runs.json")
