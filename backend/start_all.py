#!/usr/bin/env python3
"""
Starts all backend microservices in separate terminal windows.
Place this file in the backend/ folder and run:
    python start_all.py

Works on both Windows and macOS.
"""

import subprocess
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

services = [
    # (folder,                    script)
    ("buyer",                     "buyer.py"),
    ("supplier",                  "supplier.py"),
    ("driver",                    "driver.py"),
    ("inventory",                 "inventory.py"),
    ("order-service",             "order.py"),
    ("payment",                   "payment.py"),
    ("place_order",               "place_order.py"),
    ("cancel_order",              "cancel_order.py"),
    ("manage_supplier",           "manage_supplier.py"),
    ("accept-delivery",           "accept_delivery.py"),
    ("update-delivery-status",    "update_delivery_status.py"),
]

def start_service_windows(service_path, script):
    subprocess.Popen(
        ["powershell", "-NoExit", "-Command",
         f"cd '{service_path}'; python {script}"],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

def start_service_mac(service_path, script):
    apple_script = (
        f'tell application "Terminal" to do script '
        f'"cd \\"{service_path}\\" && python3 {script}"'
    )
    subprocess.Popen(["osascript", "-e", apple_script])

print("Starting all services...\n")

is_windows = sys.platform.startswith("win")
is_mac     = sys.platform == "darwin"

for folder, script in services:
    service_path = os.path.join(BASE_DIR, folder)
    script_path  = os.path.join(service_path, script)

    if not os.path.exists(script_path):
        print(f"[SKIP]  {folder}/{script} — file not found")
        continue

    if is_windows:
        start_service_windows(service_path, script)
    elif is_mac:
        start_service_mac(service_path, script)
    else:
        print(f"[UNSUPPORTED OS] Cannot auto-open terminal for {folder}/{script}")
        continue

    print(f"[START] {folder}/{script}")
    time.sleep(1)

print("\nAll services started.")
print("NOTE: Start notification separately via docker compose:")
print("  cd backend/notification")
print("  docker compose up --build")