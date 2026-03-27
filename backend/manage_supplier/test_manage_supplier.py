#!/usr/bin/env python3
"""
Test script for Manage Supplier composite service.
Run while manage_supplier.py is running on port 5010.

Usage:
    python test_manage_supplier.py
"""

import requests

BASE_URL    = "http://localhost:5010"
SUPPLIER_URL = "http://localhost:5011"

TEST_EMAIL  = "freshfarms@example.com"
TEST_SUPPLIER = {
    "CompanyName": "Fresh Farms Pte Ltd",
    "Phone":       "+65 9123 4567",
    "Password":    "password123",
    "Address":     "10 Tuas Avenue, Singapore 638820",
    "Email":       TEST_EMAIL,
}

print("=== Manage Supplier Service Tests ===\n")

# ── Health check ──────────────────────────────────────────────────────────────
r = requests.get(f"{BASE_URL}/health")
print(f"[Health] {r.status_code} {r.json()}")

# ── Check if supplier already exists ─────────────────────────────────────────
# Fetch all suppliers from atomic service to find existing one by email
existing_supplier_id = None
r = requests.get(f"{SUPPLIER_URL}/supplier")
if r.status_code == 200:
    for s in r.json():
        if s.get("Email") == TEST_EMAIL:
            existing_supplier_id = s["ID"]
            print(f"\n[Supplier already exists] ID={existing_supplier_id}, skipping create.")
            break

if existing_supplier_id is None:
    # ── Create supplier ───────────────────────────────────────────────────────
    r = requests.post(f"{BASE_URL}/supplier", json=TEST_SUPPLIER)
    print(f"\n[Create Supplier] {r.status_code}")
    print(r.json())

    if r.status_code != 201:
        print("Create supplier failed, stopping tests.")
        exit(1)

    supplier_id = r.json()["supplier"]["ID"]
    print(f"Created supplier with ID={supplier_id}")
else:
    supplier_id = existing_supplier_id

# ── Get supplier ──────────────────────────────────────────────────────────────
r = requests.get(f"{BASE_URL}/supplier/{supplier_id}")
print(f"\n[Get Supplier {supplier_id}] {r.status_code}")
print(r.json())

# ── Update supplier ───────────────────────────────────────────────────────────
r = requests.put(f"{BASE_URL}/supplier/{supplier_id}", json={
    "Phone":   "+65 9999 8888",
    "Address": "20 Tuas Avenue, Singapore 638821",
})
print(f"\n[Update Supplier {supplier_id}] {r.status_code}")
print(r.json())

# ── Create inventory item (check if any already exist first) ──────────────────
r = requests.get(f"{BASE_URL}/supplier/{supplier_id}/inventory")
existing_items = r.json().get("inventory", []) if r.status_code == 200 else []

if existing_items:
    item_id = existing_items[0]["item_id"]
    print(f"\n[Inventory already exists] Using item_id={item_id}, skipping create.")
else:
    r = requests.post(f"{BASE_URL}/supplier/{supplier_id}/inventory", json={
        "name":            "Frozen Chicken",
        "quantity":        100,
        "price":           5.90,
        "category":        "Poultry",
        "unit":            "kg",
        "description":     "Fresh frozen chicken",
        "min_temperature": -18.0,
        "max_temperature": -12.0,
    })
    print(f"\n[Create Inventory Item] {r.status_code}")
    print(r.json())
    if r.status_code != 201:
        print("Create inventory item failed, stopping inventory tests.")
        exit(1)
    item_id = r.json()["item"]["item_id"]

# ── Get all inventory items ───────────────────────────────────────────────────
r = requests.get(f"{BASE_URL}/supplier/{supplier_id}/inventory")
print(f"\n[Get All Inventory] {r.status_code} — {len(r.json().get('inventory', []))} item(s)")

# ── Get specific inventory item ───────────────────────────────────────────────
r = requests.get(f"{BASE_URL}/supplier/{supplier_id}/inventory/{item_id}")
print(f"\n[Get Item {item_id}] {r.status_code}")
print(r.json())

# ── Update inventory item ─────────────────────────────────────────────────────
r = requests.put(f"{BASE_URL}/supplier/{supplier_id}/inventory/{item_id}", json={
    "price":    6.50,
    "quantity": 200,
})
print(f"\n[Update Item {item_id}] {r.status_code}")
print(r.json())

# ── Get supplier orders ───────────────────────────────────────────────────────
print("\n=== Order Tests ===\n")

r = requests.get(f"{BASE_URL}/supplier/{supplier_id}/orders")
print(f"[Get Supplier Orders] {r.status_code}")
print(r.json())

if r.status_code == 200 and len(r.json().get("orders", [])) > 0:
    order_id = r.json()["orders"][0]["ID"]
    r = requests.put(f"{BASE_URL}/supplier/{supplier_id}/orders/{order_id}/cancel")
    print(f"\n[Cancel Order {order_id}] {r.status_code}")
    print(r.json())
else:
    print("No orders found for this supplier — skipping cancel test")