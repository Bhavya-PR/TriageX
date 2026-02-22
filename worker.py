import redis
import json
import time
import logging
import os

import requests
from dotenv import load_dotenv

from queue_manager import add_ticket
from urgency import is_high_urgency
from deduplicator import deduplicator

# Load .env so SLACK_WEBHOOK_URL / DISCORD_WEBHOOK_URL are available
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True,
)

REDIS_QUEUE_KEY = "ticket_queue"
BLOCK_TIMEOUT = 2       # seconds to wait on BRPOP before retrying
WEBHOOK_THRESHOLD = 0.8  # M2 spec: trigger alert when S > 0.8


def _send_webhook(ticket_data: dict) -> None:
    """
    Fire a POST to the Slack webhook (if configured).
    Milestone 2 requirement: trigger when urgency_score > 0.8.
    """
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        log.warning("SLACK_WEBHOOK_URL not set — skipping alert")
        return

    urgency = ticket_data.get("urgency_score", {}).get("urgency", 0.0)
    message = (
        f"🚨 *HIGH-URGENCY TICKET* [ID: {ticket_data['id']}]\n"
        f"• Category  : {ticket_data.get('category', '?')}\n"
        f"• Urgency   : {urgency:.2f}\n"
        f"• Text      : {ticket_data['text'][:300]}"
    )

    try:
        resp = requests.post(url, json={"text": message}, timeout=5)
        resp.raise_for_status()
        log.info("Slack webhook sent (status %s)", resp.status_code)
    except requests.RequestException as exc:
        log.error("Slack webhook failed: %s", exc)


def _send_master_incident_webhook(ticket_data: dict) -> None:
    """
    Fire a Master Incident webhook instead of individual alerts during a storm.
    """
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url: return

    message = (
        f"🌪️ *MASTER INCIDENT: TICKET STORM DETECTED*\n"
        f"• *Status*: >10 highly similar tickets (cosine sim > 0.9) in the last 5 minutes.\n"
        f"• *Cluster Leader Idea*: {ticket_data['text'][:200]}...\n"
        f"• *Action*: Individual webhook alerts are now SUPPRESSED for this storm."
    )
    try:
        resp = requests.post(url, json={"text": message}, timeout=5)
        resp.raise_for_status()
        log.warning("Master Incident webhook sent (status %s)!", resp.status_code)
    except requests.RequestException as exc:
        log.error("Master Incident webhook failed: %s", exc)

def process(ticket_data: dict) -> None:
    """Move one ticket from Redis into the in-memory heapq and alert if high-urgency."""
    ticket_data["processed"] = True
    add_ticket(ticket_data)

    urgency = ticket_data.get("urgency_score", {}).get("urgency", 0.0)
    
    # Check for Ticket Storm using Semantic Deduplication (Milestone 3)
    storm_status = deduplicator.check_storm(ticket_data["text"])
    
    if storm_status == "master":
        log.error("MASTER INCIDENT TRIGGERED: Deduplicator matched >10 tickets for [%s]", ticket_data["id"])
        _send_master_incident_webhook(ticket_data)
        return  # suppress individual webhook
    elif storm_status == "suppress":
        log.info("Suppressed webhook for [%s] (part of existing ticket storm cluster).", ticket_data["id"])
        return  # suppress individual webhook

    # Normal routing
    if urgency > WEBHOOK_THRESHOLD:
        log.warning(
            "HIGH URGENCY (%.2f): [%s] %s",
            urgency,
            ticket_data["id"],
            ticket_data["text"][:120],
        )
        _send_webhook(ticket_data)
    else:
        log.info(
            "Processed ticket [%s] → %s (urgency=%.2f)",
            ticket_data["id"],
            ticket_data.get("category", "?"),
            urgency,
        )


def worker():
    log.info("Worker started. Listening on Redis key '%s'…", REDIS_QUEUE_KEY)
    while True:
        try:
            # BRPOP blocks until an item arrives or timeout expires (avoids CPU spin)
            result = r.brpop(REDIS_QUEUE_KEY, timeout=BLOCK_TIMEOUT)
            if result is None:
                continue  # timeout — loop and try again

            _, raw = result  # (key, value)
            ticket_data = json.loads(raw)
            process(ticket_data)

        except redis.RedisError as e:
            log.error("Redis error: %s — retrying in 2s", e)
            time.sleep(2)
        except json.JSONDecodeError as e:
            log.error("Malformed ticket JSON, skipping: %s", e)
        except Exception as e:
            log.exception("Unexpected error processing ticket: %s", e)


if __name__ == "__main__":
    worker()
