import requests
import time
import asyncio
from telegram import Bot
import aiohttp

# Replace these with your own values
ETHERSCAN_API_KEY = "SKR4GZIENU9ZV9MN4BT3IWVAP9ZK15JW21"
TELEGRAM_BOT_TOKEN = "8131473302:AAFxLJ4RPa52SOU2zVMxkPHKjQ0V8mqpTFc"
TELEGRAM_CHANNEL_ID = "-1002609179898"  # Replace with your channel ID
PEPE_TOKEN_CONTRACT = "0xdAC17F958D2ee523a2206206994597C13D831ec7"  # Pepe token contract address
IMAGE_URL = "https://stoneform.io/assets/images/icon/logo.png"  # Replace with a valid image URL (e.g., Pepe token logo)

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

def get_pepe_transactions():
    # Fetch transactions for the Pepe token contract
    url = f"https://api.etherscan.io/api?module=account&action=tokentx&contractaddress={PEPE_TOKEN_CONTRACT}&sort=desc&apikey={ETHERSCAN_API_KEY}"
    response = requests.get(url)
    data = response.json()
    if data["status"] == "1":
        return data["result"]
    else:
        print(f"Error fetching transactions: {data['message']}")
        return []

async def send_to_telegram(transaction):
    # Format the transaction details
    message = (
        f"New Stoneform Token Transaction!\n"  # Changed "Stoneform" to "Pepe" to match the token
        f"From: {transaction['from']}\n"
        f"To: {transaction['to']}\n"
        f"Amount: {int(transaction['value']) / 10**18} PEPE\n"  # Adjust for token decimals
        f"Tx Hash: {transaction['hash']}\n"
        f"View on Etherscan: https://etherscan.io/tx/{transaction['hash']}"
    )

    # Send photo with caption to Telegram channel
    try:
        await bot.send_photo(
            chat_id=TELEGRAM_CHANNEL_ID,
            photo=IMAGE_URL,  # Use the image URL
            caption=message
        )
        print("Message with image sent to Telegram.")
    except Exception as e:
        print(f"Error sending to Telegram: {e}")

async def main():
    print("Monitoring Pepe token transactions...")
    last_tx_hash = None

    while True:
        transactions = get_pepe_transactions()
        if transactions:
            latest_tx = transactions[0]

            if latest_tx["hash"] != last_tx_hash:
                await send_to_telegram(latest_tx)
                last_tx_hash = latest_tx["hash"]

        await asyncio.sleep(60)  # Check every 60 seconds

if __name__ == "__main__":
    asyncio.run(main())