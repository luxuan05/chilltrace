#!/usr/bin/env python3
import json
import os
import smtplib
from email.mime.text import MIMEText
import amqp_lib
import requests


from dotenv import load_dotenv
load_dotenv()  # Load .env file into os.environ

rabbit_host   = os.getenv("RABBITMQ_HOST", "rabbitmq")
rabbit_port   = int(os.getenv("RABBITMQ_PORT", "5672"))
exchange_name = os.getenv("RABBITMQ_EXCHANGE", "order_topic")
exchange_type = "topic"
queue_name    = "Activity_Log"

# ── Telegram config ───────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ── Gmail config ──────────────────────────────────────────────────────────────
GMAIL_FROM         = os.getenv("GMAIL_FROM")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


# ─────────────────────────────────────────────────────────────────────────────
# Telegram
# ─────────────────────────────────────────────────────────────────────────────

def send_telegram(chat_id, message):
    if not chat_id:
        print("No ChatID available — customer may not have started the bot yet. Skipping Telegram.")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload, timeout=5)

        if response.status_code == 200:
            print(f"Telegram notification sent to ChatID: {chat_id}")
            return True
        else:
            print(f"Telegram API error {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"Telegram send error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Email
# ─────────────────────────────────────────────────────────────────────────────

def send_email(recipient_email, subject, body):
    if not recipient_email:
        print("No recipient email provided. Skipping email.")
        return

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
        print(f"Email error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# RabbitMQ callback
# ─────────────────────────────────────────────────────────────────────────────

def callback(channel, method, properties, body):
    try:
        message = json.loads(body)
        print(f"Received message: {message}")
    except Exception as e:
        print(f"Unable to parse JSON: {e}")
        print(f"Raw body: {body}")
        return

    recipient_email = message.get("recipient_email")
    chat_id         = message.get("chat_id")
    subject         = message.get("subject")
    message_body    = message.get("body")

    if not subject or not message_body:
        print("Missing subject or body. Skipping.")
        return

    send_email(recipient_email, subject, message_body)
    send_telegram(chat_id, f"*{subject}*\n\n{message_body}")
    print()


if __name__ == "__main__":
    print(f"This is {os.path.basename(__file__)} - notification consumer (Email + Telegram)")
    print("Waiting for messages...\n")
    try:
        amqp_lib.start_consuming(
            rabbit_host, rabbit_port, exchange_name, exchange_type, queue_name, callback
        )
    except Exception as exception:
        print(f"Unable to connect to RabbitMQ: {exception}")