from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime, timezone
import os
import redis
import json
from dotenv import load_dotenv

load_dotenv()

from classifier import classify_ticket
from urgency import score_urgency, is_high_urgency
from queue_manager import get_next_ticket, peek_queue, get_queue_size

app = FastAPI(title="TriageX", description="Support ticket triage API")

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True,
)

REDIS_QUEUE_KEY = "ticket_queue"


class TicketRequest(BaseModel):
    id: str
    text: str


@app.get("/")
def index():
    return {
        "message": "TriageX support ticket triage API",
        "endpoints": {
            "health": "GET /health",
            "submit_ticket": "POST /ticket",
            "view_queue": "GET /queue",
            "next_ticket": "GET /ticket/next",
        },
    }


@app.get("/health")
def health():
    try:
        redis_queue_size = r.llen(REDIS_QUEUE_KEY)
    except redis.RedisError:
        redis_queue_size = -1  # Redis unavailable
    return {
        "status": "ok",
        "redis_queue_size": redis_queue_size,       # awaiting worker processing
        "processed_queue_size": get_queue_size(),   # already in heapq
    }


@app.post("/ticket", status_code=202)
async def submit_ticket(ticket: TicketRequest):
    if not ticket.text.strip():
        raise HTTPException(status_code=400, detail="'text' must not be empty")

    try:
        category = classify_ticket(ticket.text)
        urgency_score = score_urgency(ticket.text)

        ticket_data = {
            "id": ticket.id,
            "text": ticket.text,
            "category": category,
            "urgency_score": urgency_score,
            "is_high_urgency": is_high_urgency(urgency_score),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "processed": False,
        }

        # Atomic LPUSH — returns immediately after enqueue
        r.lpush(REDIS_QUEUE_KEY, json.dumps(ticket_data))

    except redis.RedisError as e:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "ticket_id": ticket.id,
            "category": ticket_data["category"],
            "is_high_urgency": ticket_data["is_high_urgency"],
        },
    )


@app.get("/queue")
def view_queue(limit: int = 10):
    limit = min(max(limit, 1), 50)
    tickets = peek_queue(limit)
    return {"processed_queue_size": get_queue_size(), "tickets": tickets}


@app.get("/ticket/next")
def next_ticket():
    ticket = get_next_ticket()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Queue is empty")
    return ticket


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
