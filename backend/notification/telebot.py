#!/usr/bin/env python3
"""
telebot.py — Telegram bot that links a buyer's Telegram chat
to their Buyer record by storing the ChatID.

Usage (customer side):
    1. Customer sends:  /start
    2. Bot asks for registered email
    3. Customer replies with their email
    4. Bot validates and saves ChatID to Buyer table via Buyer service
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

load_dotenv()

TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN")
BUYER_SERVICE_URL = os.getenv("BUYER_SERVICE_URL", "http://buyer:5012")

# ── Conversation state ────────────────────────────────────────────────────────
WAITING_FOR_EMAIL = 0


# ─────────────────────────────────────────────────────────────────────────────
# Buyer service helpers
# ─────────────────────────────────────────────────────────────────────────────

def find_buyer_by_email(email: str) -> dict:
    """Find a buyer by email via the Buyer atomic service."""
    try:
        response = requests.get(f"{BUYER_SERVICE_URL}/buyer", timeout=10)
        if response.status_code == 200:
            for buyer in response.json():
                if buyer.get("Email", "").lower() == email.lower():
                    return {
                        "id":           buyer.get("ID"),
                        "company_name": buyer.get("CompanyName") or "Customer",
                        "email":        buyer.get("Email"),
                    }
        return None
    except Exception as e:
        print(f"Error finding buyer by email: {e}")
        return None


def save_chat_id(buyer_id: int, chat_id: int) -> bool:
    """Save ChatID to Buyer table via the Buyer atomic service."""
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
    """Step 1 — Customer sends /start. Bot asks for their registered email."""
    user_name = update.effective_user.first_name or "there"
    await update.message.reply_text(
        f"👋 Hi *{user_name}*! Welcome to our order notification service.\n\n"
        "Please enter your *registered email address* to link your account:",
        parse_mode="Markdown"
    )
    return WAITING_FOR_EMAIL


async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 2 — Customer replies with their email. Bot validates and saves ChatID."""
    chat_id = update.effective_chat.id
    email   = update.message.text.strip()

    # Basic email format check
    if "@" not in email or "." not in email:
        await update.message.reply_text(
            "❌ That doesn't look like a valid email address.\n"
            "Try again or send /cancel to exit."
        )
        return WAITING_FOR_EMAIL

    # Validate email exists in Buyer table
    buyer_info = find_buyer_by_email(email)
    if not buyer_info:
        await update.message.reply_text(
            f"❌ No account found for *{email}*.\n"
            "Please double-check your email and try again, or send /cancel to exit.",
            parse_mode="Markdown"
        )
        return WAITING_FOR_EMAIL

    # Save ChatID via Buyer atomic service
    success = save_chat_id(buyer_info["id"], chat_id)

    if success:
        print(f"Saved ChatID {chat_id} for buyer email {email}")
        await update.message.reply_text(
            f"✅ You're all set!\n\n"
            f"Your account (*{buyer_info['company_name']}*) is now linked to this chat.\n"
            "You'll receive order status updates here. 🛍️",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "⚠️ Something went wrong while linking your account. "
            "Please try again or contact support."
        )
        return WAITING_FOR_EMAIL

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Customer sends /cancel — exits the conversation."""
    await update.message.reply_text(
        "Cancelled. Send /start whenever you're ready to link your account."
    )
    return ConversationHandler.END


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/info — Display bot information."""
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
            WAITING_FOR_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("info", info))

    async with app:
        await app.start()
        print("Bot is running. Waiting for messages...")
        await app.updater.start_polling()
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())