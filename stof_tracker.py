import requests
import time
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from web3 import Web3
import os

# Configuration
BSCSCAN_API_KEY = "6IYJ7I59ZUJQDYE8S44UT8MXB48DFP69VK"
TELEGRAM_BOT_TOKEN = "8131473302:AAFxLJ4RPa52SOU2zVMxkPHKjQ0V8mqpTFc"
TELEGRAM_CHANNEL_ID = "-1002609179898"
ICO_ADDRESS = "0x4408cd3a88C813E34C23bdd1FB57d75df9227003"
TOKEN_ADDRESS = "0xf9847c631ADED64430Ece222798994b88bC8aeDA"
IMAGE_PATH = "./stoneform_telegram_img.png"  # Local image path
FALLBACK_IMAGE_URL = "https://stoneform.io/assets/images/icon/logo.png"
STONEFORM_WEBSITE = "https://ico.stoneform.io/"
STONEFORM_WHITEPAPER = "https://stoneform.io/public/pdf/WHITEPAPER.pdf"

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Initialize Web3 for BSC
w3 = Web3(Web3.HTTPProvider("https://bsc-dataseed.binance.org/"))
if not w3.is_connected():
    print("Error: Failed to connect to BSC node")
    exit(1)

# Store addresses to check for new holders
known_addresses = set()

# Token ABI (for TOKEN_ADDRESS)
TOKEN_ABI = [
    {
        "inputs":[{"internalType":"address","name":"initialOwner","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},
        {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"allowance","type":"uint256"},{"internalType":"uint256","name":"needed","type":"uint256"}],"name":"ERC20InsufficientAllowance","type":"error"},
        {"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"uint256","name":"balance","type":"uint256"},{"internalType":"uint256","name":"needed","type":"uint256"}],"name":"ERC20InsufficientBalance","type":"error"},
        {"inputs":[{"internalType":"address","name":"approver","type":"address"}],"name":"ERC20InvalidApprover","type":"error"},
        {"inputs":[{"internalType":"address","name":"receiver","type":"address"}],"name":"ERC20InvalidReceiver","type":"error"},
        {"inputs":[{"internalType":"address","name":"sender","type":"address"}],"name":"ERC20InvalidSender","type":"error"},
        {"inputs":[{"internalType":"address","name":"spender","type":"address"}],"name":"ERC20InvalidSpender","type":"error"},
        {"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"OwnableInvalidOwner","type":"error"},
        {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"OwnableUnauthorizedAccount","type":"error"},
        {"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"owner","type":"address"},{"indexed":True,"internalType":"address","name":"spender","type":"address"},{"indexed":False,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},
        {"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"previousOwner","type":"address"},{"indexed":True,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},
        {"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"from","type":"address"},{"indexed":True,"internalType":"address","name":"to","type":"address"},{"indexed":False,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},
        {"inputs":[],"name":"INITIAL_SUPPLY","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"renounceOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"}
]

# ICO Contract ABI (minimal for tokenAmountPerUSD)
ICO_ABI = [
    {
        "inputs":[],"name":"tokenAmountPerUSD","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"
    },
    {
        "inputs":[],"name":"tokenAddress","outputs":[{"internalType":"contract IERC20","name":"","type":"address"}],"stateMutability":"view","type":"function"
    }
]

def get_token_info():
    try:
        contract = w3.eth.contract(address=TOKEN_ADDRESS, abi=TOKEN_ABI)
        symbol = contract.functions.symbol().call()
        name = contract.functions.name().call()
        initial_supply = contract.functions.INITIAL_SUPPLY().call()
        decimals = contract.functions.decimals().call()
        initial_supply = initial_supply / 10**decimals
        print(f"Token Info - Name: {name}, Symbol: {symbol}, Initial Supply: {initial_supply:,.0f}, Decimals: {decimals}")
        return name, symbol, initial_supply, decimals
    except Exception as e:
        print(f"Error fetching token info: {e}")
        return None, None, None, None

def get_token_transactions():
    url = f"https://api.bscscan.com/api?module=account&action=tokentx&contractaddress={ICO_ADDRESS}&sort=desc&apikey={BSCSCAN_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "1" and data["result"]:
            print(f"Transactions found for ICO_ADDRESS: {ICO_ADDRESS}")
            return data["result"]
        else:
            print(f"BscScan API error for ICO_ADDRESS {ICO_ADDRESS}: {data.get('message', 'No transactions found')}")
            return []
    except requests.RequestException as e:
        print(f"Error fetching transactions from BscScan for ICO_ADDRESS {ICO_ADDRESS}: {e}")
        return []

def tokenpriceperusd():
    try:
        contract = w3.eth.contract(address=ICO_ADDRESS, abi=ICO_ABI)
        token_amount_per_usd = contract.functions.tokenAmountPerUSD().call()
        # Verify token address matches
        contract_token_address = contract.functions.tokenAddress().call()
        if contract_token_address.lower() != TOKEN_ADDRESS.lower():
            print(f"Warning: ICO contract token address ({contract_token_address}) does not match TOKEN_ADDRESS ({TOKEN_ADDRESS})")
            return None
        # Get decimals from TOKEN_ADDRESS
        token_contract = w3.eth.contract(address=TOKEN_ADDRESS, abi=TOKEN_ABI)
        decimals = token_contract.functions.decimals().call()
        # Convert tokens per USD to USD per token
        if token_amount_per_usd == 0:
            print("Price: tokenAmountPerUSD is 0")
            return 0
        price_usd = 1 / (token_amount_per_usd / 10**decimals)
        print(f"ICO Contract Price - Tokens per USD: {token_amount_per_usd}, Price: {price_usd} USD")
        return price_usd
    except Exception as e:
        print(f"Error fetching price from ICO contract: {e}")
        return None

def get_token_holders():
    url = f"https://api.bscscan.com/api?module=token&action=tokenholderlist&contractaddress={TOKEN_ADDRESS}&apikey={BSCSCAN_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "1" and data["result"]:
            holders_count = len(data["result"])
            print(f"BscScan API Response - Holders: {holders_count}")
            return holders_count
        else:
            print(f"BscScan API error for TOKEN_ADDRESS {TOKEN_ADDRESS}: {data.get('message', 'No holders found')}")
            return None
    except requests.RequestException as e:
        print(f"Error fetching holders from BscScan: {e}")
        return None

def is_new_holder(to_address, transactions):
    if to_address in known_addresses:
        return False
    for tx in transactions:
        known_addresses.add(tx["from"])
        known_addresses.add(tx["to"])
    return to_address not in known_addresses

async def send_to_telegram(transaction, holders_count, initial_supply, price, name, symbol, decimals):
    amount_token = int(transaction["value"]) / 10**decimals
    amount_usd = amount_token * price if price is not None else None

    new_holder = is_new_holder(transaction["to"], [transaction])
    holder_info = "New Holder!" if new_holder else "Existing Holder"

    print(f"Before message construction - Holders: {holders_count}, Initial Supply: {initial_supply}, Price: {price}")

    holders_text = f"Total Holders: {holders_count:,} 🚀\n" if holders_count is not None else "Total Holders: Unknown 🚀\n"
    supply_text = f"Initial Supply: {initial_supply:,.0f} {symbol} 💸\n" if initial_supply is not None and symbol else "Initial Supply: Unknown 💸\n"
    price_text = f"Price Per Token: ${price:.6f} 📈\n" if price is not None else "Price Per Token: Unknown 📈\n"
    usd_text = f"Value: ${amount_usd:,.2f} 💰\n" if amount_usd is not None else "Value: Unknown 💰\n"

    message = (
        f"<b>🚀 {name or 'Stoneform'} Token ({symbol or 'TOKEN'}) 🚀</b>\n\n"
        "<b>New Transaction 🚀🚀🚀</b>\n"
        f"Amount: {amount_token:,.2f} {symbol or 'TOKEN'} 🔥\n"
        f"{usd_text}"
        f"{price_text}"
        f"{supply_text}"
        f"{holders_text}"
        f"Info: {holder_info}\n"
        f"<a href='https://bscscan.com/tx/{transaction['hash']}'>View on BscScan</a>\n"
        f"\n"
        f"<a href='{STONEFORM_WEBSITE}'>Website</a> | <a href='{STONEFORM_WHITEPAPER}'>Whitepaper</a>"
    )

    print(f"Final Telegram Message:\n{message}")
    print(f"Message length: {len(message)}")

    for attempt in range(3):
        try:
            if os.path.exists(IMAGE_PATH):
                with open(IMAGE_PATH, "rb") as photo:
                    await bot.send_photo(
                        chat_id=TELEGRAM_CHANNEL_ID,
                        photo=photo,
                        caption=message,
                        parse_mode="HTML"
                    )
                print("Message with local image sent to Telegram.")
            else:
                await bot.send_photo(
                    chat_id=TELEGRAM_CHANNEL_ID,
                    photo=FALLBACK_IMAGE_URL,
                    caption=message,
                    parse_mode="HTML"
                )
                print("Message with fallback URL image sent to Telegram.")
            return
        except TelegramError as e:
            print(f"Error sending to Telegram (attempt {attempt + 1}/3): {e}")
            if attempt < 2:
                await asyncio.sleep(2)
            else:
                print("Failed to send to Telegram with image after 3 attempts.")
                try:
                    await bot.send_message(
                        chat_id=TELEGRAM_CHANNEL_ID,
                        text=message,
                        parse_mode="HTML"
                    )
                    print("Text-only message sent to Telegram.")
                    return
                except TelegramError as e:
                    print(f"Error sending text-only message to Telegram: {e}")

async def main():
    print("Monitoring token transactions on BSC...")
    last_tx_hash = None
    holders_count, initial_supply = None, None
    name, symbol, initial_supply, decimals = get_token_info()
    last_holder_update = 0
    update_interval = 300  # Update every 5 minutes

    while True:
        if time.time() - last_holder_update >= update_interval:
            holders_count = get_token_holders()
            last_holder_update = time.time()

        transactions = get_token_transactions()
        price = tokenpriceperusd()

        if transactions:
            latest_tx = transactions[0]
            if latest_tx["hash"] != last_tx_hash:
                await send_to_telegram(latest_tx, holders_count, initial_supply, price, name, symbol, decimals)
                last_tx_hash = latest_tx["hash"]

        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())