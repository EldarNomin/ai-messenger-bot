# Roadmap

## E0 — Repository & runtime skeleton
- project layout
- FastAPI app
- settings
- Dockerfile
- Docker Compose
- PostgreSQL
- Redis
- `/health`, `/ready`

## E1 — Telegram adapter
- aiogram 3
- `/start`
- `/new`
- text updates
- webhook/polling dev mode separation

## E2 — GLM integration
- `AIProvider` interface
- `ZAIProvider`
- GLM-5.3-Flash
- streaming buffer
- error mapping/retries

## E3 — Conversations
- users/platform accounts
- conversations/messages
- bounded context
- context summarization hook

## E4 — Usage & cost
- token accounting
- model price table/config
- usage events
- request IDs
- daily/global cost guards

## E5 — Free tier
- Redis rate limits
- daily allowance
- concurrent-request lock
- user-facing limit state

## E6 — Telegram Stars
- plans
- invoice/payment events
- idempotency
- PLUS activation/expiration

## E7 — Operations
- admin stats endpoints
- structured logging
- error monitoring hooks
- kill switches

## E8 — Production
- HTTPS webhook configuration
- deployment docs
- backup strategy
- smoke tests

## E9 — MAX
- MAX adapter
- MAX webhook verification/deduplication
- shared chat core
- platform-specific billing integration

## E10 — Multimodal
- images
- files
- voice transcription

## E11 — Model routing
- Deep mode
- GLM-5.3/other models
- provider fallback with cost constraints

## E12 — Product layer
- Mini App
- referrals/credits
- history UI
- analytics dashboard

## Definition of Done

Every stage must leave the repository runnable. Before moving on:
- implementation complete
- unit/integration tests green
- Docker build green
- `.env.example` current
- docs updated
- no secrets committed
