# Technical Specification — AI Messenger Bot

## 1. Goal

Build a commercial AI assistant available in Telegram and MAX with one shared backend. The initial default provider/model is Z.AI / GLM-5.3-Flash, but the product must not depend on a single vendor or expose raw vendor API semantics to normal users.

The product sells a convenient assistant inside a messenger: conversation context, multimodal inputs, tools, predictable limits and billing. Model selection, policy, costs and routing are internal.

Architecture style for the first commercial version: **modular monolith with separate API and worker processes**, PostgreSQL as the source of truth, Redis for ephemeral rate limits/locks/cache.

## 2. Product principles

- simple UX: open -> ask -> receive answer;
- do not expose API keys;
- do not make users configure model ids;
- public UX uses logical modes (`standard`, `deep`, `search`, etc.);
- no true unlimited plan;
- complex/expensive modes consume more internal allowance;
- provider/model can change without breaking product contracts;
- monetization must be based on actual net revenue and measured cost, not theoretical request counts.

## 3. MVP scope

### Telegram paid-launch scope

Required before accepting production payments:
- `/start`, `/new`;
- text chat with GLM-5.3-Flash;
- progressively updated/streamed responses;
- conversation history with bounded context;
- durable inbound-event deduplication;
- durable background job execution;
- request state machine;
- free limits;
- token/tool/cost accounting;
- budget reservation + settlement;
- products/plans/entitlements;
- Telegram Stars orders/payments/subscriptions;
- `/terms`, `/privacy`, `/support`, `/paysupport`;
- refund/reversal support;
- provider-policy enforcement;
- PostgreSQL + Redis;
- automated backups + restore procedure;
- kill switches and spend alerts;
- Docker deployment;
- basic admin statistics.

### MAX

MAX reuses the same identity/chat/entitlement/usage/policy/model-routing core. Add only platform-specific transport, account mapping and verified payment integration. Do not assume Telegram Stars semantics exist on MAX.

Current MAX partner eligibility/payment rules must be re-checked before implementation.

## 4. Stack

- Python 3.12+
- FastAPI
- aiogram 3 for Telegram
- httpx for external APIs
- SQLAlchemy 2 + Alembic
- PostgreSQL 16+
- Redis 7+
- pydantic-settings
- pytest / pytest-asyncio
- Docker / Docker Compose

Do not introduce Kafka, Kubernetes or independently deployed microservices until measured load/organization complexity justifies them.

## 5. Process roles

Same repository/codebase, separate runtime roles:

```text
api
  FastAPI + webhooks + health/admin endpoints

worker
  durable chat/payment/background jobs

scheduler (later)
  expirations, retention, reconciliation, periodic jobs
```

## 6. Core dependency direction

```text
Telegram/MAX adapter
      ↓
Inbound event normalization / durable inbox
      ↓
Application services
      ↓
Identity / Chat / Policy / Entitlement / Budget / Billing
      ↓
Model Router
      ↓
AIProvider
      ↓
Z.AI / future providers
```

Forbidden:

```text
telegram_handler.py -> direct HTTP request to Z.AI
payment_handler.py -> user.plan = "PLUS"
```

## 7. Durable webhook flow

Webhook requests must not wait for LLM generation.

Required flow:

```text
incoming webhook
 -> validate platform secret
 -> normalize event
 -> derive external_event_id
 -> INSERT inbox event with UNIQUE(platform, external_event_id)
 -> create/mark durable job transactionally
 -> HTTP 2xx quickly
 -> worker claims job
 -> execute application flow
```

Initial durable queue implementation may be a PostgreSQL `jobs` table claimed with `FOR UPDATE SKIP LOCKED`.

Redis may accelerate queues later, but payment/request truth must not exist only in Redis.

## 8. AI request state machine

Persist each model execution independently from messenger messages.

Statuses:

```text
received
queued
running
streaming
completed
failed
cancelled
```

Fields include:
- id/request_id;
- user/conversation ids;
- platform event/message ids;
- logical mode;
- provider/model;
- prompt/model/policy versions;
- reserved budget;
- input/cached/output tokens;
- actual cost;
- provider request id;
- latency;
- failure class;
- timestamps.

A duplicate platform event must resolve to the existing request and must not create a second paid provider call.

## 9. AI provider interface

```python
class AIProvider:
    async def chat(self, request, stream=True):
        ...
```

Provider response must expose normalized:
- text/chunks;
- usage;
- finish reason;
- provider request id;
- tool events when supported;
- provider error classification.

Initial: `ZAIProvider`.

Tests: `FakeAIProvider` with deterministic streaming/usage/errors.

## 10. Model catalog and logical routing

Product code never routes directly from plan -> vendor model string.

Logical modes:
- `standard_chat`;
- `deep_chat`;
- `vision_chat`;
- `document_chat`;
- `web_search`.

Catalog entry contains:
- provider/model id;
- active flag;
- capabilities/modalities;
- context/output ceilings;
- pricing version;
- cost weight;
- timeouts;
- provider concurrency limit;
- fallback group;
- provider policy profile.

Initial mapping:

```text
standard_chat -> Z.AI / glm-5.3-flash
```

Deep/full model is not part of paid MVP unless margin tests justify it.

## 11. Provider policy layer

Provider Terms/usage restrictions are runtime constraints.

Before routing:
1. classify request/product scenario as needed;
2. evaluate selected provider policy profile;
3. route only to allowed providers;
4. otherwise return a supported refusal/alternative.

As of 2026-09-28, current Z.AI API Additional Terms allow integration into downstream applications but place responsibility for end-user management/content/data controls on the API customer and restrict specified professional/high-impact use cases. Re-check current terms before launch and on terms updates.

Source snapshot: https://chat.z.ai/legal-agreement/terms-of-service

## 12. Conversation/context

Context is bounded:
- system prompt;
- stable conversation summary;
- recent turns;
- current message.

Never resend unlimited lifetime history.

Store prompt/template versions.

Use provider-reported token usage for billing. Token estimates may be used for pre-flight budgeting only.

## 13. Budget reservation and settlement

Before any cost-bearing provider/tool call:
1. resolve entitlements;
2. estimate maximum permitted cost from context + output cap + modalities/tools;
3. atomically reserve internal budget/cost units;
4. reject if reservation exceeds user/global limits;
5. execute call;
6. settle actual cost using provider-reported usage and effective price version;
7. release unused reservation.

Hard controls:
- per-request max cost;
- per-user daily/monthly budget;
- free-tier daily budget;
- global daily/provider budget;
- model/tool kill switches.

## 14. Identity

### users
- id
- status
- created_at
- last_active_at

### platform_accounts
- id
- user_id
- platform
- external_user_id
- username/display metadata
- created_at

Unique `(platform, external_user_id)`.

Telegram and MAX accounts are **not** automatically the same user. Cross-platform linking requires an explicit one-time signed confirmation flow.

## 15. Conversation tables

### conversations
- id
- user_id
- platform/account reference
- title
- summary
- summary_version
- created_at/updated_at/archived_at

### messages
- id
- conversation_id
- role
- content/reference to stored attachment
- request_id where applicable
- status
- created_at

Token/cost truth belongs primarily to request/usage tables rather than duplicating financial truth in messages.

## 16. Durable ingress/jobs

### inbox_events
- platform
- external_event_id
- event_type
- payload or normalized safe subset
- received_at
- processed_at

Unique `(platform, external_event_id)`.

### jobs
- id
- type
- dedupe_key
- payload/reference
- status
- attempts
- available_at
- locked_at/locked_by
- last_error_class
- created_at/updated_at

Jobs must be retryable/idempotent.

## 17. Usage and pricing

### usage_events
- request_id
- user_id
- provider/model
- price_version_id
- input/cached/output tokens
- tool units/calls
- actual cost
- created_at

### model_prices
- provider/model
- input/cached/output rates
- tool rates where applicable
- currency
- effective_from/effective_to

Never mutate historical usage cost because today's provider price changed.

Current reference pricing belongs in `docs/UNIT_ECONOMICS.md`, not hardcoded business logic.

## 18. Products, payments, subscriptions and entitlements

These are separate concepts.

### products/plans
Marketing/billing product definitions.

### orders
Intent to purchase a product.

### payment_events
Append-only external payment facts. External transaction id unique.

### subscriptions
Platform subscription lifecycle/reference.

### entitlements
What the user may actually use:
- standard budget;
- deep/tool access;
- context/file ceilings;
- expiration.

### ledger
Immutable allowance/credit/budget movements. Refund/reversal uses compensating entries.

Never store money as float. Use integer minor/virtual units and explicit currency/unit type.

## 19. Telegram Stars

Digital goods/services inside Telegram use Stars (`XTR`).

Required:
- invoice/order id mapping;
- validate `pre_checkout_query` quickly;
- only grant entitlement after `successful_payment`;
- store `telegram_payment_charge_id`;
- idempotent handling;
- support refunds;
- handle multiple/concurrent subscription events safely;
- `/terms`;
- `/support` and `/paysupport`;
- backup payment records.

Do not assume user purchase price per Star equals developer net proceeds. Pricing/margin must use official/current net proceeds and observed revenue.

References:
- https://core.telegram.org/bots/payments-stars
- https://core.telegram.org/api/subscriptions
- https://core.telegram.org/api/stars

## 20. Plans and limits

Suggested shape only; actual prices/allowances follow beta measurements.

### FREE
- small standard-chat budget;
- strict rate/concurrency limits;
- no expensive tools/deep mode.

### PLUS
- larger monthly standard budget;
- images/files/voice when enabled;
- larger context.

### PRO (later)
- higher budget;
- explicit deep/tool allowances.

Public UX may show an approximate standard-message allowance. Internally enforce weighted cost units + hard provider-cost ceilings.

## 21. Streaming/delivery

Buffer provider chunks and edit messenger output periodically; never edit once per token.

Store partial failure state. A delivery/edit failure must not automatically repeat the paid model call.

Separate:
- model execution retry;
- messenger delivery retry.

## 22. Reliability

External calls require:
- connect/read/overall timeouts;
- retry classification;
- exponential backoff + jitter;
- circuit breaker;
- provider concurrency limits;
- fallback only inside permitted policy/cost/capability groups.

Do not blindly replay tool calls or other side effects.

## 23. Security/privacy

Secrets only through environment/secret manager.

Never log:
- bot/API tokens;
- auth headers;
- payment secrets;
- raw prompts in general infrastructure logs.

Support:
- chat deletion;
- account deletion;
- configurable retention;
- provider/privacy/terms version recording where required;
- encrypted transport;
- encrypted production storage/backups where available;
- admin authentication separate from user auth.

## 24. Tools/agent features

No arbitrary general-purpose tools in paid MVP.

When tools are enabled:
- explicit allowlist;
- cost budget;
- max calls/request;
- timeout;
- audit trail;
- SSRF/URL protection;
- no access to internal metadata networks/secrets;
- human confirmation for any future side-effecting actions.

## 25. Observability/business metrics

Technical:
- request/error rate;
- p50/p95 latency;
- provider latency/failures;
- queue age/depth;
- webhook dedupe/retry rate;
- DB/Redis health.

Financial/product:
- DAU/WAU/MAU;
- activation/retention;
- free -> paid conversion;
- net revenue;
- API/tool cost;
- contribution margin;
- cost per active free/paid user;
- top expensive users;
- refunds;
- cost/revenue ratio by plan/model/mode/acquisition source.

## 26. Backups/operations

Before paid production:
- automated PostgreSQL backups;
- restore test/runbook;
- migration procedure;
- separate staging/production secrets;
- spend alerts;
- provider/payment error alerts;
- global model/tool/free-tier/payment kill switches.

Repository development credentials must never be reused in production.

## 27. Testing

### Unit
- router/catalog;
- provider policy gate;
- cost calculator;
- budget reservation/settlement;
- entitlement logic;
- billing ledger;
- context builder.

### Integration
- PostgreSQL;
- Redis;
- job claiming/retry;
- mocked Z.AI;
- Telegram updates/payment events;
- MAX events when added.

### Concurrency/idempotency tests
Required for:
- duplicate webhook events;
- concurrent same-user requests;
- budget reservations;
- duplicate successful payments;
- refunds/reversals;
- worker crash during running/streaming request.

No automated test may spend real model tokens.

## 28. Paid MVP acceptance criteria

A new user can:
1. start the bot;
2. ask and continue a contextual chat;
3. receive progressively updated responses;
4. create a new chat;
5. consume a free allowance;
6. see a paywall/plan offer;
7. read Terms/support information;
8. buy through Telegram Stars;
9. receive entitlement exactly once even if events repeat;
10. continue under paid limits;
11. request payment support/refund handling path.

System properties:
- webhook ACK independent of LLM latency;
- restart does not lose durable jobs/payment state;
- duplicate events do not duplicate provider spend;
- concurrent requests cannot bypass budgets;
- provider usage/cost is auditable;
- provider policy is enforced;
- backups/restores are tested;
- secrets/prompts do not leak into normal logs.

## 29. Expansion after validation

After real retention/margin data:
- MAX adapter;
- images/files/voice;
- web search;
- deep mode;
- multiple providers/fallback;
- referral/affiliate program;
- Mini App;
- richer history/settings/admin UI.

Do not add features merely because GLM supports them; add them when they improve retention/revenue or differentiate the product.

## 30. Related docs

- `docs/ARCHITECTURE.md` — runtime/dependency/billing architecture
- `docs/ROADMAP.md` — implementation order and launch gates
- `docs/UNIT_ECONOMICS.md` — cost/pricing model
- `docs/COMMERCIAL_READINESS.md` — architecture review and P0/P1/P2 priorities
