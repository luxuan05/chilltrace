#!/usr/bin/env python3
import json
import os
import smtplib
from email.mime.text import MIMEText
import amqp_lib
import requests
import pymysql
import pymysql.cursors

rabbit_host   = "localhost"
rabbit_port   = 5672
exchange_name = "order_topic"
exchange_type = "topic"
queue_name    = "Activity_Log"

# ── Telegram config ───────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ── Gmail config ──────────────────────────────────────────────────────────────
GMAIL_FROM         = os.getenv("GMAIL_FROM")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# ── MySQL config ──────────────────────────────────────────────────────────────
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = int(os.getenv("DB_PORT", 3306))
DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME     = os.getenv("DB_NAME", "your_database")


# ─────────────────────────────────────────────────────────────────────────────
# Database helper
# ─────────────────────────────────────────────────────────────────────────────

def get_connection():
    """Create and return a new MySQL connection."""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def get_buyer_info(buyer_id):
    """
    Fetch ChatID and Email from Buyer table using the ID (primary key).
    Returns dict with 'chat_id' and 'email', or None if not found.
    """
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT ChatID, Email FROM Buyer WHERE ID = %s",
                (buyer_id,)
            )
            result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "chat_id": result["ChatID"],  # may be None if buyer hasn't /start-ed yet
                "email":   result["Email"],
            }
        return None

    except Exception as e:
        print(f"Database error: {e}")
        return None


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

    buyer_id     = message.get("buyerID")
    subject      = message.get("subject")
    message_body = message.get("body")

    # Validate required fields
    if not buyer_id or not subject or not message_body:
        print("Missing buyerID, subject, or body. Skipping notification.")
        return

    # Fetch buyer info (ChatID + Email) from Buyer table
    buyer_info = get_buyer_info(buyer_id)

    if not buyer_info:
        print(f"Could not retrieve buyer info for buyerID: {buyer_id}. Skipping.")
        return

    # ── Send Email ────────────────────────────────────────────────────────────
    send_email(buyer_info["email"], subject, message_body)

    # ── Send Telegram ─────────────────────────────────────────────────────────
    telegram_message = f"*{subject}*\n\n{message_body}"
    send_telegram(buyer_info["chat_id"], telegram_message)

    print(f"Notifications processed for buyerID: {buyer_id}")
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