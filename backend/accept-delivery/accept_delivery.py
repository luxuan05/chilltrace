import json
import os
from datetime import datetime, timezone

import pika
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()


# ---- Config -----------------------------------------------------------------

DELIVERY_SERVICE_URL = os.getenv("DELIVERY_SERVICE_URL", "http://localhost:5003")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:5002")

# Driver acceptance behavior:
# - delivery-service: transition deliveryStatus (default ACCEPTED) and assign `driver`
# - order-service: update OrderStatus (default IN_TRANSIT) to reflect that a driver is taking over
DELIVERY_STATUS_ON_ACCEPT = os.getenv("DELIVERY_STATUS_ON_ACCEPT", "ACCEPTED").upper()
ORDER_STATUS_ON_ACCEPT = os.getenv("ORDER_STATUS_ON_ACCEPT", "IN_TRANSIT").upper()
DELIVERY_ACCEPTABLE_CURRENT_STATUSES = {
    s.strip().upper()
    for s in os.getenv("DELIVERY_ACCEPTABLE_CURRENT_STATUSES", "SCHEDULED").split(",")
    if s.strip()
}

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "notification.exchange")
RABBITMQ_ROUTING_KEY = os.getenv(
    "RABBITMQ_ROUTING_KEY", "notification.delivery.accepted"
)

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", 30))
PORT = int(os.getenv("PORT", 5009))


# ---- App --------------------------------------------------------------------

app = Flask(__name__)
CORS(app)


# ---- Helpers ----------------------------------------------------------------

def _upstream_error(service_name, response):
    return RuntimeError(
        f"{service_name} error {response.status_code}: {response.text}"
    )


def get_delivery(order_id):
    """
    Fetch delivery record by order ID from delivery service.
    Expected payload includes field deliveryStatus.
    """
    url = f"{DELIVERY_SERVICE_URL}/delivery/{order_id}/"
    response = requests.get(url, timeout=HTTP_TIMEOUT)

    if response.status_code == 404:
        raise ValueError(f"Delivery for order {order_id} not found.")
    if not response.ok:
        raise _upstream_error("Delivery service", response)

    return response.json()

# tbc - to change with delivery instead of order
def ensure_order_exists(order_id):
    """Read order to verify it exists before attempting status update."""
    url = f"{ORDER_SERVICE_URL}/orders/{order_id}"
    response = requests.get(url, timeout=HTTP_TIMEOUT)

    if response.status_code == 404:
        raise ValueError(f"Order {order_id} not found.")
    if not response.ok:
        raise _upstream_error("Order service", response)

    return response.json()

# tbc - to change with delivery instead of order
def update_order_status(order_id, status):
    """Update order status in order-service."""
    url = f"{ORDER_SERVICE_URL}/orders/{order_id}/status"
    response = requests.put(url, json={"OrderStatus": status}, timeout=HTTP_TIMEOUT)

    if response.status_code == 404:
        raise ValueError(f"Order {order_id} not found.")
    if response.status_code == 400:
        raise ValueError(
            f"Order status '{status}' is not accepted by order-service."
        )
    if not response.ok:
        raise _upstream_error("Order service", response)

    return response.json()


def assign_driver_to_delivery(order_id, delivery, driver_id, delivery_status):
    """
    Assign driver to the external delivery job (DeliveryAPI).

    We preserve existing delivery fields and only update:
    - deliveryStatus
    - driver
    """
    url = f"{DELIVERY_SERVICE_URL}/delivery/{order_id}/"
    response = requests.put(
        url,
        json={
            "address": delivery.get("address", ""),
            "deliveryDate": delivery.get("deliveryDate", ""),
            "deliveryStatus": delivery_status,
            "driver": driver_id,
            "initialTemperature": delivery.get("initialTemperature", 0.1),
            "finalTemperature": delivery.get("finalTemperature", 0.1),
        },
        timeout=HTTP_TIMEOUT,
    )

    if response.status_code == 404:
        raise ValueError(f"Delivery for order {order_id} not found.")
    if not response.ok:
        raise _upstream_error("Delivery service", response)

    return response.json()


def publish_notification(event_type, payload):
    """Publish event to RabbitMQ for downstream notification processing."""
    message = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }

    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=30,
    )

    connection = pika.BlockingConnection(params)
    try:
        channel = connection.channel()
        channel.exchange_declare(
            exchange=RABBITMQ_EXCHANGE,
            exchange_type="topic",
            durable=True,
        )
        channel.basic_publish(
            exchange=RABBITMQ_EXCHANGE,
            routing_key=RABBITMQ_ROUTING_KEY,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )
    finally:
        connection.close()


# ---- Routes -----------------------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Accept Delivery service is running"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/deliveries/<int:order_id>/accept", methods=["PUT"])
def accept_delivery(order_id):
    """
    Driver accepts a delivery job.

    Flow:
    Flow should be: SCHEDULED -> ACCEPTED -> IN_TRANSIT -> DELIVERED

    1) Validate delivery exists and is currently SCHEDULED.
    2) Assign driver and set deliveryStatus to DELIVERY_STATUS_ON_ACCEPT (default ACCEPTED).
    3) Update order status to ORDER_STATUS_ON_ACCEPT (default IN_TRANSIT).
    4) Publish acceptance event for notifications/audit.
    """
    data = request.get_json(silent=True) or {}
    # to check/modify
    accepted_by = str(data.get("acceptedBy", "driver")).strip() or "driver"
    note = data.get("note", "")

    driver_id = (
        data.get("driverId")
        or data.get("DriverId")
        or data.get("driver_id")
        or data.get("DriverID")
        or data.get("driver")
        or data.get("Driver")
    )

    if driver_id is None:
        return jsonify({"error": "driverId is required"}), 400

    try:
        driver_id = int(driver_id)
    except (TypeError, ValueError):
        return jsonify({"error": "driverId must be an integer"}), 400

    subject = data.get("subject") or "Delivery accepted by driver"
    body = data.get("body")
    if not body:
        body = (
            f"Your delivery job has been accepted by driver {driver_id}."
            + (f" Note: {note}" if note else "")
        )

    try:
        delivery = get_delivery(order_id)
        current_delivery_status = str(delivery.get("deliveryStatus", "")).upper()

        if current_delivery_status not in DELIVERY_ACCEPTABLE_CURRENT_STATUSES:
            return jsonify(
                {
                    "error": "Delivery cannot be accepted.",
                    "order_id": order_id,
                    "current_delivery_status": current_delivery_status or None,
                    "required_statuses": sorted(DELIVERY_ACCEPTABLE_CURRENT_STATUSES),
                }
            ), 409

        # Read order to verify it exists and to derive CustomerID for notifications.
        order = ensure_order_exists(order_id)
        customer_id = order.get("CustomerID") or order.get("CustomerId") or order.get("customer_id")

        # Assign driver + advance delivery state in the external DeliveryAPI.
        assign_result = assign_driver_to_delivery(
            order_id=order_id,
            delivery=delivery,
            driver_id=driver_id,
            delivery_status=DELIVERY_STATUS_ON_ACCEPT,
        )

        # Update your local order state so other parts of the system know the driver has taken over.
        order_update_result = update_order_status(order_id, ORDER_STATUS_ON_ACCEPT)

        notification_sent = False
        if customer_id is not None:
            publish_notification(
                "DELIVERY_ACCEPTED",
                {
                    "buyerID": customer_id,
                    "subject": subject,
                    "body": body,
                    "order_id": order_id,
                    "accepted_by": accepted_by,
                    "delivery_status": current_delivery_status,
                    "order_status": ORDER_STATUS_ON_ACCEPT,
                },
            )
            notification_sent = True

        return jsonify(
            {
                "message": "Delivery accepted successfully.",
                "order_id": order_id,
                "delivery_status": current_delivery_status,
                "order_status": ORDER_STATUS_ON_ACCEPT,
                "delivery_assigned_status": DELIVERY_STATUS_ON_ACCEPT,
                "driver_id": driver_id,
                "accepted_by": accepted_by,
                "assign_result": assign_result,
                "order_update_result": order_update_result,
                "notification_sent": notification_sent,
            }
        ), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


if __name__ == "__main__":
    print("This flask is for " + os.path.basename(__file__) + ": accept delivery ...")
    app.run(host="0.0.0.0", port=PORT, debug=True)
