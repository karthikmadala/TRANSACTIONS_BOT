import requests
import time
import asyncio
from telegram import Bot
from telegram.error import TelegramError

# Configuration
BSCSCAN_API_KEY = "SKR4GZIENU9ZV9MN4BT3IWVAP9ZK15JW21"
TELEGRAM_BOT_TOKEN = "8131473302:AAFxLJ4RPa52SOU2zVMxkPHKjQ0V8mqpTFc"
TELEGRAM_CHANNEL_ID = "-1002609179898"
STONEFORM_TOKEN_ADDRESS = "0x6982508145454ce325ddbe47a25d4ec3d2311933"
IMAGE_URL = "https://stoneform.io/assets/images/icon/logo.png"
ETHPLORER_API_KEY = "freekey"  # Replace with your Ethplorer API key for higher limits
STONEFORM_WEBSITE = "https://ico.stoneform.io/"
STONEFORM_WHITEPAPER = "https://stoneform.io/public/pdf/WHITEPAPER.pdf"
# ETHPLORER_TOKEN_URL = f"https://ethplorer.io/address/{STONEFORM_TOKEN_ADDRESS}"  # Add Ethplorer URL

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Store addresses to check for new holders
known_addresses = set()

def get_pepe_transactions():
    url = f"https://api.etherscan.io/api?module=account&action=tokentx&contractaddress={STONEFORM_TOKEN_ADDRESS}&sort=desc&apikey={BSCSCAN_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        if data["status"] == "1":
            return data["result"]
        else:
            print(f"Etherscan API error: {data['message']}")
            return []
    except requests.RequestException as e:
        print(f"Error fetching transactions from Etherscan: {e}")
        return []

def get_pepe_holders_and_supply():
    url = f"https://api.ethplorer.io/getTokenInfo/{STONEFORM_TOKEN_ADDRESS}?apiKey={ETHPLORER_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            print(f"Ethplorer API error: {data['error']['message']}")
            return None, None
        holders = data.get("holdersCount")
        total_supply = int(data.get("totalSupply", 0)) / 10**18 if data.get("totalSupply") else None
        print(f"Ethplorer API Response - Holders: {holders}, Total Supply: {total_supply}")
        return holders, total_supply
    except requests.RequestException as e:
        print(f"Error fetching holders/supply from Ethplorer: {e}")
        return None, None

def get_pepe_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=pepe&vs_currencies=usd"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        price = data.get("pepe", {}).get("usd")
        print(f"CoinGecko API Response - Price: {price}")
        return price
    except requests.RequestException as e:
        print(f"Error fetching price from CoinGecko: {e}")
        return None

def is_new_holder(to_address, transactions):
    if to_address in known_addresses:
        return False
    for tx in transactions:
        known_addresses.add(tx["from"])
        known_addresses.add(tx["to"])
    return to_address not in known_addresses

async def send_to_telegram(transaction, holders_count, total_supply, price):
    amount_pepe = int(transaction["value"]) / 10**18
    amount_usd = amount_pepe * price if price is not None else None

    new_holder = is_new_holder(transaction["to"], [transaction])
    holder_info = "New Holder!" if new_holder else "Existing Holder"

    # Debug: Log values
    print(f"Before message construction - Holders: {holders_count}, Type: {type(holders_count)}, Total Supply: {total_supply}, Price: {price}")

    # Format fields
    holders_text = f"Total Holders: {holders_count:,} 🚀\n" if holders_count is not None else "Total Holders: Unknown 🚀\n"
    supply_text = f"Total Supply: {total_supply:,.0f} PEPE 💸\n" if total_supply is not None else "Total Supply: Unknown 💸\n"
    price_text = f"Price Per Token: ${price:.6f} 📈\n" if price is not None else "Price Per Token: Unknown 📈\n"
    usd_text = f"Value: ${amount_usd:,.2f} 💰\n" if amount_usd is not None else "Value: Unknown 💰\n"

    # Construct message with HTML for clickable links
    message = (
        "<b>🚀 Stoneform Token 🚀</b>\n\n"
        "<b>New Transaction 🚀🚀🚀</b>\n"
        # f"From: <code>{transaction['from']}</code>\n"
        # f"To: <code>{transaction['to']}</code>\n"
        f"Amount: {amount_pepe:,.2f} PEPE 🔥\n"
        f"{usd_text}"
        f"{price_text}"
        f"{supply_text}"
        f"{holders_text}"
        f"Info: {holder_info}\n"
        f"<a href='https://etherscan.io/tx/{transaction['hash']}'>View on Etherscan</a>\n"
        f"\n"
        # f"<a href='{ETHPLORER_TOKEN_URL}'>View on Ethplorer</a>\n"
        f"<a href='{STONEFORM_WEBSITE}'>Website</a> | <a href='{STONEFORM_WHITEPAPER}'>Whitepaper</a>"
    )

    print(f"Final Telegram Message:\n{message}")
    print(f"Message length: {len(message)}")

    # Send message with retry logic
    for attempt in range(3):
        try:
            await bot.send_photo(
                chat_id=TELEGRAM_CHANNEL_ID,
                photo=IMAGE_URL,
                caption=message,
                parse_mode="HTML"  # Enable HTML parsing
            )
            print("Message with image sent to Telegram.")
            return
        except TelegramError as e:
            print(f"Error sending to Telegram (attempt {attempt + 1}/3): {e}")
            if attempt < 2:
                await asyncio.sleep(2)
            else:
                print("Failed to send to Telegram after 3 attempts.")

async def main():
    print("Monitoring Pepe token transactions...")
    last_tx_hash = None
    holders_count, total_supply = None, None
    last_holder_update = 0
    update_interval = 300  # Update every 5 minutes

    while True:
        # Update holders and supply every 5 minutes
        if time.time() - last_holder_update >= update_interval:
            holders_count, total_supply = get_pepe_holders_and_supply()
            last_holder_update = time.time()

        transactions = get_pepe_transactions()
        price = get_pepe_price()

        if transactions:
            latest_tx = transactions[0]
            if latest_tx["hash"] != last_tx_hash:
                await send_to_telegram(latest_tx, holders_count, total_supply, price)
                last_tx_hash = latest_tx["hash"]

        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())