# Architecture

## Core rule

Telegram and MAX are transport adapters. GLM/Z.AI is an AI provider. Neither side owns business logic.

```text
┌───────────────┐      ┌───────────────┐
│ Telegram      │      │ MAX           │
└──────┬────────┘      └──────┬────────┘
       │                      │
       ▼                      ▼
┌──────────────────────────────────────┐
│ Messenger adapters                   │
└─────────────────┬────────────────────┘
                  ▼
┌──────────────────────────────────────┐
│ Application services                 │
│ chat / users / billing / limits      │
└─────────────────┬────────────────────┘
                  ▼
┌──────────────────────────────────────┐
│ Conversation + Usage services        │
└───────────────┬───────────┬──────────┘
                │           │
                ▼           ▼
          PostgreSQL       Redis
                │
                ▼
┌──────────────────────────────────────┐
│ Model Router                         │
└─────────────────┬────────────────────┘
                  ▼
┌──────────────────────────────────────┐
│ AIProvider                           │
│ Z.AI / Kimi / Qwen / future          │
└──────────────────────────────────────┘
```

## Dependency rules

1. `adapters/*` may call application services.
2. Application services may call domain/services and provider interfaces.
3. Provider implementations may call external APIs.
4. Core/domain modules must not import aiogram, MAX SDK/client code, or provider-specific HTTP schemas.
5. Telegram and MAX must not directly invoke Z.AI.
6. Cost/usage/limit accounting happens around every model invocation.
7. Persistent state belongs in PostgreSQL; distributed counters/locks/rate limits belong in Redis.

## Suggested package layout

```text
app/
├── main.py
├── config/
│   └── settings.py
├── adapters/
│   ├── telegram/
│   └── max/
├── application/
│   └── chat_service.py
├── ai/
│   ├── router.py
│   └── providers/
│       ├── base.py
│       └── zai.py
├── conversations/
├── users/
├── usage/
├── subscriptions/
├── billing/
├── db/
└── admin/
```

## Request lifecycle

```text
messenger event
 -> authenticate/resolve platform account
 -> deduplicate event
 -> validate limits
 -> load/create conversation
 -> build bounded context
 -> select model
 -> call AI provider
 -> stream/buffer response
 -> store assistant message + usage + cost
 -> update messenger response
```

## Future-proofing

New messenger: implement `MessengerAdapter` and event mapping.

New model vendor: implement `AIProvider` and register it with `ModelRouter`.

New payment rail: implement `PaymentProvider` and map its events into the shared subscription service.
