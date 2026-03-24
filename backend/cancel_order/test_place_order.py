#!/usr/bin/env python3
"""
Step 1: Place an order to get a real order_id and intent_id.
Run this first before test_cancel_order.py
"""

import requests

resp = requests.post(
    "http://localhost:5006/placeorder",
    json={
        "CustomerID": 1,
        "OrderItems": [
            {"ItemID": 1, "Quantity": 1},
            {"ItemID": 2, "Quantity": 1}
        ],
        "SupplierID": 1,
        "Address": "1 Stamford Road, Singapore S010001",
        "ScheduledDate": "2026-03-27"
    }
)

print(f"Status: {resp.status_code}")
data = resp.json()
print(f"Response: {data}")

# Extract the values you need for test_cancel_order.py
try:
    client_secret = data["result"]["data"]["client_secret"]
    intent_id     = client_secret.split("_secret_")[0]   # pi_xxxxx part only
    order_id      = data["result"]["data"]["OrderID"]
    print(f"\n--- Copy these into test_cancel_order.py ---")
    print(f"ORDER_ID  = {order_id}")
    print(f"INTENT_ID = {intent_id}")
except Exception as e:
    print(f"\nCould not extract intent_id/order_id: {e}")
    print("Check the response above manually")