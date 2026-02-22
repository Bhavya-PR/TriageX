"""
TriageX Concurrency Stress Test
================================
Fires 20 tickets simultaneously using a ThreadPoolExecutor, then validates:
  1. All 20 receive HTTP 202
  2. No duplicate ticket IDs appear in the processed queue
  3. Latency stats are printed

Run:
    python stress_test.py

Requires the TriageX FastAPI server running on :8000 and Redis on :6379.
    uvicorn main:app --host 0.0.0.0 --port 8000
    python worker.py
"""

import concurrent.futures
import time
import uuid
import statistics

import requests

API_URL = "http://localhost:8000"
NUM_TICKETS = 20

RESET = "\033[0m"
GREEN = "\033[92m"
RED   = "\033[91m"
BOLD  = "\033[1m"
CYAN  = "\033[96m"

SAMPLE_TEXTS = [
    "My API is completely broken and production is DOWN right now — ASAP fix needed!",
    "I need a refund for the invoice I was charged twice.",
    "Your GDPR compliance is questionable; our legal team is reviewing.",
    "Can you help me reset my password? I forgot it.",
    "The dashboard loads very slowly today.",
    "Critical bug! The login page crashes on every submit — losing customers!",
    "Subscription was cancelled but you still billed me. This is fraud!",
    "Please send our service agreement and data processing addendum.",
    "We believe your data retention policy does not comply with CCPA.",
    "Server is returning 500 errors on the /orders endpoint — production is down!",
]


def submit_ticket(index: int) -> dict:
    ticket_id = f"STRESS-{index:04d}-{uuid.uuid4().hex[:6].upper()}"
    text = SAMPLE_TEXTS[index % len(SAMPLE_TEXTS)]
    start = time.perf_counter()
    try:
        resp = requests.post(
            f"{API_URL}/ticket",
            json={"id": ticket_id, "text": text},
            timeout=30,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "ticket_id": ticket_id,
            "status_code": resp.status_code,
            "ok": resp.status_code == 202,
            "elapsed_ms": elapsed_ms,
            "body": resp.json(),
        }
    except requests.RequestException as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "ticket_id": ticket_id,
            "status_code": 0,
            "ok": False,
            "elapsed_ms": elapsed_ms,
            "error": str(exc),
        }


def main():
    print(f"\n{BOLD}{'='*65}{RESET}")
    print(f"{BOLD}  TriageX — Concurrency Stress Test ({NUM_TICKETS} simultaneous tickets){RESET}")
    print(f"{BOLD}{'='*65}{RESET}\n")

    # --- Fire all requests at the exact same millisecond ---
    results = []
    wall_start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_TICKETS) as executor:
        futures = {executor.submit(submit_ticket, i): i for i in range(NUM_TICKETS)}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    wall_elapsed = (time.perf_counter() - wall_start) * 1000

    # --- Summary ---
    successes = [r for r in results if r["ok"]]
    failures  = [r for r in results if not r["ok"]]
    latencies = [r["elapsed_ms"] for r in results]

    for r in sorted(results, key=lambda x: x["ticket_id"]):
        mark = f"{GREEN}✅{RESET}" if r["ok"] else f"{RED}❌{RESET}"
        code = r.get("status_code", 0)
        lat  = r["elapsed_ms"]
        print(f"  {mark} [{r['ticket_id']}]  HTTP {code}  ({lat:.1f} ms)")

    print(f"\n{BOLD}{'='*65}{RESET}")
    print(f"  {GREEN if not failures else RED}Passed: {len(successes)}/{NUM_TICKETS}{RESET}")
    print(f"  Wall time : {wall_elapsed:.1f} ms  (all {NUM_TICKETS} requests fired together)")
    print(f"  Latency   : min={min(latencies):.1f}ms  max={max(latencies):.1f}ms  "
          f"p50={statistics.median(latencies):.1f}ms")

    # --- Validate no duplicates in queue ---
    print(f"\n{CYAN}  Checking for duplicate ticket IDs in queue…{RESET}")
    time.sleep(1)  # give worker a moment to drain
    try:
        q_resp = requests.get(f"{API_URL}/queue?limit=50", timeout=10).json()
        seen_ids = [t["id"] for t in q_resp.get("tickets", [])]
        dupes = [tid for tid in seen_ids if seen_ids.count(tid) > 1]
        if dupes:
            print(f"  {RED}❌ Duplicate IDs found: {set(dupes)}{RESET}")
        else:
            print(f"  {GREEN}✅ No duplicate IDs — atomic lock working correctly{RESET}")
    except Exception as exc:
        print(f"  {RED}Could not check queue: {exc}{RESET}")

    print(f"{BOLD}{'='*65}{RESET}\n")

    if failures:
        print(f"\n{RED}Failures:{RESET}")
        for r in failures:
            print(f"  [{r['ticket_id']}] status={r.get('status_code')}  err={r.get('error', r.get('body'))}")


if __name__ == "__main__":
    main()
