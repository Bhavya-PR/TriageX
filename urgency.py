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
    # NEGATIVE sentiment → high urgency (dampen slightly so frustrated-but-ok texts don't spike)
    # NEUTRAL → mid-range
    if label == "POSITIVE":
        urgency = 1.0 - score
    elif label == "NEGATIVE":
        urgency = score * 0.9   # dampen: raw negative score overshoots for mild frustration
    else:  # NEUTRAL
        urgency = 0.45 * score

    return {"urgency": float(urgency)}  # S ∈ [0, 1]


def is_high_urgency(scores: dict) -> bool:
    return scores.get("urgency", 0.0) > 0.75  # raised: 0.7 → 0.75 to reduce false positives
