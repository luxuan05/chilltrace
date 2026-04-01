#!/usr/bin/env python3
"""
telebot.py — Telegram bot that links a buyer's Telegram chat
to their Buyer record by storing the ChatID.

Usage (customer side):
    1. Customer sends:  /start
    2. Bot asks for Buyer ID
    3. Customer replies with their Buyer ID
    4. Bot validates and saves ChatID to Buyer table
"""

import asyncio
import os
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from dotenv import load_dotenv

load_dotenv()  # Load .env file into os.environ
BUYER_SERVICE_URL = os.getenv("BUYER_SERVICE_URL", "http://localhost:5012")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ── Conversation state ────────────────────────────────────────────────────────
WAITING_FOR_BUYER_ID = 0


def buyer_exists(buyer_id: str) -> dict:
    try:
        response = requests.get(f"{BUYER_SERVICE_URL}/buyer/{buyer_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "id":           data.get("ID"),
                "company_name": data.get("CompanyName") or "Customer",
                "email":        data.get("Email"),
            }
        return None
    except Exception as e:
        print(f"Error checking buyer existence: {e}")
        return None


def save_chat_id(buyer_id: str, chat_id: int) -> bool:
    try:
        response = requests.put(
            f"{BUYER_SERVICE_URL}/buyer/{buyer_id}",
            json={"ChatID": str(chat_id)},
            timeout=10,
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error saving ChatID: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Conversation handlers
# ─────────────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Step 1 — Customer sends /start.
    Bot greets them and asks for their Buyer ID.
    """
    user_name = update.effective_user.first_name or "there"

    await update.message.reply_text(
        f"👋 Hi *{user_name}*! Welcome to our order notification service.\n\n"
        "Please enter your *Buyer ID* to link your account:",
        parse_mode="Markdown"
    )

    return WAITING_FOR_BUYER_ID


async def receive_buyer_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Step 2 — Customer replies with their Buyer ID.
    Bot validates it and saves the ChatID to the Buyer table.
    """
    chat_id  = update.effective_chat.id
    buyer_id = update.message.text.strip()

    # ── Guard: must be a number ───────────────────────────────────────────────
    if not buyer_id.isdigit():
        await update.message.reply_text(
            "❌ That doesn't look like a valid Buyer ID. Please enter a number.\n"
            "Try again or send /cancel to exit."
        )
        return WAITING_FOR_BUYER_ID

    # ── Validate buyerID exists in Buyer table ────────────────────────────────
    buyer_info = buyer_exists(buyer_id)
    if not buyer_info:
        await update.message.reply_text(
            f"❌ Buyer ID *{buyer_id}* was not found in our system.\n"
            "Please double-check your Buyer ID and try again, or send /cancel to exit.",
            parse_mode="Markdown"
        )
        return WAITING_FOR_BUYER_ID

    # ── Save ChatID to Buyer table ────────────────────────────────────────────
    success = save_chat_id(buyer_id, chat_id)

    if success:
        print(f"Saved ChatID {chat_id} for buyerID {buyer_id}")
        company_name = buyer_info["company_name"]
        await update.message.reply_text(
            f"✅ You're all set!\n\n"
            f"Your account (*{company_name}* - ID: {buyer_id}) is now linked to this chat.\n"
            "You'll receive order status updates here. 🛍️",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "⚠️ Something went wrong while linking your account. "
            "Please try again or contact support."
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Customer sends /cancel — exits the conversation."""
    await update.message.reply_text(
        "Cancelled. Send /start whenever you're ready to link your account."
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
# Info
# ─────────────────────────────────────────────────────────────────────────────
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /info - Display bot information
    """
    await update.message.reply_text(
        "ℹ️ This bot links your Telegram account to your Buyer profile.\n\n"
        "Commands:\n"
        "  /start - Link your account\n"
        "  /info - Show this message\n"
        "  /cancel - Cancel current conversation"
    )

# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    print("Starting Telegram bot...")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_BUYER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_buyer_id)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("info", info))

    # Manually manage the bot lifecycle instead of run_polling()
    async with app:
        await app.start()
        print("Bot is running. Waiting for messages...")
        await app.updater.start_polling()

        # Keep running until interrupted
        await asyncio.Event().wait()

        await app.updater.stop()
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())