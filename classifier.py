from transformers import pipeline

# Load zero-shot classification pipeline once at module level (avoids reloading on every call)
_classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# "General" is intentionally NOT a candidate — it competes with real labels and lowers accuracy.
# Instead, General is used as a fallback only when confidence is very low.
CANDIDATE_LABELS = ["Billing", "Technical", "Legal"]


def classify_ticket(text: str) -> str:
    if not text or not text.strip():
        return "General"

    result = _classifier(text, CANDIDATE_LABELS, multi_label=False)
    top_label = result["labels"][0]
    top_score = result["scores"][0]

    # Fall back to General only if the model has very low confidence in all 3 real categories
    if top_score < 0.25:
        return "General"

    return top_label
