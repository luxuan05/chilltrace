#!/usr/bin/env python3
"""
Test script for Driver atomic service.
Run while driver.py is running on port 5013.

Usage:
    python test_driver.py
"""

import requests

BASE_URL = "http://localhost:5013"

# ── Test data ─────────────────────────────────────────────────────────────────
NEW_DRIVER = {
    "Name":      "Ali Bin Hassan",
    "VehicleNo": "SGX1234A",
    "Phone":     "+65 8123 4567",
    "Address":   "Block 123 Jurong East Street 1, Singapore 600123",
}
# ─────────────────────────────────────────────────────────────────────────────

print("=== Driver Service Tests ===\n")

# Health check
r = requests.get(f"{BASE_URL}/health")
print(f"[Health] {r.status_code} {r.json()}")

# Create driver
r = requests.post(f"{BASE_URL}/driver", json=NEW_DRIVER)
print(f"\n[Create Driver] {r.status_code}")
print(r.json())

if r.status_code == 201:
    driver_id = r.json()["driver"]["ID"]

    # Get specific driver
    r = requests.get(f"{BASE_URL}/driver/{driver_id}")
    print(f"\n[Get Driver {driver_id}] {r.status_code}")
    print(r.json())

    # Get all drivers
    r = requests.get(f"{BASE_URL}/driver")
    print(f"\n[Get All Drivers] {r.status_code} — {len(r.json())} driver(s) found")

    # Update driver
    r = requests.put(f"{BASE_URL}/driver/{driver_id}", json={"VehicleNo": "SBA9999Z"})
    print(f"\n[Update Driver {driver_id}] {r.status_code}")
    print(r.json())