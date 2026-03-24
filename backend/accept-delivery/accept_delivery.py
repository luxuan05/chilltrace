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

# Keep this configurable because order-service currently does not define ACCEPTED.
ACCEPTED_ORDER_STATUS = os.getenv("ACCEPTED_ORDER_STATUS", "DELIVERED").upper()

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


def ensure_order_exists(order_id):
    """Read order to verify it exists before attempting status update."""
    url = f"{ORDER_SERVICE_URL}/orders/{order_id}"
    response = requests.get(url, timeout=HTTP_TIMEOUT)

    if response.status_code == 404:
        raise ValueError(f"Order {order_id} not found.")
    if not response.ok:
        raise _upstream_error("Order service", response)

    return response.json()


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
    Customer confirms order is received.

    Flow:
    1) Validate delivery exists and is currently DELIVERED.
    2) Update order status to ACCEPTED_ORDER_STATUS (default: DELIVERED).
    3) Publish acceptance event for notifications/audit.
    """
    data = request.get_json(silent=True) or {}
    accepted_by = data.get("acceptedBy", "customer")
    note = data.get("note", "")

    try:
        delivery = get_delivery(order_id)
        current_delivery_status = str(delivery.get("deliveryStatus", "")).upper()

        if current_delivery_status != "DELIVERED":
            return jsonify(
                {
                    "error": "Delivery cannot be accepted yet.",
                    "order_id": order_id,
                    "current_delivery_status": current_delivery_status or None,
                    "required_status": "DELIVERED",
                }
            ), 409

        ensure_order_exists(order_id)
        order_update_result = update_order_status(order_id, ACCEPTED_ORDER_STATUS)

        publish_notification(
            "DELIVERY_ACCEPTED",
            {
                "order_id": order_id,
                "accepted_by": accepted_by,
                "note": note,
                "delivery_status": current_delivery_status,
                "order_status": ACCEPTED_ORDER_STATUS,
            },
        )

        return jsonify(
            {
                "message": "Delivery accepted successfully.",
                "order_id": order_id,
                "delivery_status": current_delivery_status,
                "order_status": ACCEPTED_ORDER_STATUS,
                "accepted_by": accepted_by,
                "order_update_result": order_update_result,
                "notification_sent": True,
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
