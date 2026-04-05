from flask import Flask, request, jsonify
from flask_cors import CORS
import pika
import requests
import json
import os

app = Flask(__name__)
CORS(app)

# --- Service URLs ---
BUYER_SERVICE_URL = os.environ.get("BUYER_SERVICE_URL", "http://buyer:5012")
DELIVERY_SERVICE_URL = os.environ.get("DELIVERY_SERVICE_URL", "http://localhost:5003")
ORDER_SERVICE_URL    = os.environ.get("ORDER_SERVICE_URL",    "http://order:5002")
RABBITMQ_HOST        = os.environ.get("RABBITMQ_HOST",        "localhost")
RABBITMQ_EXCHANGE    = os.environ.get("RABBITMQ_EXCHANGE",    "order_topic")

DELIVERY_BASE = f"{DELIVERY_SERVICE_URL}/IS213_ChillTrace/rest/DeliveryAPI"

def get_buyer_info(customer_id):
    try:
        resp = requests.get(f"{BUYER_SERVICE_URL}/buyer/{customer_id}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("Email", ""), data.get("ChatID", "")
    except Exception as e:
        print(f"Failed to fetch buyer info: {e}")
    return "", ""

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

    # Update OrderStatus on Orders table
    if order_id:
        try:
            order_status = (
                "FAILED_TEMP_BREACH"
                if (new_status == "CANCELLED" and reason == "temperature_breach")
                else new_status
            )
            resp = requests.put(
                f"{ORDER_SERVICE_URL}/orders/{order_id}/status",
                json={"OrderStatus": order_status},
            )
            if not resp.ok:
                errors.append(f"Order service: {resp.status_code} {resp.text}")
            else:
                print(f"[ORDER] Order #{order_id} -> {order_status}")
        except requests.RequestException as e:
            errors.append(f"Could not reach Order service: {e}")

    # AMQP notification
    if new_status == "CANCELLED" and reason == "temperature_breach":
        recipient_email, chat_id = get_buyer_info(customer_id)

        body = (
            f"Hi,\n\n"
            f"Your order #{order_id} has been cancelled due to a temperature breach during delivery.\n\n"
            f"Our team will be in touch regarding a refund.\n\n"
            f"We apologise for the inconvenience."
        )

        publish_notification(
            routing_key="delivery.update",
            payload={
                "recipient_email": recipient_email,
                "chat_id":         chat_id,
                "subject":         f"Order #{order_id} Cancelled - Temperature Breach",
                "body":            body,
            },
        )
    elif new_status == "DELIVERED":
        recipient_email, chat_id = get_buyer_info(customer_id)

        body = (
            f"Hi,\n\n"
            f"Your order #{order_id} has been successfully delivered!\n\n"
            f"Thank you for using ChillTrace!"
        )

        publish_notification(
            routing_key="delivery.update",
            payload={
                "recipient_email": recipient_email,
                "chat_id":         chat_id,
                "subject":         f"Order #{order_id} Delivered Successfully",
                "body":            body,
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