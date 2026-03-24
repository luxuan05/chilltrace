#!/usr/bin/env python3
"""
telebot.py — Telegram bot that links a buyer's Telegram chat
to their Buyer record by storing the ChatID.

Usage (customer side):
    Customer sends:  /start <buyerID>
    e.g.             /start 1

The bot then saves their Telegram ChatID to the Buyer table.
"""

import os
import pymysql
import pymysql.cursors
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ── MySQL config (set these in your .env / docker-compose environment) ────────
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "your_database")


# ─────────────────────────────────────────────────────────────────────────────
# Database helpers
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


def buyer_exists(buyer_id: str) -> dict:
    """
    Check if the buyerID exists in the Buyer table.
    Returns buyer info dict if found, None if not found.
    """
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT ID, CompanyName, Email FROM Buyer WHERE ID = %s",
                (buyer_id,)
            )
            result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "id": result["ID"],
                "company_name": result["CompanyName"] or "Customer",
                "email": result["Email"],
            }
        return None

    except Exception as e:
        print(f"Error checking buyer existence: {e}")
        return None


def save_chat_id(buyer_id: str, chat_id: int) -> bool:
    """
    Update the Buyer table to store ChatID for the given buyerID.
    """
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE Buyer SET ChatID = %s WHERE ID = %s",
                (chat_id, buyer_id)
            )
            rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        return rows_affected > 0

    except Exception as e:
        print(f"Error saving ChatID: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# /start handler
# ─────────────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start <buyerID>
    Validates the buyerID, then saves the Telegram ChatID to the Buyer table.
    """
    chat_id   = update.effective_chat.id
    user_name = update.effective_user.first_name or "there"
    args      = context.args  # everything after /start

    # ── Guard: buyerID must be provided ──────────────────────────────────────
    if not args:
        await update.message.reply_text(
            "👋 Hi! To receive order notifications, please start with your Buyer ID.\n\n"
            "Example:\n"
            "  /start 1"
        )
        return

    buyer_id = args[0].strip()

    # ── Guard: validate buyerID exists in Buyer table ────────────────────────
    buyer_info = buyer_exists(buyer_id)
    if not buyer_info:
        await update.message.reply_text(
            f"❌ Buyer ID *{buyer_id}* was not found in our system.\n"
            "Please double-check your Buyer ID and try again.",
            parse_mode="Markdown"
        )
        return

    # ── Save ChatID to Buyer table ───────────────────────────────────────────
    success = save_chat_id(buyer_id, chat_id)

    if success:
        print(f"Saved ChatID {chat_id} for buyerID {buyer_id}")
        company_name = buyer_info["company_name"]
        await update.message.reply_text(
            f"✅ Hi *{user_name}*! You're all set.\n\n"
            f"Your account (*{company_name}* - ID: {buyer_id}) is now linked to this chat.\n"
            "You'll receive order status updates here. 🛍️",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "⚠️ Something went wrong while linking your account. "
            "Please try again or contact support."
        )

# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting Telegram bot...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))

    print("Bot is running. Waiting for messages...")
    app.run_polling()