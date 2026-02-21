from transformers import pipeline

# Load zero-shot classification pipeline once at module level (avoids reloading on every call)
_classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

CANDIDATE_LABELS = ["Billing", "Technical", "Legal", "General"]


def classify_ticket(text: str) -> str:
    if not text or not text.strip():
        return "General"

    result = _classifier(text, CANDIDATE_LABELS, multi_label=False)
    top_label = result["labels"][0]
    top_score = result["scores"][0]

    # If confidence is below threshold, fall back to General
    if top_score < 0.35:
        return "General"

    return top_label
