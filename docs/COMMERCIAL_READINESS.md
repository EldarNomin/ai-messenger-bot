# Commercial Readiness Review

Review date: 2026-09-28.

## Executive decision

Keep the current technology stack and modular-monolith direction:
- Python/FastAPI;
- PostgreSQL;
- Redis;
- Telegram adapter first;
- MAX as a second adapter;
- pluggable LLM providers.

Do **not** introduce microservices, Kafka or Kubernetes for the MVP.

The important changes are inside the product core: durable jobs, entitlement/billing separation, policy enforcement, cost reservation and operational controls.

## P0 — required before accepting money

### 1. Durable webhook processing

Webhook handlers must validate + persist + ACK quickly. LLM work runs in a worker. This avoids duplicate paid calls and platform retry problems.

MAX retries failed webhook deliveries and may unsubscribe a webhook if it cannot deliver successfully for an extended period. Source: https://dev.max.ru/docs-api/methods/POST/subscriptions

### 2. Billing ledger + entitlements

Do not model a purchase as `user.plan = PLUS`.

Use:
- orders;
- payment events;
- subscriptions;
- entitlements;
- immutable usage/credit ledger.

Refunds/reversals create compensating entries. External transaction ids are unique.

### 3. Budget reservation

Reserve a worst-case internal budget before the provider call and settle actual provider-reported usage afterwards. This closes the concurrency hole where many simultaneous requests can exceed the user's/global spend cap.

### 4. Provider policy gate

As of this review, Z.AI's API Additional Terms allow downstream applications for end users, but place responsibility for end-user management, content review/data security on the API customer and restrict certain qualified/high-impact professional use cases. The product therefore needs a provider-policy layer and user Terms/AUP rather than being an unrestricted pass-through proxy.

Current source: https://chat.z.ai/legal-agreement/terms-of-service

Re-check these terms before launch and when versions change.

### 5. Telegram commercial requirements

For digital goods/services inside Telegram use Telegram Stars. Before live payments, provide clear Terms and customer support. Telegram's official live checklist requires an easy way to access Terms and customer support; digital-goods documentation also requires payment support/refund handling.

Implement at least:
- `/terms`;
- `/privacy`;
- `/support`;
- `/paysupport`;
- refunds;
- idempotent successful-payment handling;
- backup of payment records.

Source: https://core.telegram.org/bots/payments-stars

### 6. Production backups and spend kill switch

Before payments:
- automated PostgreSQL backup;
- verified restore procedure;
- separate production secrets;
- global provider spend cap;
- provider/model/tool kill switches;
- alerting for spend spikes and payment errors.

## P1 — strongly recommended before public growth

### Explicit Telegram ↔ MAX account linking

Never infer that two platform accounts are the same user. Provide a signed, short-lived link flow if shared subscriptions/history are desired.

### Logical model modes

Product/UI should know `standard`, `deep`, `vision`, `search`, not vendor model ids. Provider/model selection belongs to ModelRouter.

### Model catalog

Keep capabilities, context limits, pricing versions, active/fallback state and cost weights in a catalog/config layer.

### Data retention controls

Support deletion of chats/account and configurable retention. Keep prompts out of normal infrastructure logs.

### Tool sandboxing

When web/file/tools arrive, add explicit tool budgets, allowlists, SSRF protection and call-count ceilings before enabling agentic loops.

## P2 — after product-market validation

- Mini App;
- referrals;
- affiliate/creator acquisition;
- multiple model vendors;
- provider fallback;
- richer admin dashboard;
- advanced anti-fraud;
- dedicated managed database if load/revenue justifies it.

## Product risk: selling only “GLM access”

The architecture can support it, but the product should not be positioned as a raw GLM reseller. That is easy to copy and users can compare it directly against model-provider interfaces.

The monetizable product should be the convenience layer:
- works directly in messenger;
- persistent context;
- images/files/voice;
- web search;
- simple modes instead of model configuration;
- predictable limits/subscription;
- fast Russian-language UX;
- Telegram + MAX under one account later.

The underlying model may change without changing the product promise.

## MAX-specific note

MAX is architecturally a good second transport, but don't assume payment semantics are the same as Telegram.

Current MAX documentation confirms that public bot/mini-app access for partners requires a verified Russian legal entity, IP or self-employed profile; each bot is moderated. The payment rail for this product must be verified against then-current MAX partner rules before coding it.

Sources:
- https://dev.max.ru/docs/chatbots/bots-create/create
- https://dev.max.ru/docs/webapps/introduction

## Repository visibility

The repository was public at the time of review. For a commercial pre-launch product, switch it to **Private** unless there is a deliberate open-source strategy. Never commit production `.env`, bot tokens, API keys, webhook secrets, customer exports or payment data.

## Launch sequence

Recommended sequence:

```text
closed local/dev
  ↓
Telegram internal beta (no payment)
  ↓
real usage/cost measurement
  ↓
Telegram Stars test environment
  ↓
small paid canary
  ↓
observe margin/refunds/retention
  ↓
public Telegram launch
  ↓
MAX adapter + verified payment approach
  ↓
multimodal/tools/deep mode
```

## Architecture verdict

The original architecture direction was sound, but not sufficient for paid production because it treated the request flow and billing too simply. With the changes in `ARCHITECTURE.md`, `ROADMAP.md` and `UNIT_ECONOMICS.md`, the project has a stronger commercial foundation without unnecessary infrastructure complexity.
