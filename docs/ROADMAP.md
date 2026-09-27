# Roadmap

The goal is a **commercially safe modular monolith**, not a demo and not premature microservices.

## E0 — Repository & runtime skeleton
- project layout
- FastAPI app
- settings
- Dockerfile
- Docker Compose
- PostgreSQL
- Redis
- `/health`, `/ready`
- CI: lint, tests, Docker build

## E1 — Durable ingress & Telegram adapter
- aiogram 3
- Telegram webhook + dev polling separation
- webhook secret validation
- normalized inbound event model
- PostgreSQL inbox/event deduplication
- durable `jobs` table
- worker process using safe job claiming
- fast webhook ACK before LLM work
- `/start`, `/new`

## E2 — AI abstraction & GLM integration
- `AIProvider` interface
- `ZAIProvider`
- logical model catalog (`standard_chat`, not model strings in product code)
- GLM-5.3-Flash
- streaming buffer
- provider timeouts/error mapping/retries
- `FakeAIProvider`

## E3 — Identity & conversations
- users/platform accounts
- explicit account-link design for future Telegram ↔ MAX linking
- conversations/messages
- durable AI request state machine
- bounded context
- context summarization hook
- prompt/model/policy version tracking

## E4 — Usage, budget & unit economics
- provider-reported token accounting
- versioned model price table/config
- usage events
- request IDs/provider request IDs
- budget reservation before provider call
- actual-cost settlement after provider response
- daily/monthly/global cost guards
- tool-cost accounting

## E5 — Product plans & entitlements
- `products/plans`
- `entitlements`
- internal usage/credit ledger
- Redis rate limits
- free allowance
- concurrent-request lock
- weighted usage by logical mode/modality/tool
- user-facing balance/limit state

## E6 — Provider policy & commercial compliance
- provider policy profiles
- request policy gate before model routing
- `/terms`
- `/privacy`
- `/support`
- `/paysupport`
- product Terms/Privacy/AUP acceptance/versioning where required
- data-retention/deletion workflow
- provider disclosure requirements documented

## E7 — Telegram Stars billing
- orders
- immutable/idempotent payments
- pre-checkout validation within Telegram deadline
- successful payment handling
- subscription records
- payment → subscription → entitlement mapping
- refunds/reversals as compensating records
- PLUS activation/expiration
- duplicate/multiple-subscription handling
- reconciliation/admin payment view

## E8 — Operations & production readiness
- structured logging without raw secrets/prompts
- metrics/tracing/error monitoring
- provider circuit breaker/concurrency controls
- kill switches
- automated PostgreSQL backups
- restore drill/runbook
- production secrets strategy
- migrations/runbook
- spend/payment/provider alerts

## E9 — Production launch
- HTTPS webhook configuration
- staging → production promotion
- smoke tests
- payment test environment → production checklist
- canary/limited user launch
- margin/retention dashboards

## E10 — MAX
- MAX eligibility/verification completed
- MAX adapter
- `platform-api2.max.ru`
- webhook secret verification
- same durable inbox/job pipeline
- explicit identity-link flow
- payment rail researched/verified against then-current MAX rules before implementation
- no assumption that Telegram Stars semantics apply to MAX

## E11 — Multimodal & tools
- images
- files
- voice transcription
- web search
- per-tool cost budgets
- SSRF/URL protection
- tool-call count limits
- audit trail

## E12 — Advanced routing/product layer
- Deep mode
- GLM-5.3/other providers
- provider fallback with policy/cost constraints
- Mini App
- referrals/credits after anti-fraud controls
- history UI
- analytics dashboard

## Definition of Done

Every stage must leave the repository runnable. Before moving on:
- implementation complete;
- unit/integration tests green;
- Docker build green;
- migrations tested;
- `.env.example` current;
- docs updated;
- no secrets committed;
- idempotency tests exist for event/payment flows introduced in that stage;
- cost-impacting code has tests for limits/reservations/settlement.

## Launch gate for paid users

Do not accept production payments until all are true:
- durable webhook/job pipeline is enabled;
- payment idempotency is tested;
- `/terms`, `/support`, `/paysupport` exist;
- backups and restore procedure are verified;
- global spend kill switch works;
- per-user and global budgets work under concurrency;
- Z.AI/provider policy restrictions are enforced/documented;
- production pricing is based on actual platform net proceeds and observed model usage, not only theoretical token cost.
