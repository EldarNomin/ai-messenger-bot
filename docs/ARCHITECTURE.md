# Architecture

## Architecture style

Use a **modular monolith** for the first commercial version. Do not split the system into microservices prematurely.

Run separate process roles from the same codebase:
- `api` — FastAPI, Telegram/MAX webhooks, health/admin API;
- `worker` — durable AI jobs and messenger delivery;
- optional `scheduler` later — subscription expiry, retention and reconciliation jobs.

PostgreSQL is the source of truth. Redis is for rate limits, short-lived locks/cache and optional acceleration, not the only copy of financially important state.

## Core rule

Telegram and MAX are transport adapters. Z.AI/other vendors are AI providers. Payment systems are payment rails. None of them owns product/business rules.

```text
Telegram/MAX
    │
    ▼
Webhook adapters
    │  validate secret + normalize + persist inbox event
    ▼
PostgreSQL inbox/events  ──────► immediate HTTP 2xx
    │
    ▼
Durable job dispatcher / worker
    │
    ▼
Application services
    ├── IdentityService
    ├── ChatService
    ├── EntitlementService
    ├── Usage/BudgetService
    ├── PolicyService
    └── BillingService
    │
    ├────────────► PostgreSQL
    ├────────────► Redis
    │
    ▼
Model Router (logical modes, not vendor model ids)
    │
    ▼
AIProvider
    ├── Z.AI
    ├── Kimi/Qwen/etc later
    └── test FakeAIProvider
```

## Why webhook handling is asynchronous

Never keep a Telegram/MAX webhook request open while waiting for an LLM response.

Required flow:

```text
platform webhook
 -> validate authenticity
 -> derive external_event_id
 -> insert inbox event with UNIQUE(platform, external_event_id)
 -> enqueue/mark job in the same durable transaction
 -> return HTTP 2xx quickly
 -> worker claims job
 -> execute chat request
 -> deliver/edit messenger message
 -> mark job complete
```

This prevents duplicate model charges when platforms retry events and makes deployments/restarts safer. MAX explicitly retries failed webhook deliveries and can unsubscribe a webhook after prolonged failure, so fast acknowledgement is a production requirement.

A simple first implementation can use a PostgreSQL `jobs` table claimed with `FOR UPDATE SKIP LOCKED`. Redis Streams/ARQ may be introduced later, but the authoritative job/payment state must remain durable.

## Dependency rules

1. `adapters/*` may call application services or persist normalized inbox events.
2. Application services may call domain services and provider interfaces.
3. Provider implementations may call external APIs.
4. Core/domain modules must not import aiogram, MAX HTTP schemas or vendor SDK types.
5. Telegram/MAX must never directly invoke Z.AI.
6. Usage, budget reservation and settlement wrap every model/tool call.
7. PostgreSQL owns durable state; Redis owns ephemeral counters/locks/cache.
8. Payment webhooks do not mutate user plans directly; they append/settle billing records through BillingService.
9. Provider-specific policy restrictions are enforced before routing.

## Suggested package layout

```text
app/
├── main.py
├── config/
├── adapters/
│   ├── telegram/
│   └── max/
├── application/
│   ├── chat_service.py
│   ├── identity_service.py
│   ├── entitlement_service.py
│   ├── budget_service.py
│   ├── policy_service.py
│   └── billing_service.py
├── ai/
│   ├── router.py
│   ├── catalog.py
│   └── providers/
│       ├── base.py
│       └── zai.py
├── billing/
├── conversations/
├── entitlements/
├── identity/
├── jobs/
├── policy/
├── usage/
├── db/
└── admin/
```

## Chat request state machine

Every billable AI execution has its own durable request record:

```text
received -> queued -> running -> streaming -> completed
                         └──────-> failed
                         └──────-> cancelled
```

Store:
- internal request id;
- platform event/message ids;
- user/conversation ids;
- logical mode;
- provider/model selected;
- prompt/model/policy versions;
- reserved budget;
- provider request id;
- token usage and actual cost;
- response status/error class;
- timestamps.

A retry of the same platform event must reuse the same logical request instead of creating another paid model call.

## Budget reservation and settlement

Before calling a provider:
1. determine the plan/entitlements;
2. estimate worst-case request cost from context, modality, tools and max output;
3. reserve internal cost units/budget atomically;
4. execute the provider call;
5. settle against provider-reported usage;
6. release unused reservation.

This protects the business from concurrent overspend and requests with unexpectedly large context/output.

## Model catalog and router

Do not route product plans directly to model strings such as `glm-5.3-flash`.

The product uses logical capabilities/modes, for example:
- `standard_chat`;
- `deep_chat`;
- `vision_chat`;
- `document_chat`;
- `web_search`.

A model catalog maps these to providers/models and contains:
- model/provider id;
- supported modalities/tools;
- context/output ceilings;
- active/disabled flag;
- pricing version;
- timeout/retry policy;
- fallback group;
- cost multiplier/credit weight.

This lets the business change vendors without changing the UX or tariff model.

## Provider policy layer

Provider terms are part of runtime architecture, not only legal documentation.

For each provider maintain a policy profile describing prohibited/restricted product scenarios. The request flow performs a policy decision before model routing. If one provider cannot serve a request under its terms, either:
- route to an approved provider whose terms allow the scenario; or
- decline the unsupported scenario.

Do not silently rely on a universal assistant prompt as the only compliance control.

## Billing architecture

Separate **payment**, **subscription**, **entitlement** and **usage** concepts.

```text
Payment rail (Telegram Stars / future MAX rail)
        ↓
orders + payments (immutable/idempotent)
        ↓
subscriptions
        ↓
entitlements
        ↓
usage/budget/credits ledger
```

Important rules:
- never make Telegram Stars or a MAX payment type the primary business model object;
- store amounts as integer minor/virtual units, never floats;
- external transaction IDs are unique;
- payment events are append-only/auditable;
- refunds/reversals create compensating ledger entries;
- concurrent platform subscriptions must not accidentally multiply entitlements;
- implement reconciliation jobs against provider/platform payment history where possible.

Telegram digital goods require Stars; `/paysupport`, refunds and dispute handling must be part of the product, not an afterthought.

## Cross-platform identity

Telegram and MAX accounts are separate identities by default.

Never merge users because names/phones appear similar. Link them only through an explicit one-time account-link flow, e.g. short-lived signed link code:

```text
Telegram user -> create link code -> enter/open in MAX -> confirm -> same internal user_id
```

Until linked, each platform account maps to an independent internal user.

## Data retention and privacy

Keep product data separate from operational logs.

Support from the beginning:
- configurable message retention;
- user chat deletion;
- full account deletion workflow;
- deletion tombstone/audit without retaining deleted prompt content;
- provider/privacy policy version accepted by user where required;
- no raw prompts in infrastructure logs;
- encrypted transport and encrypted production volumes/backups.

## Tools and agent safety

Do not expose arbitrary function calling to the model in the first release.

When tools are added:
- explicit allowlist;
- per-tool cost budget;
- request timeout;
- URL/SSRF protection for web readers;
- maximum tool-call count per user request;
- audit trail;
- no secret material in tool results;
- human confirmation before any future side-effecting action.

## Reliability

Provider integration should include:
- strict connect/read/overall timeouts;
- exponential backoff with jitter for safe retries;
- retry classification (never blindly replay side effects);
- circuit breaker;
- per-provider concurrency limit;
- fallback only within an allowed cost/capability group;
- provider health metrics.

Partial streaming failures must store a failed/partial request state and present a deterministic user-facing recovery action rather than silently charging twice.

## Production data safety

Production Docker/infra must not use repository default database passwords.

Before accepting paid users:
- automated PostgreSQL backups;
- restore test;
- migration rollback/forward procedure;
- separate production secrets;
- monitoring/alerting for spend, payment failures and provider errors;
- global kill switches for models, tools, free tier and payments.

## Request lifecycle

```text
messenger event
 -> authenticate + normalize
 -> persist/deduplicate inbox event
 -> fast ACK
 -> worker claims durable job
 -> resolve/link platform account
 -> policy check
 -> entitlement check
 -> bounded context build
 -> budget reserve
 -> logical mode -> provider/model route
 -> provider call + buffered streaming delivery
 -> provider usage settlement
 -> persist assistant message/request outcome
 -> publish metrics
```

## Future-proofing

New messenger: implement a transport adapter + identity mapping.

New model vendor: implement `AIProvider` + provider policy profile + model catalog entries.

New payment rail: implement `PaymentProvider`; shared subscriptions/entitlements remain unchanged.

New pricing plan: configure products/entitlements/credit weights; do not fork chat handlers.
