import requests
import time
import asyncio
from telegram import Bot
from telegram.error import TelegramError

# Configuration
BSCSCAN_API_KEY = "6IYJ7I59ZUJQDYE8S44UT8MXB48DFP69VK"
TELEGRAM_BOT_TOKEN = "8131473302:AAFxLJ4RPa52SOU2zVMxkPHKjQ0V8mqpTFc"
TELEGRAM_CHANNEL_ID = "-1002609179898"
STONEFORM_TOKEN_ADDRESS = "0x0cc0f0Ce7611227d23B8779a95f91Faac913Bd2d"  # Replace with actual BEP-20 token address
IMAGE_URL = "./stonefrom_telegram_img.png"
STONEFORM_WEBSITE = "https://ico.stoneform.io/"
STONEFORM_WHITEPAPER = "https://stoneform.io/public/pdf/WHITEPAPER.pdf"

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Store addresses to check for new holders
known_addresses = set()

def get_token_transactions():
    url = f"https://api-testnet.bscscan.com/api?module=account&action=tokentx&contractaddress={STONEFORM_TOKEN_ADDRESS}&sort=desc&apikey={BSCSCAN_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "1":
            return data["result"]
        else:
            print(f"BscScan API error: {data['message']}")
            return []
    except requests.RequestException as e:
        print(f"Error fetching transactions from BscScan: {e}")
        return []

def get_token_supply():
    url = f"https://api-testnet.bscscan.com/api?module=stats&action=tokensupply&contractaddress={STONEFORM_TOKEN_ADDRESS}&apikey={BSCSCAN_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "1":
            total_supply = int(data["result"]) / 10**18 if data["result"] else None
            print(f"BscScan API Response - Total Supply: {total_supply}")
            return total_supply
        else:
            print(f"BscScan API error: {data['message']}")
            return None
    except requests.RequestException as e:
        print(f"Error fetching supply from BscScan: {e}")
        return None

def get_stof_price_from_dexscreener():
    token_address = "0x8586c16c8054CB50fD09d287a288d33E2765bBb9"
    url = f"https://api-testnet.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "pairs" in data and len(data["pairs"]) > 0:
            # Get first pair (usually the most active one)
            pair = data["pairs"][0]
            price = float(pair["priceUsd"])
            print(f"STOF Token Price from Dexscreener: ${price}")
            return price
        else:
            print("STOF token not found on Dexscreener.")
            return None
    except requests.RequestException as e:
        print(f"Error fetching STOF price from Dexscreener: {e}")
        return None


def get_token_price():
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

async def send_to_telegram(transaction, total_supply, price):
    amount_token = int(transaction["value"]) / 10**18
    amount_usd = amount_token * price if price is not None else None

    new_holder = is_new_holder(transaction["to"], [transaction])
    holder_info = "New Holder!" if new_holder else "Existing Holder"

    # Format fields
    supply_text = f"Total Supply: {total_supply:,.0f} TOKEN 💸\n" if total_supply is not None else "Total Supply: Unknown 💸\n"
    price_text = f"Price Per Token: ${price:.6f} 📈\n" if price is not None else "Price Per Token: Unknown 📈\n"
    usd_text = f"Value: ${amount_usd:,.2f} 💰\n" if amount_usd is not None else " busesValue: Unknown 💰\n"

    # Construct message with HTML for clickable links
    message = (
        "<b>🚀 Stoneform Token 🚀</b>\n\n"
        "<b>New Transaction 🚀🚀🚀</b>\n"
        f"Amount: {amount_token:,.2f} TOKEN 🔥\n"
        f"{usd_text}"
        f"{price_text}"
        f"{supply_text}"
        f"Info: {holder_info}\n"
        f"<a href='https://bscscan.com/tx/{transaction['hash']}'>View on BscScan</a>\n"
        f"\n"
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
                parse_mode="HTML"
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
    print("Monitoring token transactions on BSC...")
    last_tx_hash = None
    total_supply = None
    last_supply_update = 0
    update_interval = 300  # Update every 5 minutes

    while True:
        # Update supply every 5 minutes
        if time.time() - last_supply_update >= update_interval:
            total_supply = get_token_supply()
            last_supply_update = time.time()

        transactions = get_token_transactions()
        price = get_token_price()

        if transactions:
            latest_tx = transactions[0]
            if latest_tx["hash"] != last_tx_hash:
                await send_to_telegram(latest_tx, total_supply, price)
                last_tx_hash = latest_tx["hash"]

        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())