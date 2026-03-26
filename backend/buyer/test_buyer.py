#!/usr/bin/env python3
"""
Test script for Buyer atomic service.
Run while buyer.py is running on port 5012.

Usage:
    python test_buyer.py
"""

import requests

BASE_URL = "http://localhost:5012"

# ── Test data ─────────────────────────────────────────────────────────────────
NEW_BUYER = {
    "CompanyName":  "ABC Trading Pte Ltd",
    "Phone":        "+65 9123 4567",
    "PasswordHash": "hashed_password_here",
    "Address":      "80 Stamford Road, Singapore 178902",
    "Email":        "john.tan@abctrading.com",
    "ChatID":       "",
}
# ─────────────────────────────────────────────────────────────────────────────

print("=== Buyer Service Tests ===\n")

# Health check
r = requests.get(f"{BASE_URL}/health")
print(f"[Health] {r.status_code} {r.json()}")

# Create buyer
r = requests.post(f"{BASE_URL}/buyer", json=NEW_BUYER)
print(f"\n[Create Buyer] {r.status_code}")
print(r.json())

if r.status_code == 201:
    buyer_id = r.json()["buyer"]["ID"]

    # Get specific buyer
    r = requests.get(f"{BASE_URL}/buyer/{buyer_id}")
    print(f"\n[Get Buyer {buyer_id}] {r.status_code}")
    print(r.json())

    # Get all buyers
    r = requests.get(f"{BASE_URL}/buyer")
    print(f"\n[Get All Buyers] {r.status_code} — {len(r.json())} buyer(s) found")

    # Update buyer
    r = requests.put(f"{BASE_URL}/buyer/{buyer_id}", json={"Address": "1 Orchard Road, Singapore 238801"})
    print(f"\n[Update Buyer {buyer_id}] {r.status_code}")
    print(r.json())