"""FastAPI entrypoint — universal webhook to Telegram gateway."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from jinja2 import Template
from sqlalchemy import desc, select

from .config import Integration, load_integrations
from .db import WebhookLog, get_session, init_db
from .signatures import verify_github, verify_hmac_sha256, verify_stripe
from .telegram import send_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bridge")

INTEGRATIONS: dict[str, Integration] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    for integ in load_integrations():
        INTEGRATIONS[integ.name] = integ
        log.info("Loaded integration: %s -> %s", integ.name, integ.path)
    yield


app = FastAPI(title="Telegram Webhook Bridge", version="1.0.0", lifespan=lifespan)


@app.get("/healthz")
async def health():
    return {"status": "ok", "integrations": list(INTEGRATIONS.keys())}


def _verify_signature(integ: Integration, body: bytes, headers) -> bool:
    if integ.signature_method == "none":
        return True
    if not integ.signing_secret:
        return False
    if integ.signature_method == "hmac":
        return verify_hmac_sha256(integ.signing_secret, body, headers.get("x-signature", ""))
    if integ.signature_method == "github":
        return verify_github(integ.signing_secret, body, headers.get("x-hub-signature-256"))
    if integ.signature_method == "stripe":
        return verify_stripe(integ.signing_secret, body, headers.get("stripe-signature"))
    return False


def _extract_event_type(integration_name: str, payload: dict, headers) -> str:
    # GitHub events come via header
    if integration_name == "github":
        return headers.get("x-github-event", "unknown")
    # Stripe and most modern webhooks use "type" or "event"
    return payload.get("type") or payload.get("event") or "unknown"


def _render_message(integ: Integration, event_type: str, payload: dict) -> str:
    template_str = integ.templates.get(event_type) or integ.default_template
    template = Template(template_str)
    return template.render(name=integ.name, event=event_type, data=payload,
                           summary=json.dumps(payload, indent=2)[:800])


@app.post("/hook/{name}")
async def webhook(name: str, request: Request, x_idempotency_key: str | None = Header(default=None)):
    integ = INTEGRATIONS.get(name)
    if integ is None:
        raise HTTPException(404, f"Unknown integration: {name}")

    body = await request.body()
    if not _verify_signature(integ, body, request.headers):
        log.warning("Signature failed for %s", name)
        raise HTTPException(401, "Signature verification failed")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")

    event_type = _extract_event_type(name, payload, request.headers)

    if integ.events_allowlist and event_type not in integ.events_allowlist:
        return {"status": "ignored", "reason": f"event {event_type} not in allowlist"}

    message = _render_message(integ, event_type, payload)
    ok, info = await send_message(integ.telegram_chat_id, message)

    async with get_session() as session:
        session.add(WebhookLog(
            integration_name=name,
            event_type=event_type,
            status="delivered" if ok else "failed",
            payload=body.decode("utf-8", errors="replace"),
            error=None if ok else info,
        ))
        await session.commit()

    if not ok:
        return JSONResponse({"status": "failed", "error": info}, status_code=502)
    return {"status": "delivered"}


@app.get("/admin/logs")
async def list_logs(limit: int = 100, name: str | None = None):
    async with get_session() as session:
        q = select(WebhookLog).order_by(desc(WebhookLog.received_at)).limit(limit)
        if name:
            q = q.where(WebhookLog.integration_name == name)
        rows = (await session.execute(q)).scalars().all()
        return [{
            "id": r.id,
            "integration": r.integration_name,
            "event": r.event_type,
            "status": r.status,
            "received_at": r.received_at.isoformat(),
            "error": r.error,
        } for r in rows]
