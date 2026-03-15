#!/usr/bin/env python3
import json
import os
import smtplib
from email.mime.text import MIMEText
import amqp_lib
import requests

rabbit_host   = "rabbitmq"
rabbit_port   = 5672
exchange_name = "order_topic"
exchange_type = "topic"
queue_name    = "Activity_Log"

# ── Telegram config ───────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID        = os.getenv("CHAT_ID")

# ── Gmail config ──────────────────────────────────────────────────────────────
GMAIL_FROM         = os.getenv("GMAIL_FROM")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def send_telegram(message):
    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, json=payload)


def send_email(recipient_email, subject, body):
    msg = MIMEText(body)
    msg["From"]    = GMAIL_FROM
    msg["To"]      = recipient_email
    msg["Subject"] = subject

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_FROM, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_FROM, recipient_email, msg.as_string())
        print(f"Email sent to {recipient_email}")
    except Exception as e:
        print(f"Email error: {e=}")


def callback(channel, method, properties, body):
    # required signature for the callback; no return
    try:
        message = json.loads(body)
        print(f"JSON: {message}")
    except Exception as e:
        print(f"Unable to parse JSON: {e=}")
        print(f"Message: {body}")
        return

    recipient_email = message.get("recipient_email")
    subject         = message.get("subject")
    email_body      = message.get("body")

    if not recipient_email or not subject or not email_body:
        print("Missing recipient_email, subject, or body. Skipping.")
        return

    send_email(recipient_email, subject, email_body)
    send_telegram(f"{subject}\n\n{email_body}")

    print()


if __name__ == "__main__":
    print(f"This is {os.path.basename(__file__)} - amqp consumer...")
    try:
        amqp_lib.start_consuming(
            rabbit_host, rabbit_port, exchange_name, exchange_type, queue_name, callback
        )
    except Exception as exception:
        print(f"  Unable to connect to RabbitMQ.\n     {exception=}\n")