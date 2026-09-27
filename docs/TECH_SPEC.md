# Technical Specification — AI Messenger Bot

## 1. Goal

Build a commercial AI assistant available in Telegram and MAX. The initial default model is GLM-5.3-Flash through Z.AI. The architecture must support adding GLM-5.3, Kimi, Qwen, DeepSeek and other OpenAI-compatible providers without rewriting messenger logic.

The product sells convenience, not raw API access: users interact with an assistant inside a messenger, while model selection, limits, billing and routing remain internal.

## 2. MVP scope

### Telegram v0.1

Required:
- `/start`
- text chat with GLM-5.3-Flash
- streamed/periodically edited responses
- conversation history
- `/new` / New chat
- free daily limits
- request, token and cost accounting
- Telegram Stars payment abstraction
- PLUS subscription
- PostgreSQL persistence
- Redis rate limiting/cache
- Docker deployment
- health/readiness endpoints
- basic admin statistics

### MAX v0.2

Reuse the same backend. Add only platform-specific adapter, webhook handling and payment integration. No AI or billing business logic may be duplicated inside the MAX layer.

## 3. UX principles

Primary flow:
1. User opens bot.
2. Sends a question immediately.
3. Bot shows activity and starts returning answer quickly.
4. Follow-up messages preserve context.
5. User can start a fresh chat at any time.

Do not expose API keys or force model configuration on normal users.

## 4. Recommended stack

- Python 3.12+
- FastAPI
- aiogram 3 for Telegram
- httpx for external HTTP APIs
- SQLAlchemy 2 + Alembic
- PostgreSQL 16+
- Redis
- pydantic-settings
- pytest
- Docker / Docker Compose

## 5. Architectural boundaries

Correct dependency direction:

```text
Telegram/MAX adapter
      ↓
Application service
      ↓
Conversation / Usage / Subscription services
      ↓
Model Router
      ↓
AIProvider interface
      ↓
Z.AI / Kimi / Qwen / other provider
```

Forbidden:

```text
telegram_handler.py -> direct HTTP request to Z.AI
```

Messenger-specific code must not own model selection, subscription rules, cost calculations or conversation policies.

## 6. AI provider interface

All LLMs implement a common interface conceptually equivalent to:

```python
class AIProvider:
    async def chat(self, messages, model=None, stream=True, options=None):
        ...
```

Initial implementation: `ZAIProvider`.

Later providers:
- KimiProvider
- QwenProvider
- OpenAICompatibleProvider

## 7. Model router

Initial policy:
- default -> GLM-5.3-Flash
- deep -> configurable stronger model
- vision -> multimodal-capable model

Routing must be configuration-driven. Never hardcode tariff/business decisions into handlers.

## 8. Streaming

Streaming response UX is required. For Telegram, buffer chunks and edit the message periodically rather than for every token. Target edit cadence: roughly 500–1000 ms, adjusted to API limits.

## 9. Conversation context

Each user has conversations with messages.

Context sent to the model should be bounded:
- system prompt
- summarized older context
- last N messages
- current user message

Do not resend unlimited lifetime history on every request.

When history exceeds a configurable threshold, summarize older turns and retain recent messages verbatim.

## 10. Data model

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
- username
- first_name
- created_at

Unique key: `(platform, external_user_id)`.

### conversations
- id
- user_id
- platform
- title
- summary
- created_at
- updated_at
- archived_at

### messages
- id
- conversation_id
- role
- content
- model
- input_tokens
- output_tokens
- cost_usd
- latency_ms
- status
- created_at

### usage_events
- id
- user_id
- conversation_id
- provider
- model
- input_tokens
- cached_tokens
- output_tokens
- cost_usd
- request_id
- created_at

### processed_events
- platform
- external_event_id
- processed_at

Used for webhook deduplication.

### model_prices
- provider
- model
- input_price
- cached_input_price
- output_price
- effective_from

Prices must be configuration/data, not constants buried in business logic.

## 11. Tariffs and limits

Initial product shape:

### FREE
- small daily request allowance
- GLM-5.3-Flash
- shorter context/output limits

### PLUS
- higher limits
- larger context
- future image/file/voice access

### PRO (later)
- high limits
- deep mode
- stronger models/tools

No true unlimited plan. Internally enforce:
- requests per minute/day/month
- tokens per day/month
- max output tokens
- max context
- max concurrent requests
- daily/monthly cost ceiling

## 12. Billing

Payment code must implement a provider abstraction:

```text
PaymentProvider
├── TelegramStarsProvider
├── MaxPaymentProvider
└── FutureProvider
```

Persist external transaction IDs and enforce idempotency so duplicate payment events cannot activate subscriptions twice.

Subscription data must support:
- plan
- activation time
- expiration time
- renewal state
- platform payment reference

## 13. Cost controls

Every LLM call records usage and estimated cost.

Support:
- per-user daily cost cap
- per-user monthly cost cap
- global daily spend cap
- model/provider kill switch
- free-tier kill switch

If a threshold is exceeded, block further expensive execution and log an alert condition.

## 14. Rate limiting

Use Redis. Initial configurable examples:
- FREE: 5 req/min + daily cap
- PLUS: 15 req/min
- PRO: 30 req/min
- one concurrent model request per user in MVP

Exact values are configuration, not hardcoded product truth.

## 15. Webhooks

Production integrations use HTTPS webhooks.

Endpoints:
- `POST /webhooks/telegram`
- `POST /webhooks/max`

Validate platform webhook secrets and deduplicate repeated events.

## 16. Reliability

For network/429/5xx model failures use controlled retry with exponential backoff, e.g. 1s, 2s, 4s, maximum 3 attempts where safe.

Provider fallback architecture is desirable, but fallback must respect cost ceilings and must not silently route cheap traffic to an unexpectedly expensive model.

## 17. Security

Secrets only through environment/secret manager:
- TELEGRAM_BOT_TOKEN
- MAX_BOT_TOKEN
- ZAI_API_KEY
- DATABASE_URL
- REDIS_URL
- webhook secrets
- admin secret

Never commit real credentials.

Do not log:
- bot tokens
- model API keys
- payment secrets
- raw auth headers

User message content should not be duplicated into infrastructure logs unless explicitly required and sanitized.

## 18. Observability

Each model request should have:
- request_id
- user_id
- conversation_id
- provider
- model
- token usage
- estimated cost
- latency
- status/error class

Core metrics:
- users / DAU / WAU / MAU
- messages/day
- AI requests/day
- token usage
- AI cost
- revenue
- gross margin
- free-to-paid conversion
- error rate
- p95 latency

## 19. Health endpoints

`GET /health` — process alive.

`GET /ready` — verifies dependencies required to serve traffic, initially PostgreSQL and Redis.

## 20. Testing

### Unit
- model router
- cost calculator
- tariff/limit logic
- context builder
- subscription logic

### Integration
- PostgreSQL
- Redis
- mocked Z.AI
- Telegram update handling
- MAX event handling when added

### E2E
- `/start`
- question -> answer
- follow-up context
- `/new`
- free limit exhaustion
- successful payment -> PLUS activation
- subscription expiration

Provide `FakeAIProvider` for deterministic tests. Automated tests must not spend real model tokens.

## 21. MVP acceptance criteria

A new Telegram user can:
1. start the bot;
2. ask a question;
3. receive a progressively updated AI response;
4. continue a contextual conversation;
5. start a new chat;
6. see/use a free allowance;
7. hit the free limit;
8. purchase a paid plan;
9. have the plan activated idempotently;
10. continue chatting under paid limits.

The system must also:
- survive restart without losing state;
- record tokens/costs;
- enforce rate and spending limits;
- reject duplicate events/payments safely;
- keep secrets out of git/logs.

## 22. Product expansion after MVP

After demand validation:
- MAX adapter
- images
- voice transcription/TTS
- PDF/DOCX/TXT/CSV handling
- web search
- deep mode
- multiple model providers
- referral/credits system
- Mini App
- conversation history UI
- analytics/admin dashboard
