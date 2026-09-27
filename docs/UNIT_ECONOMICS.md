# Unit Economics & Pricing Guardrails

Snapshot date: 2026-09-28. Re-verify provider/platform pricing before launch and periodically afterwards.

## 1. Do not price by raw request count internally

A user message can cost 100× more than another because of:
- context length;
- output length;
- stronger model selection;
- images/files/video;
- web search/tool calls;
- retries/fallbacks.

Customer UX may show a simple allowance, but internal enforcement must use weighted cost units plus hard USD-equivalent spend ceilings.

## 2. Current Z.AI reference prices

Official Z.AI pricing currently lists per 1M tokens:

| Model | Input | Cached input | Output |
|---|---:|---:|---:|
| GLM-5.3-Flash | $0.15 | $0.03 | $0.50 |
| GLM-5.3-FlashX | $0.37 | $0.075 | $1.25 |
| GLM-5.3 | $1.40 | $0.26 | $4.40 |

Built-in web search is currently listed at `$0.01/use`.

Source: https://docs.z.ai/guides/overview/pricing

This means web search can cost more than the underlying standard chat generation for many short requests, and GLM-5.3 is roughly an order of magnitude more expensive than Flash for typical generation. Treat those as separate weighted features.

## 3. Example model-only costs

Illustrative only; actual usage must come from provider-reported usage.

### Standard short chat

3,000 input + 1,000 output tokens on GLM-5.3-Flash:

```text
input  = 3,000 / 1,000,000 × $0.15 = $0.00045
output = 1,000 / 1,000,000 × $0.50 = $0.00050
total  ≈ $0.00095
```

### Larger standard chat

16,000 input + 4,000 output tokens:

```text
input  = $0.0024
output = $0.0020
total  ≈ $0.0044
```

### Same larger request on GLM-5.3

```text
input  = 16,000 / 1,000,000 × $1.40 = $0.0224
output = 4,000 / 1,000,000 × $4.40 = $0.0176
total  ≈ $0.0400
```

That is why `deep_chat` must not consume the same allowance as `standard_chat`.

## 4. Internal cost units

Recommended concept:

```text
1 cost unit ≈ configurable internal cost budget
```

Do **not** promise the exact mapping publicly. It exists to normalize changing vendors/models.

Initial relative weights can be something like:
- standard text chat: `1×` base weight;
- large file/vision: variable based on estimated context;
- web search: add explicit tool weight;
- deep model: `8–12×` base weight;
- provider fallback: charged according to actual selected route, but bounded by the user's entitlement.

Weights belong in configuration/database and can be changed without code deployment.

## 5. Reserve, then settle

Before a model/tool call:
- calculate estimated maximum cost from current context + output cap + tool allowance;
- atomically reserve budget;
- reject if reservation exceeds user/global limit.

After response:
- read provider-reported usage;
- compute actual cost using the price version effective for that request;
- settle actual cost;
- release unused reservation.

Never rely only on a post-request token counter; concurrency can otherwise overspend the account before counters catch up.

## 6. Telegram Stars revenue is not equal to the user's purchase price

For digital goods inside Telegram, payments must use Telegram Stars. Telegram documents that user acquisition price and developer net proceeds can differ because of VAT and other fees.

Therefore production pricing must use **actual/official developer net proceeds**, not assumptions such as `1 Star = fixed USD` based on what the user pays.

Store/reconcile:
- Stars charged;
- expected developer reward value at sale time if available;
- actual withdrawable/reward proceeds;
- refunds/reversals;
- effective revenue per paid user.

Sources:
- https://core.telegram.org/bots/payments-stars
- https://core.telegram.org/api/stars

## 7. Margin dashboard

At minimum track daily and monthly:

```text
Gross contribution margin =
recognized net platform revenue
- LLM/API costs
- tool/API costs
- hosting attributable cost
- refunds/reversals
```

Track by:
- plan;
- acquisition source/referrer;
- logical mode;
- model/provider;
- free vs paid cohort.

Critical alerts:
- cost/revenue ratio above threshold;
- one user's daily cost spike;
- global provider spend spike;
- abnormal retry/fallback rate;
- web-search/tool cost spike;
- refund rate increase.

## 8. Pricing strategy for launch

Do not launch with a true unlimited plan.

Prefer:
- FREE: small budget with daily anti-abuse limits;
- PLUS: monthly entitlement with standard-chat budget;
- PRO: larger budget + deep/tool allowances;
- top-up credits later if demand exists.

Public marketing may use friendly language such as an approximate number of standard chats, while Terms should explain that complex requests/tools consume allowance differently.

## 9. What to measure before fixing final prices

Run a closed beta and measure:
- median/p90 input tokens per request;
- median/p90 output tokens;
- requests per active user/day;
- percentage of requests with long context;
- web-search use rate;
- file/image use rate;
- provider failure/retry rate;
- cost per free active user;
- cost per paid active user;
- actual Telegram net proceeds per subscription.

Only after this should final Stars prices and monthly allowances be frozen.
