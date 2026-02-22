# TriageX 🚀

> **Smart-Support Ticket Routing Engine** — Hackathon submission

This project implements a high-throughput, intelligent routing engine for support tickets, including ML classification, sentiment-based urgency scoring, async queues (Redis), semantic deduplication for ticket storms, and skill-based agent routing via constraint optimization.

---

## How to Run Locally (macOS/Linux)

You will need **4 separate terminal windows** to run the full system.

### Terminal 1: Start Redis

Start the Redis broker (requires Redis to be installed, e.g., `brew install redis` on macOS):

```bash
redis-server
```

_(Leave this running)_

### Terminal 2: Start the FastAPI Server

```bash
# 1. Activate the virtual environment
source venv/bin/activate

# 2. Install dependencies (if not already done)
pip install -r requirements.txt

# 3. Start the API
uvicorn main:app --host 0.0.0.0 --port 8000
```

_(Leave this running)_

### Terminal 3: Start the Background Worker

```bash
source venv/bin/activate
python worker.py
```

_(Leave this running — it processes tickets and handles webhook alerts)_

### Terminal 4: Run the Tests

With the above 3 services running, you can now send traffic to the API:

```bash
source venv/bin/activate

# 1. Run the functional test (sends 10 sample tickets and checks accuracy)
python test_tickets.py

# 2. Run the concurrency stress test (fires 20 tickets simultaneously)
python stress_test.py
```

_(Optional)_ To test **Skill-Based Routing**, push some tickets into the queue and then hit the `/route` endpoint:

```bash
curl -X POST http://localhost:8000/route?limit=10
```

---

## How to Run with Docker (Alternative)

If you prefer to run the entire stack (Redis, API, and Worker) inside Docker containers:

```bash
# Start all services
docker compose up --build
```

Then, open a new terminal to run the test scripts:

```bash
source venv/bin/activate
python test_tickets.py
python stress_test.py
```

---

## Webhook Alerts (Optional)

To receive high-urgency ticket alerts via Slack:

1. Copy the environment template: `cp .env.example .env`
2. Add your Slack Incoming Webhook URL to the `.env` file.
3. Restart the `worker.py` process.
