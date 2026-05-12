import os
import hmac
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="Webhook Gateway", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return True
    expected = "sha256=" + hmac.new(secret.encode(), payload, digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "webhook-gateway", "version": "0.1.0"}


@app.post("/webhooks/activepieces")
async def webhook_activepieces(
    request: Request,
    x_ap_signature: Optional[str] = Header(None),
):
    payload = await request.body()

    if WEBHOOK_SECRET:
        if not x_ap_signature:
            raise HTTPException(status_code=401, detail="Missing X-AP-Signature header")
        if not _verify_signature(payload, x_ap_signature, WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        body = await request.json()
    except Exception:
        body = {"raw": payload.decode("utf-8", errors="replace")}

    logger.info("Activepieces webhook received: %s", str(body)[:200])

    return {
        "received": True,
        "source": "activepieces",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_keys": list(body.keys()) if isinstance(body, dict) else [],
    }


@app.post("/webhooks/github")
async def webhook_github(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
):
    payload = await request.body()

    if WEBHOOK_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")
        if not _verify_signature(payload, x_hub_signature_256, WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid GitHub signature")

    try:
        body = await request.json()
    except Exception:
        body = {}

    event_type = x_github_event or "unknown"
    repo = body.get("repository", {}).get("full_name", "unknown")
    logger.info("GitHub webhook: event=%s repo=%s", event_type, repo)

    return {
        "received": True,
        "source": "github",
        "event": event_type,
        "repository": repo,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
