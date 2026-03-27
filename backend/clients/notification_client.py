import json
import os
import time
from datetime import datetime, timezone

import pika


# ---- Config ----------------------------------------

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

EXCHANGE_NAME = "order_topic"
EXCHANGE_TYPE = "topic"


# ---- Connection Helper -----------------------------------------------------

def _get_connection():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=30,
    )
    return pika.BlockingConnection(params)


# ---- Core Publisher --------------------------------------------------------

def publish_event(routing_key, payload, retries=3):
    """
    Generic publisher to RabbitMQ.
    """

    message = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }

    for attempt in range(retries):
        try:
            connection = _get_connection()
            channel = connection.channel()

            channel.exchange_declare(
                exchange=EXCHANGE_NAME,
                exchange_type=EXCHANGE_TYPE,
                durable=True,
            )

            channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                ),
            )

            connection.close()
            return True

        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Failed to publish message: {str(e)}")
            time.sleep(1)


# ---- WRAPPER -------------------------------

def publish_delivery_accepted(order_id, customer_id, driver_id, note=""):
    """
    Sends event to notification service when delivery is accepted.
    """

    subject = "Delivery Accepted"
    body = f"Your delivery has been accepted by driver {driver_id}."
    if note:
        body += f"\nNote: {note}"

    payload = {
        "event_type": "delivery.accepted",
        "buyerID": customer_id,
        "subject": subject,
        "body": body,
        "order_id": order_id,
        "driver_id": driver_id,
    }

    return publish_event(
        routing_key="delivery.accepted",
        payload=payload,
    )