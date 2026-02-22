from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime, timezone
import os
import redis
import json
import concurrent.futures
from dotenv import load_dotenv

load_dotenv()

from classifier import classify_ticket
from urgency import score_urgency, is_high_urgency
from queue_manager import get_next_ticket, peek_queue, get_queue_size
from config import BILLING_KEYWORDS, LEGAL_KEYWORDS, URGENCY_FLAGS
from routing import map_tickets_to_agents, get_agent_status

# Circuit Breaker / ML ThreadPool
# "If the Transformer model latency exceeds 500ms... failover"
ml_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def _fallback_classify(text: str) -> str:
    """Lightweight Milestone 1 model fallback (Keyword-based)"""
    t = text.lower()
    for kw in BILLING_KEYWORDS:
        if kw in t: return "Billing"
    for kw in LEGAL_KEYWORDS:
        if kw in t: return "Legal"
    return "Technical"

def _fallback_urgency(text: str) -> dict:
    """Lightweight Milestone 1 model fallback (Regex/Keyword-based)"""
    t = text.lower()
    for kw in URGENCY_FLAGS:
        if kw in t: return {"urgency": 0.9} # High urgency
    return {"urgency": 0.3} # Default low


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
            "route_assignments": "POST /route",
            "agent_status": "GET /agents"
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
        # CIRCUIT BREAKER: Evaluate latency over a 500ms timeout
        def _ml_task():
            return classify_ticket(ticket.text), score_urgency(ticket.text)
            
        future = ml_executor.submit(_ml_task)
        # Wait up to 0.5s (500ms)
        category, urgency_score = future.result(timeout=0.5)
        model_used = "transformer (M2)"
    except concurrent.futures.TimeoutError:
        # "automatically failover to the lightweight Milestone 1 model."
        print(f"⚠️ Circuit Breaker Tripped! Transformer timeout for [{ticket.id}]. Failing over to M1 model.")
        category = _fallback_classify(ticket.text)
        urgency_score = _fallback_urgency(ticket.text)
        model_used = "keyword_fallback (M1)"
        
    try:
        ticket_data = {
            "id": ticket.id,
            "text": ticket.text,
            "category": category,
            "urgency_score": urgency_score,
            "is_high_urgency": is_high_urgency(urgency_score),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "processed": False,
            "model_used": model_used
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

@app.post("/route")
def route_tickets(limit: int = 10):
    """
    Skill-Based Routing via Constraint Optimization.
    Takes top tickets from the queue and assigns them to available agents based on Skill Vectors.
    """
    # 1. Grab top N tickets
    tickets = peek_queue(limit)
    if not tickets:
        return {"assignments": [], "message": "No tickets available"}
        
    # 2. Run Constraint Optimization Algorithm
    allocations = map_tickets_to_agents(tickets)
    
    # Normally we would remove them from queue, but for visualization we just return the plan
    return {
        "status": "Constraint Optimization Resolved",
        "assignments": allocations
    }

@app.get("/agents")
def get_agents():
    """Returns stateful registry and load status"""
    return get_agent_status()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
