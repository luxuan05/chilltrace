#!/usr/bin/env python3
"""
Test script for Supplier atomic service.
Run while supplier.py is running on port 5011.

Usage:
    python test_supplier.py
"""

import requests

BASE_URL = "http://localhost:5011"

# ── Test data ─────────────────────────────────────────────────────────────────
NEW_SUPPLIER = {
    "CompanyName":  "Fresh Farms Pte Ltd",
    "Phone":        "+65 9123 4567",
    "PasswordHash": "hashed_password_here",
    "Address":      "10 Tuas Avenue, Singapore 638820",
}
# ─────────────────────────────────────────────────────────────────────────────

print("=== Supplier Service Tests ===\n")

# Health check
r = requests.get(f"{BASE_URL}/health")
print(f"[Health] {r.status_code} {r.json()}")

# Create supplier
r = requests.post(f"{BASE_URL}/supplier", json=NEW_SUPPLIER)
print(f"\n[Create Supplier] {r.status_code}")
print(r.json())

if r.status_code == 201:
    supplier_id = r.json()["supplier"]["ID"]

    # Get specific supplier
    r = requests.get(f"{BASE_URL}/supplier/{supplier_id}")
    print(f"\n[Get Supplier {supplier_id}] {r.status_code}")
    print(r.json())

    # Get all suppliers
    r = requests.get(f"{BASE_URL}/supplier")
    print(f"\n[Get All Suppliers] {r.status_code} — {len(r.json())} supplier(s) found")

    # Update supplier
    r = requests.put(f"{BASE_URL}/supplier/{supplier_id}", json={"Phone": "+65 9999 8888"})
    print(f"\n[Update Supplier {supplier_id}] {r.status_code}")
    print(r.json())