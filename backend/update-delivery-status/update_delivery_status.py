from flask import Flask, request, jsonify
from flask_cors import CORS
import pika
import requests
import json
import os

app = Flask(__name__)
CORS(app)

# --- Service URLs ---
DELIVERY_SERVICE_URL = os.environ.get("DELIVERY_SERVICE_URL", "http://localhost:5003")
ORDER_SERVICE_URL    = os.environ.get("ORDER_SERVICE_URL",    "http://localhost:5002")
RABBITMQ_HOST        = os.environ.get("RABBITMQ_HOST",        "localhost")
RABBITMQ_EXCHANGE    = os.environ.get("RABBITMQ_EXCHANGE",    "notification")

DELIVERY_BASE = f"{DELIVERY_SERVICE_URL}/IS213_ChillTrace/rest/DeliveryAPI"


def publish_notification(routing_key: str, payload: dict):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        channel.exchange_declare(exchange=RABBITMQ_EXCHANGE, exchange_type="topic", durable=True)
        channel.basic_publish(
            exchange=RABBITMQ_EXCHANGE,
            routing_key=routing_key,
            body=json.dumps(payload),
            properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
        )
        connection.close()
        print(f"[AMQP] Published to '{routing_key}': {payload}")
    except Exception as e:
        print(f"[AMQP] Failed to publish notification: {e}")




# ---------------------------------------------------------------------------
# PUT /delivery_job/<order_id>/status
#
# Body: { "status": "DELIVERED"|"CANCELLED", "customer_id": int,
#         "reason": "temperature_breach" }
#
# ---------------------------------------------------------------------------
@app.route("/delivery_job/<int:order_id>/status", methods=["PUT"])
def update_delivery_job_status(order_id):
    data = request.get_json()
    if not data or "status" not in data:
        return jsonify({"error": "Missing 'status' in request body"}), 400

    new_status  = data["status"].upper()
    customer_id = data.get("customer_id")
    reason      = data.get("reason", "")

    valid_statuses = {"IN_TRANSIT", "DELIVERED", "CANCELLED", "FAILED_TEMP_BREACH"}
    if new_status not in valid_statuses:
        return jsonify({"error": f"Invalid status. Must be one of {valid_statuses}"}), 400

    errors = []


    # Step 2 — update OrderStatus on Orders table
    if order_id:
        try:
            order_status = (
                "FAILED_TEMP_BREACH"
                if (new_status == "CANCELLED" and reason == "temperature_breach")
                else new_status
            )
            resp = requests.put(
                f"{ORDER_SERVICE_URL}/orders/{order_id}",
                json={"OrderStatus": order_status},
            )
            if not resp.ok:
                errors.append(f"Order service: {resp.status_code} {resp.text}")
            else:
                print(f"[ORDER] Order #{order_id} -> {order_status}")
        except requests.RequestException as e:
            errors.append(f"Could not reach Order service: {e}")

    # Step 3 — AMQP notification
    if new_status == "CANCELLED" and reason == "temperature_breach":
        publish_notification(
            routing_key="notification.order.cancelled",
            payload={
                "event":       "ORDER_CANCELLED",
                "reason":      "temperature_breach",
                "order_id":    order_id,
                "customer_id": customer_id,
                "message":     "Your order was cancelled due to a temperature breach during delivery.",
            },
        )
    elif new_status == "DELIVERED":
        publish_notification(
            routing_key="notification.order.delivered",
            payload={
                "event":       "ORDER_DELIVERED",
                "order_id":    order_id,
                "customer_id": customer_id,
                "message":     "Your order has been successfully delivered!",
            },
        )

    return jsonify({
        "message":  f"Order #{order_id} delivery status updated to {new_status}",
        "order_id": order_id,
        "status":   new_status,
        "errors":   errors,
    }), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"service": "update_delivery_status", "status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5008, debug=True)