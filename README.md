# AI Messenger Bot

Commercial AI assistant for Telegram and MAX with a shared backend and pluggable LLM providers.

## MVP

- Telegram bot
- GLM-5.3-Flash via Z.AI
- Streaming responses
- Conversation context
- Free-tier limits
- Usage and cost accounting
- Telegram Stars subscription
- PostgreSQL + Redis
- Docker Compose
- MAX adapter in the next milestone

## Architecture

```text
Telegram ─┐
          ├─> Messenger adapters -> Application services -> Conversation service -> Model router -> AI providers
MAX ──────┘                                      │
                                                  ├─> PostgreSQL
                                                  └─> Redis
```

The core must not depend on Telegram or MAX-specific APIs. Messenger integrations are adapters; model providers are replaceable.

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

- `docs/TECH_SPEC.md` — product and technical requirements
- `docs/ARCHITECTURE.md` — architectural rules and boundaries
- `docs/ROADMAP.md` — implementation stages

## Security

Never commit real bot tokens, API keys, payment secrets, webhook secrets, or `.env` files.
