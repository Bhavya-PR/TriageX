# TriageX 🚀

> **Smart-Support Ticket Routing Engine** — Hackathon submission  
> _System Design & NLP Track · 48-Hour Implementation_

---

## Architecture

```
                        ┌─────────────────────────────────────────┐
                        │              Client / curl               │
                        └───────────────────┬─────────────────────┘
                                            │  POST /ticket
                                            ▼
                        ┌─────────────────────────────────────────┐
  Milestone 1 ──────►  │   FastAPI  (main.py)  — 202 Accepted    │
  Milestone 2 ──────►  │   ·  zero-shot classify  (BART)         │
                        │   ·  urgency score S∈[0,1] (RoBERTa)   │
                        └───────────────────┬─────────────────────┘
                                            │  LPUSH  (atomic)
                                            ▼
                        ┌─────────────────────────────────────────┐
                        │           Redis  (broker)               │
                        └───────────────────┬─────────────────────┘
                                            │  BRPOP (blocking)
                                            ▼
                        ┌─────────────────────────────────────────┐
                        │         worker.py — background          │
                        │   ·  threading.Lock  →  heapq           │
                        │   ·  S > 0.8  →  Slack / Discord 🔔    │
                        └─────────────────────────────────────────┘
```

---

## Milestones

### Milestone 1 — Minimum Viable Router (MVR)

| Requirement                                    | Implementation                                                     |
| ---------------------------------------------- | ------------------------------------------------------------------ |
| Classify tickets → Billing / Technical / Legal | `classifier.py` — HuggingFace `facebook/bart-large-mnli` zero-shot |
| Regex urgency heuristic (broken, ASAP, …)      | `config.py` — `URGENCY_FLAGS` list                                 |
| REST API accepting JSON payload                | `main.py` (FastAPI) + `app.py` (Flask fallback)                    |
| In-memory priority queue (`heapq`)             | `queue_manager.py`                                                 |
| Single-threaded execution acceptable           | ✅                                                                 |

### Milestone 2 — Intelligent Queue

| Requirement                               | Implementation                                                     |
| ----------------------------------------- | ------------------------------------------------------------------ |
| Transformer-based classification          | `classifier.py` — BART zero-shot (same model, M2-grade)            |
| Regression urgency score S ∈ [0, 1]       | `urgency.py` — `cardiffnlp/twitter-roberta-base-sentiment-latest`  |
| Async broker (Redis) + 202 Accepted       | `main.py` `LPUSH` → `worker.py` `BRPOP`                            |
| 10+ simultaneous requests w/ atomic locks | `queue_manager.py` — `threading.Lock` wraps every `heapq` op       |
| Webhook alert when S > 0.8                | `worker.py` — posts to `SLACK_WEBHOOK_URL` + `DISCORD_WEBHOOK_URL` |

---

## Quick Start

### Option A — Docker (recommended)

```bash
# 1. Copy and fill in webhook URLs (optional)
cp .env.example .env
# edit .env with your Slack / Discord webhook URLs

# 2. Start everything
docker compose up --build
```

This starts **Redis**, the **FastAPI API** (port 8000), and the **background worker** together.

---

### Option B — Local (venv)

```bash
# 1. Create & activate virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start Redis (requires Docker)
docker compose up -d redis

# 4. Copy env and configure
cp .env.example .env

# 5. Start the API
uvicorn main:app --host 0.0.0.0 --port 8000

# 6. In a separate terminal — start the worker
python worker.py
```

---

## API Reference

### `POST /ticket`

Submit a support ticket. Returns **202 Accepted** immediately; classification and queueing happen asynchronously.

**Request body:**

```json
{ "id": "T001", "text": "My invoice was charged twice — refund ASAP!" }
```

**Response (202):**

```json
{
  "status": "accepted",
  "ticket_id": "T001",
  "category": "Billing",
  "is_high_urgency": true
}
```

---

### `GET /queue?limit=10`

Peek at the top N tickets sorted by urgency (highest first).

---

### `GET /ticket/next`

Pop the single most urgent ticket for an agent to handle.

---

### `GET /health`

Returns Redis queue depth and processed heapq size.

---

## Testing

### Functional test (10 labelled tickets)

```bash
python test_tickets.py
```

### Concurrency / atomic lock stress test (20 simultaneous requests)

```bash
python stress_test.py
```

Expected output:

- All 20 tickets return **HTTP 202**
- **"No duplicate IDs — atomic lock working correctly"**
- Latency stats printed

---

## Webhook Alerts

Set either (or both) in `.env`:

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/…
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/…
```

Whenever the background worker processes a ticket with urgency **S > 0.8**, it posts a formatted alert:

```
🚨 HIGH-URGENCY TICKET [ID: T001]
• Category  : Billing
• Urgency   : 0.91
• Text      : My invoice was charged twice — refund ASAP!
```

---

## Project Structure

```
TriageX/
├── main.py            ← FastAPI app (Milestone 2 entry point)
├── app.py             ← Flask app (Milestone 1 fallback)
├── classifier.py      ← Zero-shot ticket classifier (BART)
├── urgency.py         ← Sentiment-based urgency scorer (RoBERTa)
├── queue_manager.py   ← Thread-safe heapq priority queue
├── worker.py          ← Redis consumer + webhook alerting
├── config.py          ← Keyword / urgency flag constants
├── stress_test.py     ← 20-concurrent-request stress test
├── test_tickets.py    ← 10-ticket functional test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Tech Stack

| Layer               | Technology                                                     |
| ------------------- | -------------------------------------------------------------- |
| API Framework       | FastAPI + Uvicorn                                              |
| ML — Classification | HuggingFace `facebook/bart-large-mnli` (zero-shot)             |
| ML — Urgency        | HuggingFace `cardiffnlp/twitter-roberta-base-sentiment-latest` |
| Async Broker        | Redis (`LPUSH` / `BRPOP`)                                      |
| Concurrency Safety  | `threading.Lock`                                               |
| Alert Delivery      | Slack / Discord Incoming Webhooks                              |
| Containerisation    | Docker + Docker Compose                                        |
