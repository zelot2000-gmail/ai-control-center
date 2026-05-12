import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="Observer Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

SERVICES = {
    "mobile-gateway": os.getenv("MOBILE_GATEWAY_URL", "http://mobile-gateway:8088"),
    "rag-api": os.getenv("RAG_API_URL", "http://rag-api:8090"),
    "tto-api": os.getenv("TTO_API_URL", "http://tto-api:8091"),
    "rtk-bridge": os.getenv("RTK_BRIDGE_URL", "http://rtk-bridge:8092"),
    "webhook-gateway": os.getenv("WEBHOOK_GATEWAY_URL", "http://webhook-gateway:8093"),
    "worker": os.getenv("WORKER_URL", "http://worker:8095"),
}

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")


async def _check_service(name: str, base_url: str, timeout: float = 3.0) -> dict:
    endpoint = f"{base_url}/health"
    if name == "qdrant-healthz":
        endpoint = f"{base_url}/healthz"
    start = asyncio.get_event_loop().time()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(endpoint)
            latency_ms = round((asyncio.get_event_loop().time() - start) * 1000, 1)
            return {
                "status": "up" if resp.status_code == 200 else "degraded",
                "http_status": resp.status_code,
                "latency_ms": latency_ms,
            }
    except Exception as e:
        return {"status": "down", "error": str(e)[:100], "latency_ms": None}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "observer", "version": "0.1.0"}


@app.get("/status")
async def status():
    check_list = list(SERVICES.items()) + [("qdrant", QDRANT_URL)]
    names = [name for name, _ in check_list]
    coros = [_check_service(name if name != "qdrant" else "qdrant-healthz", url) for name, url in check_list]

    checks = await asyncio.gather(*coros, return_exceptions=False)
    results = dict(zip(names, checks))

    all_up = all(r["status"] == "up" for r in results.values())
    degraded = [name for name, r in results.items() if r["status"] != "up"]

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall": "ok" if all_up else "degraded",
        "degraded_services": degraded,
        "services": results,
    }


@app.get("/service-health")
async def service_health():
    check_list = list(SERVICES.items()) + [("qdrant", QDRANT_URL)]
    names = [name for name, _ in check_list]
    coros = [_check_service(name if name != "qdrant" else "qdrant-healthz", url) for name, url in check_list]
    results = await asyncio.gather(*coros, return_exceptions=False)
    return dict(zip(names, results))


@app.get("/docker-summary")
async def docker_summary():
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True, text=True, timeout=10,
        )
        lines = result.stdout.strip().split("\n") if result.stdout else []
        containers = []
        for line in lines[1:]:
            parts = line.split("\t")
            containers.append({
                "name": parts[0].strip() if len(parts) > 0 else "",
                "status": parts[1].strip() if len(parts) > 1 else "",
                "ports": parts[2].strip() if len(parts) > 2 else "",
            })
        return {
            "containers": containers,
            "total": len(containers),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "note": "docker command may not be available inside container"}
