# Telegram Webhook Bridge — Universal Notification Gateway

Accept webhooks from any service (Stripe, GitHub, Shopify, Sentry, your custom app) and route formatted notifications to Telegram chats with markdown, inline buttons, and acknowledgment tracking.

## What This Solves

Every SaaS sends webhooks. None of them speak Telegram. This bridge gives you one URL per integration that:
- Validates webhook signatures (HMAC, Stripe, GitHub-style)
- Maps each integration to its own Telegram chat
- Formats payloads with sensible templates (overridable)
- Sends inline action buttons (Approve / Reject / View) when applicable
- Logs every webhook with status (sent / failed / duplicate)
- Deduplicates retried webhooks via idempotency keys

## Features

- **FastAPI** — async, fast, OpenAPI docs out of the box
- **Multi-integration** — Stripe, GitHub, Shopify, generic JSON
- **Signature verification** — HMAC-SHA256, GitHub-style, Stripe-style
- **Template engine** — Jinja2 for custom message formatting
- **Inline buttons** — return actions to your webhook handler URL
- **SQLite log** — every webhook stored, queryable via /admin
- **Docker-ready** — single container, healthcheck included

## Quick Start

```bash
pip install -r requirements.txt

cp .env.example .env
# edit .env with TELEGRAM_BOT_TOKEN

cp integrations.example.yaml integrations.yaml
# edit integrations.yaml with your routes

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Your webhook URLs become:
- `https://yourdomain.com/hook/stripe`
- `https://yourdomain.com/hook/github`
- `https://yourdomain.com/hook/custom/my-app`

## Configuration Example

```yaml
integrations:
  - name: stripe
    path: /hook/stripe
    signature_method: stripe   # validates Stripe-Signature header
    signing_secret: ${STRIPE_WEBHOOK_SECRET}
    telegram_chat_id: -1001234567890
    templates:
      "charge.succeeded": "💰 New payment: ${{ data.object.amount_decimal }}"
      "customer.subscription.deleted": "😢 Cancelled: {{ data.object.customer_email }}"

  - name: github
    path: /hook/github
    signature_method: github   # validates X-Hub-Signature-256
    signing_secret: ${GITHUB_WEBHOOK_SECRET}
    telegram_chat_id: 987654321
    events_allowlist: [pull_request, issues, deployment_status]
```

## API

- `POST /hook/{name}` — main webhook ingress
- `GET /admin/logs?limit=100` — recent webhook history (auth via API key)
- `GET /healthz` — health check

## Architecture

```
External service ──webhook──→ FastAPI ──verify sig──→ template ──→ Telegram
                                  │
                                  ↓
                              SQLite log
```

## Tech Stack

- Python 3.11+
- FastAPI 0.110+
- Pydantic 2.5+
- SQLAlchemy 2.0+ (async)
- Jinja2
- httpx (async)

---

*Built by Thinh Nguyen — available for custom integration & automation work on Upwork.*
