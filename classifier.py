from config import BILLING_KEYWORDS, TECHNICAL_KEYWORDS, LEGAL_KEYWORDS


# Counts keyword matches per category and returns the winning category
def classify_ticket(text):
    lowered = text.lower()

    scores = {
        "Billing": sum(1 for kw in BILLING_KEYWORDS if kw in lowered),
        "Technical": sum(1 for kw in TECHNICAL_KEYWORDS if kw in lowered),
        "Legal": sum(1 for kw in LEGAL_KEYWORDS if kw in lowered),
    }

    top_score = max(scores.values())

    # Fall back to General if nothing matched or multiple categories tied
    if top_score == 0:
        return "General"

    winners = [category for category, score in scores.items() if score == top_score]
    if len(winners) > 1:
        return "General"

    return winners[0]
