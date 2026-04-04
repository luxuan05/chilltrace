import os
import time
import requests

DELIVERY_SERVICE_URL = os.getenv("DELIVERY_SERVICE_URL", "http://localhost:5003")
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", 30))


# ---- Shared request handler -----------------------------------------------

def _request_with_retry(method, url, retries=3, **kwargs):
    for attempt in range(retries):
        try:
            response = requests.request(method, url, timeout=HTTP_TIMEOUT, **kwargs)

            if response.status_code == 404:
                raise ValueError("Resource not found")

            if not response.ok:
                raise RuntimeError(
                    f"Delivery service error {response.status_code}: {response.text}"
                )

            return response.json()

        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(1)


# ---- Public functions ------------------------------------------------------

def get_delivery(delivery_id):
    url = f"{DELIVERY_SERVICE_URL}/delivery/{delivery_id}/"
    return _request_with_retry("GET", url)


def update_delivery(delivery_id, payload):
    url = f"{DELIVERY_SERVICE_URL}/delivery/{delivery_id}/"
    return _request_with_retry("PUT", url, json=payload)