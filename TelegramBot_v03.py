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
    IMAGE_PATH: str = "./telegram_img.png"
    FALLBACK_IMAGE_URL: str = "./logo.png"
    WEBSITE_URL: str = "http://localhost:8000"
    WHITEPAPER_URL: str = "./WHITEPAPER.pdf"
    CACHE_FILE: str = "token_monitor_cache.json"
    LOG_FILE: str = "token_monitor.log"
    BSC_NODE_URL: str = "https://bsc-testnet-rpc.publicnode.com"
    POLLING_INTERVAL: int = 30  # Reduced to 30s for faster checks
    REQUEST_TIMEOUT: int = 10
    MAX_RETRIES: int = 3
    FALLBACK_PRICE: float = 0.0001
    FALLBACK_SUPPLY: float = 1000000
    FALLBACK_NAME: str = "OURTOKEN"
    FALLBACK_SYMBOL: str = "TOKEN"
    FALLBACK_DECIMALS: int = 18

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

# ABIs
TOKEN_ABI = [
    {
        "inputs":[{"internalType":"address","name":"initialOwner","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},
        {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"allowance","type":"uint256"},{"internalType":"uint256","name":"needed","type":"uint256"}],"name":"ERC20InsufficientAllowance","type":"error"},
        {"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"uint256","name":"balance","type":"uint256"},{"internalType":"uint256","name":"needed","type":"uint256"}],"name":"ERC20InsufficientBalance","type":"error"},
        {"inputs":[{"internalType":"address","name":"approver","type":"address"}],"name":"ERC20InvalidApprover","type":"error"},
        {"inputs":[{"internalType":"address","name":"receiver","type":"address"}],"name":"ERC20InvalidReceiver","type":"error"},
        {"inputs":[{"internalType":"address","name":"sender","type":"address"}],"name":"ERC20InvalidSender","type":"error"},{"inputs":[{"internalType":"address","name":"spender","type":"address"}],"name":"ERC20InvalidSpender","type":"error"},
        {"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"OwnableInvalidOwner","type":"error"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"OwnableUnauthorizedAccount","type":"error"},
        {"inputs":[],"name":"INITIAL_SUPPLY","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"renounceOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"}
]

ICO_ABI = [
    {
        "inputs":[],"name":"tokenAmountPerUSD","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"
    },
    {
        "inputs":[],"name":"tokenAddress","outputs":[{"internalType":"contract IERC20","name":"","type":"address"}],"stateMutability":"view","type":"function"
    },
    
    {
        "inputs": [

            {"internalType": "address",
                "name": "recipient",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "paymentType",
                "type": "uint256"
            },
            {
                "internalType": "uint256",
                "name": "tokenAmount",
                "type": "uint256"
            },
            {
                "components": [
                {
                    "internalType": "uint8",
                    "name": "v",
                    "type": "uint8"
                },
                {
                    "internalType": "bytes32",
                    "name": "r",
                    "type": "bytes32"
                },
                {
                    "internalType": "bytes32",
                    "name": "s",
                    "type": "bytes32"
                },
                {
                    "internalType": "uint256",
                    "name": "nonce",S
                    "type": "uint256"
                }
                ],
                "internalType": "struct StoneForm_ICO.Sign",
                "name": "sign",
                "type": "tuple"
            }],
        "name": "buyToken","outputs": [],"stateMutability": "payable","type": "function"
    }  
]

TRANSFER_EVENT_ABI = {
    "anonymous": False,
    "inputs": [
        {"indexed": True, "name": "from", "type": "address"},
        {"indexed": True, "name": "to", "type": "address"},
        {"indexed": False, "name": "value", "type": "uint256"}
    ],
    "name": "Transfer",
    "type": "event"
}

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
                logger.info(f"Cache loaded: {len(self.known_addresses)} addresses, last tx: {self.last_tx_hash}")
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
def get_token_info() -> Tuple[str, str, float, int]:
    try:
        contract = w3.eth.contract(address=Config.TOKEN_ADDRESS, abi=TOKEN_ABI)
        symbol = contract.functions.symbol().call()
        name = contract.functions.name().call()
        initial_supply = contract.functions.INITIAL_SUPPLY().call()
        decimals = contract.functions.decimals().call()
        initial_supply = initial_supply / 10**decimals
        logger.info(f"Token Info - Name: {name}, Symbol: {symbol}, Initial Supply: {initial_supply:,.0f}, Decimals: {decimals}")
        return name, symbol, initial_supply, decimals
    except Web3Exception as e:
        logger.error(f"Error fetching token info for {Config.TOKEN_ADDRESS}: {e}", exc_info=True)
        return Config.FALLBACK_NAME, Config.FALLBACK_SYMBOL, Config.FALLBACK_SUPPLY, Config.FALLBACK_DECIMALS

async def fetch_with_retry(url: str, session: aiohttp.ClientSession, retries: int = Config.MAX_RETRIES) -> Optional[Dict]:
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=Config.REQUEST_TIMEOUT) as response:
                response.raise_for_status()
                data = await response.json()
                logger.debug(f"Fetched data from {url}: {data.get('status')}")
                return data
        except aiohttp.ClientError as e:
            logger.error(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
    return None

async def get_token_transactions(session: aiohttp.ClientSession) -> List[Dict]:
    transactions = []
    # Try txlist endpoint
    url = f"https://api-testnet.bscscan.com/api?module=account&action=txlist&address={Config.ICO_ADDRESS}&sort=desc&apikey={Config.BSCSCAN_API_KEY}"
    data = await fetch_with_retry(url, session)
    if data and data.get("status") == "1" and data.get("result"):
        logger.info(f"Found {len(data['result'])} transactions for ICO_ADDRESS {Config.ICO_ADDRESS} via txlist")
        transactions = data["result"]
    
    # Fallback to tokentx
    if not transactions:
        url = f"https://api-testnet.bscscan.com/api?module=account&action=tokentx&contractaddress={Config.TOKEN_ADDRESS}&address={Config.ICO_ADDRESS}&sort=desc&apikey={Config.BSCSCAN_API_KEY}"
        data = await fetch_with_retry(url, session)
        if data and data.get("status") == "1" and data.get("result"):
            logger.info(f"Found {len(data['result'])} transactions for ICO_ADDRESS {Config.ICO_ADDRESS} via tokentx")
            transactions = data["result"]
        else:
            logger.warning(f"No transactions found via tokentx: {data.get('message', 'Unknown error') if data else 'Request failed'}")
    
    return transactions

@lru_cache(maxsize=1)
def tokenpriceperusd() -> float:
    try:
        contract = w3.eth.contract(address=Config.ICO_ADDRESS, abi=ICO_ABI)
        token_amount_per_usd = contract.functions.tokenAmountPerUSD().call()
        contract_token_address = contract.functions.tokenAddress().call()
        if contract_token_address.lower() != Config.TOKEN_ADDRESS.lower():
            logger.warning(f"ICO contract token address mismatch: {contract_token_address} vs {Config.TOKEN_ADDRESS}")
            return Config.FALLBACK_PRICE
        token_contract = w3.eth.contract(address=Config.TOKEN_ADDRESS, abi=TOKEN_ABI)
        decimals = token_contract.functions.decimals().call()
        if token_amount_per_usd == 0:
            logger.warning("tokenAmountPerUSD is 0")
            return Config.FALLBACK_PRICE
        price_usd = 1 / (token_amount_per_usd / 10**decimals)
        logger.info(f"Token Price: {price_usd:.6f} USD")
        return price_usd
    except Web3Exception as e:
        logger.error(f"Error fetching price for {Config.ICO_ADDRESS}: {e}", exc_info=True)
        return Config.FALLBACK_PRICE

def is_new_holder(from_address: str, cache: Cache) -> bool:
    if not from_address:
        logger.warning("Empty from_address, assuming new holder")
        return True
    logger.debug(f"Checking if {from_address} is a new holder. Known addresses: {list(cache.known_addresses)}")
    if from_address.lower() in [addr.lower() for addr in cache.known_addresses]:
        logger.info(f"Address {from_address} already in cache, marking as existing holder")
        return False
    cache.known_addresses.add(from_address)
    cache.save_cache()
    logger.info(f"Added new holder {from_address} to cache")
    return True

async def get_transfer_event_value(tx_hash: str, decimals: int) -> float:
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        contract = w3.eth.contract(address=Config.TOKEN_ADDRESS, abi=[TRANSFER_EVENT_ABI])
        logs = contract.events.Transfer().process_receipt(receipt)
        for log in logs:
            if log['address'].lower() == Config.TOKEN_ADDRESS.lower():
                value = log['args']['value'] / 10**decimals
                logger.info(f"Found Transfer event in tx {tx_hash}: {value:,.2f} tokens")
                return value
        logger.debug(f"No Transfer event found in tx {tx_hash}")
        return 0.0
    except Web3Exception as e:
        logger.error(f"Error fetching Transfer event for tx {tx_hash}: {e}")
        return 0.0

async def send_to_telegram(
    transaction: Dict,
    initial_supply: float,
    price: float,
    name: str,
    symbol: str,
    decimals: int,
    volume_24h: float,
    cache: Cache
):
    amount_token = int(transaction.get("value", 0)) / 10**decimals if transaction.get("value") else 0.0
    if amount_token == 0.0:
        amount_token = await get_transfer_event_value(transaction["hash"], decimals)
    
    amount_usd = amount_token * price
    holders_count = len(cache.known_addresses)
    new_holder = is_new_holder(transaction.get("from", ""), cache)
    
    message = (
        f"<b>🚀 {name} ({symbol}) 🚀</b>\n\n"
        f"<b>New Transaction Alert 📢</b>\n"
        f"📍 Amount: {amount_token:,.2f} {symbol}\n"
        f"💰 USD Value: ${amount_usd:,.2f}\n"
        f"📈 Price: ${price:.6f}\n"
        f"💸 Initial Supply: {initial_supply:,.0f} {symbol}\n"
        f"👥 Holders: {holders_count:,}\n"
        # f"📊 24h Volume: {volume_24h:,.2f} {symbol}\n"
        f"ℹ️ Status: {'New Holder!' if new_holder else 'Existing Holder'}\n"
        f"⏰ Time: {datetime.fromtimestamp(int(transaction.get('timeStamp', 0))).strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"<a href='https://testnet.bscscan.com/tx/{transaction['hash']}'>View on BscScan</a>\n\n"
        f"<a href='{Config.WEBSITE_URL}'>Website</a> | "
        f"<a href='{Config.WHITEPAPER_URL}'>Whitepaper</a>"
    )

    logger.info(f"Sending Telegram message for tx {transaction['hash']} (length: {len(message)}):\n{message}")

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

        try:
            await bot.send_message(
                chat_id=Config.TELEGRAM_CHANNEL_ID,
                text=message,
                parse_mode="HTML"
            )
            logger.info("Text-only message sent")
        except TelegramError as e:
            logger.error(f"Failed to send text-only message: {e}")

async def calculate_24h_volume(transactions: List[Dict], decimals: int = Config.FALLBACK_DECIMALS) -> float:
    now = int(time.time())
    one_day_ago = now - 24 * 3600
    volume = 0.0
    for tx in transactions:
        if int(tx.get("timeStamp", 0)) >= one_day_ago:
            amount = int(tx.get("value", 0)) / 10**decimals if tx.get("value") else 0.0
            if amount == 0.0:
                amount = await get_transfer_event_value(tx["hash"], decimals)
            volume += amount
    logger.info(f"Calculated 24h volume: {volume:,.2f}")
    return volume

async def main():
    logger.info("Starting token monitoring service...")
    
    if not w3.is_connected():
        logger.error("Failed to connect to BSC node")
        exit(1)

    cache = Cache()
    logger.info(f"Cache initialized: last_tx_hash={cache.last_tx_hash}, known_addresses={len(cache.known_addresses)}")
    name, symbol, initial_supply, decimals = get_token_info()
    logger.info(f"Token info fetched: name={name}, symbol={symbol}, initial_supply={initial_supply}, decimals={decimals}")
    volume_24h = 0

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=ssl.create_default_context(cafile=certifi.where()))
    ) as session:
        while True:
            try:
                logger.debug("Starting main loop iteration")
                transactions = await get_token_transactions(session)
                price = tokenpriceperusd()
                logger.info(f"Price fetched: {price}")
                volume_24h = await calculate_24h_volume(transactions, decimals)

                if transactions:
                    logger.info(f"Processing {len(transactions)} transactions")
                    for tx in transactions[:5]:
                        logger.info(f"Transaction: {tx['hash']}, From: {tx.get('from', 'N/A')}, To: {tx.get('to', 'N/A')}, Value: {tx.get('value', 'N/A')}, Time: {tx.get('timeStamp', 'N/A')}")
                    latest_tx = transactions[0]
                    if latest_tx["hash"] != cache.last_tx_hash:
                        logger.info(f"New transaction detected: {latest_tx['hash']}")
                        await send_to_telegram(
                            latest_tx, initial_supply, price,
                            name, symbol, decimals, volume_24h, cache
                        )
                        cache.last_tx_hash = latest_tx["hash"]
                        cache.save_cache()
                    else:
                        logger.info("No new transactions")
                else:
                    logger.info("No transactions found in this iteration")

                await asyncio.sleep(Config.POLLING_INTERVAL)

            except Exception as e:
                logger.error(f"Main loop error: {e}", exc_info=True)
                await asyncio.sleep(Config.POLLING_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())