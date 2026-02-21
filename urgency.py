from config import URGENCY_FLAGS, BASE_URGENCY_SCORE, MAX_URGENCY_SCORE


# Scans ticket text for urgency flag phrases and builds a score from 1 to 10
def score_urgency(text):
    lowered = text.lower()
    score = BASE_URGENCY_SCORE

    for flag in URGENCY_FLAGS:
        if flag in lowered:
            score += 2

    # Don't let score exceed the defined maximum
    return min(score, MAX_URGENCY_SCORE)


# Simple threshold check — 7 or above is considered high urgency
def is_high_urgency(score):
    return score >= 7
