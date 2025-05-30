import requests
import time
import asyncio
import logging
import certifi
import ssl
import json
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError, RetryAfter
from web3 import Web3
from web3.exceptions import Web3Exception
import os
from typing import Dict, List, Optional, Tuple
import aiohttp
from dataclasses import dataclass
from functools import lru_cache

# Configuration class
@dataclass
class Config:
    BSCSCAN_API_KEY: str = "6IYJ7I59ZUJQDYE8S44UT8MXB48DFP69VK"
    TELEGRAM_BOT_TOKEN: str = "8131473302:AAFxLJ4RPa52SOU2zVMxkPHKjQ0V8mqpTFc"
    TELEGRAM_CHANNEL_ID: str = "-1002609179898"
    ICO_ADDRESS: str = "0x0cc0f0Ce7611227d23B8779a95f91Faac913Bd2d"
    TOKEN_ADDRESS: str = "0x8586c16c8054CB50fD09d287a288d33E2765bBb9"
    IMAGE_PATH: str = "./stoneform_telegram_img.png"
    FALLBACK_IMAGE_URL: str = "https://stoneform.io/assets/images/icon/logo.png"
    STONEFORM_WEBSITE: str = "https://ico.stoneform.io/"
    STONEFORM_WHITEPAPER: str = "https://stoneform.io/public/pdf/WHITEPAPER.pdf"
    CACHE_FILE: str = "token_monitor_cache.json"
    LOG_FILE: str = "token_monitor.log"
    BSC_NODE_URL: str = "https://bsc-dataseed.binance.org/"
    POLLING_INTERVAL: int = 60
    HOLDER_UPDATE_INTERVAL: int = 300
    REQUEST_TIMEOUT: int = 10
    MAX_RETRIES: int = 3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Web3 and Telegram bot
w3 = Web3(Web3.HTTPProvider(Config.BSC_NODE_URL))
bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)

# ABIs (unchanged from original)
TOKEN_ABI = [
    {
        "inputs":[{"internalType":"address","name":"initialOwner","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},
        {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"allowance","type":"uint256"},{"internalType":"uint256","name":"needed","type":"uint256"}],"name":"ERC20InsufficientAllowance","type":"error"},
        {"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"uint256","name":"balance","type":"uint256"},{"internalType":"uint256","name":"needed","type":"uint256"}],"name":"ERC20InsufficientBalance","type":"error"},
        {"inputs":[{"internalType":"address","name":"approver","type":"address"}],"name":"ERC20InvalidApprover","type":"error"},
        {"inputs":[{"internalType":"address","name":"receiver","type":"address"}],"name":"ERC20InvalidReceiver","type":"error"},
        {"inputs":[{"internalType":"address","name":"sender","type":"address"}],"name":"ERC20InvalidSender","type":"error"},{"inputs":[{"internalType":"address","name":"spender","type":"address"}],"name":"ERC20InvalidSpender","type":"error"},
        {"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"OwnableInvalidOwner","type":"error"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"OwnableUnauthorizedAccount","type":"error"},
        {"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"pure","type":"function"},
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

ICO_ABI = [
    {
        "inputs":[],"name":"tokenAmountPerUSD","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"
    },
    {
        "inputs":[],"name":"tokenAddress","outputs":[{"internalType":"contract IERC20","name":"","type":"address"}],"stateMutability":"view","type":"function"
    }
]

class Cache:
    def __init__(self):
        self.cache_file = Config.CACHE_FILE
        self.known_addresses = set()
        self.last_tx_hash = None
        self.load_cache()

    def load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.known_addresses = set(data.get('known_addresses', []))
                    self.last_tx_hash = data.get('last_tx_hash')
                logger.info("Cache loaded successfully")
        except Exception as e:
            logger.error(f"Error loading cache: {e}")

    def save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({
                    'known_addresses': list(self.known_addresses),
                    'last_tx_hash': self.last_tx_hash
                }, f)
            logger.info("Cache saved successfully")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

@lru_cache(maxsize=1)
def get_token_info() -> Tuple[Optional[str], Optional[str], Optional[float], Optional[int]]:
    try:
        contract = w3.eth.contract(address=Config.TOKEN_ADDRESS, abi=TOKEN_ABI)
        symbol = contract.functions.symbol().call()
        name = contract.functions.name().call()
        initial_supply = contract.functions.totalSupply().call()
        decimals = contract.functions.decimals().call()
        initial_supply = initial_supply / 10**decimals
        logger.info(f"Token Info - Name: {name}, Symbol: {symbol}, Initial Supply: {initial_supply:,.0f}")
        return name, symbol, initial_supply, decimals
    except Web3Exception as e:
        logger.error(f"Error fetching token info: {e}")
        return None, None, None, None

async def fetch_with_retry(url: str, session: aiohttp.ClientSession, retries: int = Config.MAX_RETRIES) -> Optional[Dict]:
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=Config.REQUEST_TIMEOUT) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
    return None

async def get_token_transactions(session: aiohttp.ClientSession) -> List[Dict]:
    url = f"https://api.bscscan.com/api?module=account&action=tokentx&contractaddress={Config.ICO_ADDRESS}&sort=desc&apikey={Config.BSCSCAN_API_KEY}"
    data = await fetch_with_retry(url, session)
    if data and data.get("status") == "1" and data.get("result"):
        logger.info(f"Found {len(data['result'])} transactions for ICO_ADDRESS")
        return data["result"]
    logger.warning(f"No transactions found for ICO_ADDRESS: {data.get('message', 'Unknown error') if data else 'Request failed'}")
    return []

@lru_cache(maxsize=1)
def tokenpriceperusd() -> Optional[float]:
    try:
        contract = w3.eth.contract(address=Config.ICO_ADDRESS, abi=ICO_ABI)
        token_amount_per_usd = contract.functions.tokenAmountPerUSD().call()
        contract_token_address = contract.functions.tokenAddress().call()
        if contract_token_address.lower() != Config.TOKEN_ADDRESS.lower():
            logger.warning(f"ICO contract token address mismatch: {contract_token_address} vs {Config.TOKEN_ADDRESS}")
            return None
        token_contract = w3.eth.contract(address=Config.TOKEN_ADDRESS, abi=TOKEN_ABI)
        decimals = token_contract.functions.decimals().call()
        if token_amount_per_usd == 0:
            logger.warning("tokenAmountPerUSD is 0")
            return 0
        price_usd = 1 / (token_amount_per_usd / 10**decimals)
        logger.info(f"Token Price: {price_usd:.6f} USD")
        return price_usd
    except Web3Exception as e:
        logger.error(f"Error fetching price: {e}")
        return None

async def get_token_holders(session: aiohttp.ClientSession) -> Optional[int]:
    url = f"https://api.bscscan.com/api?module=token&action=tokenholderlist&contractaddress={Config.TOKEN_ADDRESS}&apikey={Config.BSCSCAN_API_KEY}"
    data = await fetch_with_retry(url, session)
    if data and data.get("status") == "1" and data.get("result"):
        holders_count = len(data["result"])
        logger.info(f"Current holders: {holders_count}")
        return holders_count
    logger.warning(f"No holders found: {data.get('message', 'Unknown error') if data else 'Request failed'}")
    return None

def is_new_holder(to_address: str, transactions: List[Dict], cache: Cache) -> bool:
    if to_address in cache.known_addresses:
        return False
    for tx in transactions:
        cache.known_addresses.add(tx["from"])
        cache.known_addresses.add(tx["to"])
    return to_address not in cache.known_addresses

async def send_to_telegram(
    transaction: Dict,
    holders_count: Optional[int],
    initial_supply: Optional[float],
    price: Optional[float],
    name: Optional[str],
    symbol: Optional[str],
    decimals: Optional[int],
    volume_24h: float
):
    amount_token = int(transaction["value"]) / 10**decimals if decimals else 0
    amount_usd = amount_token * price if price is not None and decimals else None
    new_holder = is_new_holder(transaction["to"], [transaction], cache)
    
    # Enhanced message with more details
    message = (
        f"<b>🚀 {name or 'Stoneform'} Token ({symbol or 'TOKEN'}) 🚀</b>\n\n"
        f"<b>New Transaction Alert 📢</b>\n"
        f"📍 Amount: {amount_token:,.2f} {symbol or 'TOKEN'}\n"
        f"💰 USD Value: ${amount_usd:,.2f}\n" if amount_usd is not None else "💰 USD Value: Unknown\n"
        f"📈 Price: ${price:.6f}\n" if price is not None else "📈 Price: Unknown\n"
        f"💸 Initial Supply: {initial_supply:,.0f} {symbol or 'TOKEN'}\n" if initial_supply else "💸 Initial Supply: Unknown\n"
        f"👥 Holders: {holders_count:,}\n" if holders_count is not None else "👥 Holders: Unknown\n"
        f"📊 24h Volume: {volume_24h:,.2f} {symbol or 'TOKEN'}\n"
        f"ℹ️ Status: {'New Holder!' if new_holder else 'Existing Holder'}\n"
        f"⏰ Time: {datetime.fromtimestamp(int(transaction['timeStamp'])).strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"<a href='https://bscscan.com/tx/{transaction['hash']}'>View on BscScan</a>\n\n"
        f"<a href='{Config.STONEFORM_WEBSITE}'>Website</a> | "
        f"<a href='{Config.STONEFORM_WHITEPAPER}'>Whitepaper</a>"
    )

    logger.info(f"Sending Telegram message (length: {len(message)}):\n{message}")

    async with aiohttp.ClientSession() as session:
        for attempt in range(Config.MAX_RETRIES):
            try:
                if os.path.exists(Config.IMAGE_PATH):
                    with open(Config.IMAGE_PATH, "rb") as photo:
                        await bot.send_photo(
                            chat_id=Config.TELEGRAM_CHANNEL_ID,
                            photo=photo,
                            caption=message,
                            parse_mode="HTML"
                        )
                    logger.info("Message sent with local image")
                else:
                    await bot.send_photo(
                        chat_id=Config.TELEGRAM_CHANNEL_ID,
                        photo=Config.FALLBACK_IMAGE_URL,
                        caption=message,
                        parse_mode="HTML"
                    )
                    logger.info("Message sent with fallback image")
                return
            except RetryAfter as e:
                logger.warning(f"Rate limit hit, retrying after {e.retry_after} seconds")
                await asyncio.sleep(e.retry_after)
            except TelegramError as e:
                logger.error(f"Telegram error (attempt {attempt + 1}/{Config.MAX_RETRIES}): {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Unexpected error sending to Telegram: {e}")
                break

        # Fallback to text-only message
        try:
            await bot.send_message(
                chat_id=Config.TELEGRAM_CHANNEL_ID,
                text=message,
                parse_mode="HTML"
            )
            logger.info("Text-only message sent")
        except TelegramError as e:
            logger.error(f"Failed to send text-only message: {e}")

async def calculate_24h_volume(transactions: List[Dict], decimals: int) -> float:
    now = int(time.time())
    one_day_ago = now - 24 * 3600
    volume = sum(
        int(tx["value"]) / 10**decimals
        for tx in transactions
        if int(tx["timeStamp"]) >= one_day_ago
    )
    return volume

async def main():
    logger.info("Starting token monitoring service...")
    
    if not w3.is_connected():
        logger.error("Failed to connect to BSC node")
        exit(1)

    cache = Cache()
    name, symbol, initial_supply, decimals = get_token_info()
    last_holder_update = 0
    holders_count = None
    volume_24h = 0

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=ssl.create_default_context(cafile=certifi.where()))
    ) as session:
        while True:
            try:
                if time.time() - last_holder_update >= Config.HOLDER_UPDATE_INTERVAL:
                    holders_count = await get_token_holders(session)
                    last_holder_update = time.time()

                transactions = await get_token_transactions(session)
                price = tokenpriceperusd()
                volume_24h = await calculate_24h_volume(transactions, decimals or 18)

                if transactions:
                    latest_tx = transactions[0]
                    if latest_tx["hash"] != cache.last_tx_hash:
                        await send_to_telegram(
                            latest_tx, holders_count, initial_supply, price,
                            name, symbol, decimals, volume_24h
                        )
                        cache.last_tx_hash = latest_tx["hash"]
                        cache.save_cache()

                await asyncio.sleep(Config.POLLING_INTERVAL)

            except Exception as e:
                logger.error(f"Main loop error: {e}")
                await asyncio.sleep(Config.POLLING_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())