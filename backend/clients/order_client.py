import os
import time
import requests

ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:5002")
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", 30))


# ---- Shared request handler -----------------------------------------------

def _request_with_retry(method, url, retries=3, **kwargs):
    for attempt in range(retries):
        try:
            response = requests.request(method, url, timeout=HTTP_TIMEOUT, **kwargs)

            if response.status_code == 404:
                raise ValueError("Order not found")

            if response.status_code == 400:
                raise ValueError(f"Invalid request: {response.text}")

            if not response.ok:
                raise RuntimeError(
                    f"Order service error {response.status_code}: {response.text}"
                )

            return response.json()

        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1)


# ---- Public functions ------------------------------------------------------

def get_order(order_id):
    url = f"{ORDER_SERVICE_URL}/orders/{order_id}"
    return _request_with_retry("GET", url)


def update_order_status(order_id, status):
    url = f"{ORDER_SERVICE_URL}/orders/{order_id}/status"
    return _request_with_retry(
        "PUT",
        url,
        json={"OrderStatus": status},
    )