from transformers import pipeline

# Sentiment model: maps negative sentiment → high urgency, positive → low urgency
sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model="cardiffnlp/twitter-roberta-base-sentiment-latest"
)


def score_urgency(text: str) -> dict:
    if not text or not text.strip():
        return {"urgency": 0.0}

    result = sentiment_pipeline(text)[0]
    label = result["label"].upper()   # "POSITIVE", "NEGATIVE", or "NEUTRAL"
    score = result["score"]

    # POSITIVE sentiment → low urgency (invert score)
    # NEGATIVE sentiment → high urgency (keep score)
    # NEUTRAL → mid-range
    if label == "POSITIVE":
        urgency = 1.0 - score
    elif label == "NEGATIVE":
        urgency = score
    else:  # NEUTRAL
        urgency = 0.5 * score

    return {"urgency": float(urgency)}  # S ∈ [0, 1]


def is_high_urgency(scores: dict) -> bool:
    return scores.get("urgency", 0.0) > 0.7
