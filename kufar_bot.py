import asyncio
import logging
import sqlite3
import httpx
from aiogram import Bot

BOT_TOKEN = "8391966929:AAHpBPLoI-slusE73N05HXhfJtTAmqSZDLM"
CHAT_ID = 7140251019

KUFAR_API_URL = "https://api.kufar.by/search-api/v2/search/rendered-paginated?cat=12020&g_lida=true&lang=ru&size=10&sort=lst.d"
CHECK_INTERVAL = 60

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)

def init_db():
    conn = sqlite3.connect("seen_ads.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS ads (ad_id TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

def is_ad_seen(ad_id: str) -> bool:
    conn = sqlite3.connect("seen_ads.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM ads WHERE ad_id = ?", (ad_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def save_ad(ad_id: str):
    conn = sqlite3.connect("seen_ads.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO ads (ad_id) VALUES (?)", (ad_id,))
    conn.commit()
    conn.close()

async def fetch_kufar_ads():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.kufar.by/",
        "Origin": "https://www.kufar.by"
    }
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(KUFAR_API_URL, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("ads", [])
            else:
                logging.error(f"Ошибка запроса: {response.status_code}")
        except Exception as e:
            logging.error(f"Исключение при запросе: {e}")
    return []

async def check_new_ads():
    ads = await fetch_kufar_ads()
    for ad in reversed(ads):
        ad_id = str(ad.get("ad_id"))
        if not is_ad_seen(ad_id):
            subject = ad.get("subject", "Грузоперевозки в Лиде")
            price_byn = ad.get("price_byn", "")
            price_str = f"{int(price_byn) / 100:.2f} BYN" if price_byn and price_byn != "0" else "Договорная"
            link = ad.get("ad_link", "")
            
            message = (
                f"🚛 **Новое объявление (Грузоперевозки Лида)!**\n\n"
                f"📌 **{subject}**\n"
                f"💰 **Цена:** {price_str}\n\n"
                f"🔗 [Посмотреть на Kufar]({link})"
            )
            try:
                await bot.send_message(CHAT_ID, message, parse_mode="Markdown")
                save_ad(ad_id)
                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Ошибка отправки: {e}")

async def main():
    init_db()
    logging.info("Бот запущен!")
    while True:
        await check_new_ads()
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
