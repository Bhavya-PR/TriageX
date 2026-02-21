import heapq
import json
import os

QUEUE_FILE = os.path.join(os.path.dirname(__file__), "queue_store.json")

ticket_queue = []
ticket_counter = 0  # used to break ties; older tickets surface first within same urgency


def _save():
    """Persist the current queue to disk."""
    data = {
        "ticket_counter": ticket_counter,
        "tickets": [
            {"neg_urgency": neg, "seq": seq, "ticket": t}
            for neg, seq, t in ticket_queue
        ],
    }
    with open(QUEUE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _load():
    """Load the queue from disk if it exists."""
    global ticket_queue, ticket_counter
    if not os.path.exists(QUEUE_FILE):
        return
    try:
        with open(QUEUE_FILE) as f:
            data = json.load(f)
        ticket_counter = data.get("ticket_counter", 0)
        ticket_queue = [
            (item["neg_urgency"], item["seq"], item["ticket"])
            for item in data.get("tickets", [])
        ]
        heapq.heapify(ticket_queue)
    except (json.JSONDecodeError, KeyError):
        # Corrupted store — start fresh
        ticket_queue = []
        ticket_counter = 0


# Load persisted queue on module import
_load()


# Adds a ticket to the priority queue, highest urgency pops first
def add_ticket(ticket_dict):
    global ticket_counter
    ticket_counter += 1
    # urgency_score is now {"urgency": float} ∈ [0, 1]
    urgency = ticket_dict["urgency_score"].get("urgency", 0.0)
    # negate urgency so heapq (min-heap) returns highest urgency first
    heapq.heappush(ticket_queue, (-urgency, ticket_counter, ticket_dict))
    _save()


# Removes and returns the most urgent ticket, or None if the queue is empty
def get_next_ticket():
    if not ticket_queue:
        return None
    _, _, ticket_dict = heapq.heappop(ticket_queue)
    _save()
    return ticket_dict


# Returns a sorted snapshot of up to `limit` tickets without removing them
def peek_queue(limit=10):
    # Sort a copy so we don't disturb the underlying heap structure
    sorted_items = sorted(ticket_queue, key=lambda item: item[0])  # most negative (highest urgency) first
    return [ticket_dict for _, _, ticket_dict in sorted_items[:limit]]


# Returns the current number of tickets waiting in the queue
def get_queue_size():
    return len(ticket_queue)
