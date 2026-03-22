import os
import json

import pika
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────────

DELIVERY_SERVICE_URL = os.getenv("DELIVERY_SERVICE_URL", "http://localhost:5003")
ORDER_SERVICE_URL    = os.getenv("ORDER_SERVICE_URL",    "http://localhost:5002")

RABBITMQ_HOST        = os.getenv("RABBITMQ_HOST",        "localhost")
RABBITMQ_PORT        = int(os.getenv("RABBITMQ_PORT",    5672))
RABBITMQ_USER        = os.getenv("RABBITMQ_USER",        "guest")
RABBITMQ_PASS        = os.getenv("RABBITMQ_PASS",        "guest")
RABBITMQ_EXCHANGE    = os.getenv("RABBITMQ_EXCHANGE",    "notification.exchange")
RABBITMQ_ROUTING_KEY = os.getenv("RABBITMQ_ROUTING_KEY", "notification.delivery")

# ── App ───────────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_delivery(order_id):
    """
    GET from OutSystems: /delivery/{orderId}/
    Returns the full delivery object to preserve existing field values.
    """
    url = f"{DELIVERY_SERVICE_URL}/delivery/{order_id}/"
    response = requests.get(url, timeout=30)

    if response.status_code == 404:
        raise ValueError(f"Delivery for order {order_id} not found.")
    if not response.ok:
        raise RuntimeError(f"Delivery service error {response.status_code}: {response.text}")

    return response.json()


def update_delivery_job_status(order_id, status):
    """
    PUT to OutSystems: /delivery/{orderId}/
    GET first to preserve all existing field values, then PUT with updated deliveryStatus.
    """
    # Get existing delivery to preserve all current field values
    delivery = get_delivery(order_id)

    url = f"{DELIVERY_SERVICE_URL}/delivery/{order_id}/"
    response = requests.put(url, json={
        "address":            delivery.get("address", ""),
        "deliveryDate":       delivery.get("deliveryDate", ""),
        "deliveryStatus":     status,
        "driver":             delivery.get("driver", 0),
        "initialTemperature": delivery.get("initialTemperature", 0.1),
        "finalTemperature":   delivery.get("finalTemperature", 0.1)
    }, timeout=30)

    if response.status_code == 404:
        raise ValueError(f"Delivery for order {order_id} not found.")
    if not response.ok:
        raise RuntimeError(f"Delivery service error {response.status_code}: {response.text}")

    return response.json()


def update_order_status(order_id, status):
    """PUT to Order service (5002) to update order status."""
    url = f"{ORDER_SERVICE_URL}/orders/{order_id}/status"
    response = requests.put(url, json={"OrderStatus": status}, timeout=30)

    if response.status_code == 404:
        raise ValueError(f"Order {order_id} not found.")
    if not response.ok:
        raise RuntimeError(f"Order service error {response.status_code}: {response.text}")

    return response.json()


def publish_notification(event_type, payload):
    """Publish a notification event to RabbitMQ (step 12 in both diagrams)."""
    message = {"event_type": event_type, **payload}

    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=30
    )

    connection = pika.BlockingConnection(params)
    try:
        channel = connection.channel()
        channel.exchange_declare(
            exchange=RABBITMQ_EXCHANGE,
            exchange_type="topic",
            durable=True
        )
        channel.basic_publish(
            exchange=RABBITMQ_EXCHANGE,
            routing_key=RABBITMQ_ROUTING_KEY,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json"
            )
        )
    finally:
        connection.close()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Update Delivery Status service is running"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/delivery-jobs/<int:order_id>/status", methods=["PUT"])
def update_delivery_status(order_id):
    """
    Called by Driver Delivery Job UI (step 8).
    Uses orderId since OutSystems API is keyed by orderId.
    Body: { "deliveryStatus": "IN_TRANSIT" | "DELIVERED" | "CANCELLED" }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    new_status = data.get("deliveryStatus")
    if not new_status:
        return jsonify({"error": "deliveryStatus is required"}), 400

    new_status = new_status.upper()
    allowed_statuses = {"IN_TRANSIT", "DELIVERED", "CANCELLED"}
    if new_status not in allowed_statuses:
        return jsonify({"error": f"Invalid deliveryStatus. Must be one of: {sorted(allowed_statuses)}"}), 400

    try:
        # Step 9: always move to IN_TRANSIT first
        update_delivery_job_status(order_id, "IN_TRANSIT")

        if new_status == "IN_TRANSIT":
            return jsonify({
                "order_id": order_id,
                "deliveryStatus": "IN_TRANSIT",
                "message": "Delivery marked as IN_TRANSIT."
            }), 200

        if new_status == "DELIVERED":
            # Step 10: update delivery → DELIVERED
            update_delivery_job_status(order_id, "DELIVERED")

            # Step 11: update order → DELIVERED
            update_order_status(order_id, "DELIVERED")

            # Step 12: notify
            publish_notification("DELIVERY_COMPLETED", {
                "order_id": order_id,
                "deliveryStatus": "DELIVERED",
                "message": "Your order has been delivered successfully."
            })

            return jsonify({
                "order_id": order_id,
                "deliveryStatus": "DELIVERED",
                "order_status": "DELIVERED",
                "notification_sent": True
            }), 200

        if new_status == "CANCELLED":
            # Step 10: update delivery → CANCELLED
            update_delivery_job_status(order_id, "CANCELLED")

            # Step 11: update order → CANCELLED
            update_order_status(order_id, "CANCELLED")

            # Step 12: notify temperature breach
            publish_notification("DELIVERY_CANCELLED_TEMP_BREACH", {
                "order_id": order_id,
                "deliveryStatus": "CANCELLED",
                "message": "Your order was cancelled due to a temperature breach during delivery."
            })

            return jsonify({
                "order_id": order_id,
                "deliveryStatus": "CANCELLED",
                "order_status": "CANCELLED",
                "notification_sent": True
            }), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


if __name__ == '__main__':
    print("This flask is for " + os.path.basename(__file__) + ": update delivery status ...")
    app.run(host='0.0.0.0', port=5008, debug=True)