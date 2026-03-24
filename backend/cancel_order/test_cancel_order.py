#!/usr/bin/env python3
"""
Test script for the Cancel Order composite service.
Run while the service is running locally.

Usage:
    python test_cancel_order.py
"""

import requests

CANCEL_ORDER_URL = "http://localhost:5009"

# ── Change these values ───────────────────────────────────────────────────────
ORDER_ID        = 1
INTENT_ID       = "pi_xxxxx"               # Stripe PaymentIntent ID from place order
RECIPIENT_EMAIL = "your_test_email@gmail.com"
CUSTOMER_NAME   = "John Tan"
# ─────────────────────────────────────────────────────────────────────────────

print(f"Cancelling order {ORDER_ID}...")

resp = requests.put(
    f"{CANCEL_ORDER_URL}/cancelorder/{ORDER_ID}",
    json={
        "intent_id":       INTENT_ID,
        "recipient_email": RECIPIENT_EMAIL,
        "customer_name":   CUSTOMER_NAME,
    },
)

print(f"Status  : {resp.status_code}")
print(f"Response: {resp.json()}")