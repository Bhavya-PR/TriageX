from flask import Flask, request, jsonify
from datetime import datetime, timezone

from classifier import classify_ticket
from urgency import score_urgency, is_high_urgency
from queue_manager import add_ticket, get_next_ticket, peek_queue, get_queue_size

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    """Root route: API info and available endpoints."""
    return jsonify({
        "message": "Support ticket queue API",
        "endpoints": {
            "health": "/health (GET)",
            "submit_ticket": "/ticket (POST)",
            "view_queue": "/queue (GET)",
            "next_ticket": "/ticket/next (GET)",
        },
    }), 200


# Confirms the server is alive and shows how many tickets are queued
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "queue_size": get_queue_size()}), 200


# Accepts a new support ticket, classifies and scores it, then queues it
@app.route("/ticket", methods=["POST"])
def submit_ticket():
    try:
        body = request.get_json()

        if not body or "id" not in body or "text" not in body:
            return jsonify({"error": "Both 'id' and 'text' fields are required"}), 400

        ticket_id = body["id"]
        text = body["text"]

        if not text.strip():
            return jsonify({"error": "'text' must not be empty"}), 400

        category = classify_ticket(text)
        urgency_score = score_urgency(text)

        ticket = {
            "id": ticket_id,
            "text": text,
            "category": category,
            "urgency_score": urgency_score,
            "is_high_urgency": is_high_urgency(urgency_score),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        add_ticket(ticket)
        return jsonify(ticket), 201

    except Exception:
        return jsonify({"error": "An unexpected error occurred while processing the ticket"}), 500


# Shows a snapshot of queued tickets sorted by urgency, without removing them
@app.route("/queue", methods=["GET"])
def view_queue():
    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        limit = 10

    # Clamp limit to a sane maximum to avoid accidental large dumps
    limit = min(limit, 50)

    tickets = peek_queue(limit)
    return jsonify({"queue_size": get_queue_size(), "tickets": tickets}), 200



# Pops and returns the single most urgent ticket for an agent to handle
@app.route("/ticket/next", methods=["GET"])
def next_ticket():
    ticket = get_next_ticket()
    if ticket is None:
        return jsonify({"error": "Queue is empty"}), 404
    return jsonify(ticket), 200



if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
