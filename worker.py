import redis
import json
import time
import logging

from queue_manager import add_ticket
from urgency import is_high_urgency

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

REDIS_QUEUE_KEY = "ticket_queue"
BLOCK_TIMEOUT = 2  # seconds to wait on BRPOP before retrying


def process(ticket_data: dict) -> None:
    """Move one ticket from Redis into the in-memory heapq."""
    ticket_data["processed"] = True
    add_ticket(ticket_data)

    if is_high_urgency(ticket_data.get("urgency_score", {})):
        log.warning("HIGH URGENCY: [%s] %s", ticket_data["id"], ticket_data["text"][:120])
        # Uncomment to send a real Slack/Discord alert:
        # import requests, os
        # requests.post(os.environ["SLACK_WEBHOOK_URL"],
        #               json={"text": f"URGENT [{ticket_data['id']}]: {ticket_data['text'][:200]}"})
    else:
        log.info("Processed ticket [%s] → %s", ticket_data["id"], ticket_data["category"])


def worker():
    log.info("Worker started. Listening on Redis key '%s'...", REDIS_QUEUE_KEY)
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
