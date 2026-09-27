# AI Messenger Bot

Commercial AI assistant for Telegram and MAX with a shared backend and pluggable LLM providers.

## MVP

- Telegram bot first
- GLM-5.3-Flash via Z.AI
- durable webhook inbox + background worker
- streaming/progressively edited responses
- bounded conversation context
- free-tier limits and cost budgets
- provider policy gate
- product entitlements/usage ledger
- Telegram Stars subscription/payment support
- PostgreSQL + Redis
- Docker Compose
- MAX adapter after Telegram validation

## Architecture

```text
Telegram/MAX
    ↓
Webhook adapters
    ↓
Durable inbox/jobs -> fast ACK
    ↓
Worker
    ↓
Application services
(identity/chat/policy/entitlements/budget/billing)
    ↓
Model router -> AI providers
    │
    ├─ PostgreSQL (source of truth)
    └─ Redis (ephemeral limits/locks/cache)
```

The project is intentionally a modular monolith for the first commercial release. The core must not depend on Telegram/MAX-specific APIs or one LLM vendor.

## Local start

```bash
cp .env.example .env
docker compose up --build
```

Health check:

```bash
curl http://localhost:8000/health
```

## Docs

- `docs/TECH_SPEC.md` — commercial/technical requirements
- `docs/ARCHITECTURE.md` — runtime, dependency and billing boundaries
- `docs/ROADMAP.md` — implementation stages and paid-launch gate
- `docs/UNIT_ECONOMICS.md` — cost model and pricing guardrails
- `docs/COMMERCIAL_READINESS.md` — architecture review and priorities

## Security

Never commit real bot tokens, API keys, payment secrets, webhook secrets, production exports or `.env` files.

Before accepting money, switch the repository to private unless there is a deliberate open-source strategy, use production-only secrets, verify backups/restores and enable spend/payment alerts.
