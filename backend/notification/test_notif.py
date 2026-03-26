import pika
import json

connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

message = {
    "buyerID": 1,
    "subject": "Order Confirmed",
    "body": "Your order #1001 has been confirmed and is being processed."
}

channel.basic_publish(
    exchange="order_topic",
    routing_key="order.notification",
    body=json.dumps(message)
)

print("Test message published!")
connection.close()