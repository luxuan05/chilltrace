#!/usr/bin/env python3
"""
Test script for Manage Supplier composite service.
Run while manage_supplier.py is running on port 5010.

Usage:
    python test_manage_supplier.py
"""

import requests

BASE_URL = "http://localhost:5010"

print("=== Manage Supplier Service Tests ===\n")

# ── Health check ──────────────────────────────────────────────────────────────
r = requests.get(f"{BASE_URL}/health")
print(f"[Health] {r.status_code} {r.json()}")

# ── Create supplier with inventory items ──────────────────────────────────────
r = requests.post(f"{BASE_URL}/supplier", json={
    "supplier": {
        "CompanyName":  "Fresh Farms Pte Ltd",
        "Phone":        "+65 9123 4567",
        "PasswordHash": "hashed_password_here",
        "Address":      "10 Tuas Avenue, Singapore 638820",
    },
    "inventory_items": [
        {
            "Name":           "Frozen Chicken",
            "Qty":            100,
            "Price":          5.90,
            "Category":       "Poultry",
            "Unit":           "kg",
            "Description":    "Fresh frozen chicken",
            "MinTemperature": -18.0,
            "MaxTemperature": -12.0,
        },
        {
            "Name":           "Frozen Fish",
            "Qty":            50,
            "Price":          8.50,
            "Category":       "Seafood",
            "Unit":           "kg",
            "Description":    "Fresh frozen fish",
            "MinTemperature": -18.0,
            "MaxTemperature": -12.0,
        },
    ]
})
print(f"\n[Create Supplier] {r.status_code}")
print(r.json())

if r.status_code == 201:
    supplier_id = r.json()["supplier"]["ID"]

    # ── Get supplier details ──────────────────────────────────────────────────
    r = requests.get(f"{BASE_URL}/supplier/{supplier_id}")
    print(f"\n[Get Supplier {supplier_id}] {r.status_code}")
    print(r.json())

    # ── Update supplier ───────────────────────────────────────────────────────
    r = requests.put(f"{BASE_URL}/supplier/{supplier_id}", json={
        "Phone":   "+65 9999 8888",
        "Address": "20 Tuas Avenue, Singapore 638821",
    })
    print(f"\n[Update Supplier {supplier_id}] {r.status_code}")
    print(r.json())