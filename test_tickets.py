"""
TriageX Test Script — sends 10 sample tickets and prints results.
Run: python test_tickets.py
"""
import requests
import json
import time

API_URL = "http://localhost:8000"

TICKETS = [
    {
        "id": "T001",
        "text": "You charged my credit card TWICE this month! I demand an immediate refund or I'm disputing with my bank!",
        "expected_category": "Billing",
        "expected_urgency": "high",
    },
    {
        "id": "T002",
        "text": "The app keeps crashing every time I try to log in. I've reinstalled it 3 times and it still doesn't work.",
        "expected_category": "Technical",
        "expected_urgency": "medium",
    },
    {
        "id": "T003",
        "text": "Your terms of service violate GDPR. My lawyer will be in touch if this is not resolved within 48 hours.",
        "expected_category": "Legal",
        "expected_urgency": "high",
    },
    {
        "id": "T004",
        "text": "Hi, I'd like to know what payment methods you accept for subscription plans.",
        "expected_category": "Billing",
        "expected_urgency": "low",
    },
    {
        "id": "T005",
        "text": "How do I reset my password? I forgot it.",
        "expected_category": "Technical",
        "expected_urgency": "low",
    },
    {
        "id": "T006",
        "text": "I was billed for a plan I cancelled 3 months ago. This is fraud and I want my money back NOW.",
        "expected_category": "Billing",
        "expected_urgency": "high",
    },
    {
        "id": "T007",
        "text": "My API integration is returning a 500 error on the /orders endpoint. Production is down!",
        "expected_category": "Technical",
        "expected_urgency": "high",
    },
    {
        "id": "T008",
        "text": "Can you send me a copy of our service agreement and data processing addendum?",
        "expected_category": "Legal",
        "expected_urgency": "low",
    },
    {
        "id": "T009",
        "text": "I believe your data retention policy does not comply with CCPA regulations.",
        "expected_category": "Legal",
        "expected_urgency": "medium",
    },
    {
        "id": "T010",
        "text": "The dashboard is loading very slowly today — takes about 10 seconds.",
        "expected_category": "Technical",
        "expected_urgency": "low",
    },
]

RESET  = "\033[0m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"


def urgency_label(is_high: bool, score: float) -> str:
    if is_high:
        return "high"
    elif score > 0.4:
        return "medium"
    return "low"


def check(actual, expected, field):
    ok = actual.lower() == expected.lower()
    mark = f"{GREEN}✅{RESET}" if ok else f"{RED}❌{RESET}"
    return mark, ok


print(f"\n{BOLD}{'='*65}{RESET}")
print(f"{BOLD}  TriageX — 10 Ticket Test Run{RESET}")
print(f"{BOLD}{'='*65}{RESET}\n")

passed = 0
for t in TICKETS:
    resp = requests.post(f"{API_URL}/ticket", json={"id": t["id"], "text": t["text"]})
    if resp.status_code != 202:
        print(f"{RED}[{t['id']}] HTTP {resp.status_code} — server error!{RESET}\n")
        continue

    data = resp.json()
    category    = data.get("category", "?")
    is_high     = data.get("is_high_urgency", False)
    # fetch full urgency score from queue
    urgency_score = None
    try:
        q = requests.get(f"{API_URL}/queue?limit=50").json()
        for ticket in q.get("tickets", []):
            if ticket["id"] == t["id"]:
                urgency_score = ticket["urgency_score"].get("urgency", 0)
                break
    except Exception:
        urgency_score = 0.5 if is_high else 0.2

    actual_urgency = urgency_label(is_high, urgency_score or 0)

    cat_mark, cat_ok    = check(category, t["expected_category"], "category")
    urg_mark, urg_ok    = check(actual_urgency, t["expected_urgency"], "urgency")

    if cat_ok and urg_ok:
        passed += 1

    print(f"{BOLD}[{t['id']}]{RESET} {t['text'][:65]}...")
    print(f"  Category : {cat_mark} got={BOLD}{category}{RESET}  expected={t['expected_category']}")
    print(f"  Urgency  : {urg_mark} got={BOLD}{actual_urgency}{RESET}  expected={t['expected_urgency']}")
    print()
    time.sleep(0.3)  # small pause so worker can process

print(f"{BOLD}{'='*65}{RESET}")
result_color = GREEN if passed == len(TICKETS) else YELLOW
print(f"  Result: {result_color}{passed}/{len(TICKETS)} tests passed{RESET}")
print(f"{BOLD}{'='*65}{RESET}\n")
