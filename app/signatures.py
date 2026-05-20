"""Webhook signature verification — GitHub, Stripe, generic HMAC."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional


def verify_hmac_sha256(secret: str, payload: bytes, signature: str) -> bool:
    """Generic HMAC-SHA256 — signature is hex digest."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


def verify_github(secret: str, payload: bytes, header_value: Optional[str]) -> bool:
    """GitHub: X-Hub-Signature-256: sha256=<hex>"""
    if not header_value or not header_value.startswith("sha256="):
        return False
    provided = header_value[len("sha256="):]
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided)


def verify_stripe(secret: str, payload: bytes, header_value: Optional[str], tolerance_seconds: int = 300) -> bool:
    """Stripe: Stripe-Signature: t=<ts>,v1=<hex>"""
    if not header_value:
        return False
    parts = dict(p.split("=", 1) for p in header_value.split(",") if "=" in p)
    ts = parts.get("t")
    sig = parts.get("v1")
    if not ts or not sig:
        return False
    try:
        if abs(time.time() - int(ts)) > tolerance_seconds:
            return False
    except ValueError:
        return False
    signed_payload = f"{ts}.".encode() + payload
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
