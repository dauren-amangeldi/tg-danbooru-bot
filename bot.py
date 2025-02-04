import os
import requests
import logging
import asyncio
import html
from urllib.parse import urlparse
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загружаем переменные окружения из файла token.env (файл должен быть в той же папке, что и скрипт)
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, "token.env")
load_dotenv(env_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")
print("BOT_TOKEN =", BOT_TOKEN)  # Для отладки (можно удалить после проверки)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден. Убедитесь, что он указан в файле token.env")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_danbooru_data(url: str):
    """
    Функция для получения данных с Danbooru.
    Принимает URL вида:
      https://danbooru.donmai.us/posts/4963030?q=yoga_pants+shorts+
    Извлекает числовой ID из пути и делает запрос к API Danbooru.
    Возвращает кортеж (image_url, tags) или (None, None) в случае ошибки.
    """
    try:
        # Разбираем URL
        parsed_url = urlparse(url)
        # Ожидается, что путь имеет вид /posts/4963030
        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) < 2 or path_parts[0] != "posts":
            logging.error("Некорректный формат URL. Ожидается /posts/<id>")
            return None, None

        image_id = path_parts[1]
        logging.info(f"Извлечен ID: {image_id}")

        # Формируем API URL для получения информации об изображении
        api_url = f"https://danbooru.donmai.us/posts/{image_id}.json"
        logging.info(f"API URL: {api_url}")

        response = requests.get(api_url)
        if response.status_code != 200:
            logging.error(f"Ошибка запроса к Danbooru API: статус {response.status_code}")
            return None, None

        data = response.json()
        image_url = data.get("file_url")
        tags = data.get("tag_string", "").split()
        return image_url, tags
    except Exception as e:
        logging.error(f"Ошибка при обработке URL: {e}")
        return None, None

@dp.message(F.text.startswith("https://danbooru.donmai.us/posts/"))
async def handle_danbooru_link(message: types.Message):
    """
    Хэндлер для сообщений, начинающихся с ссылки Danbooru.
    Извлекает данные об изображении и тегах, пытается отправить изображение с тегами.
    Если отправка изображения не удалась, отправляет сообщение с тегами.
    """
    url = message.text.strip()
    logging.info(f"Получена ссылка: {url}")

    image_url, tags = get_danbooru_data(url)
    if not image_url:
        await message.reply("Ошибка: не удалось получить данные с Danbooru.")
        return

    # Формируем подпись с тегами (ограничим до первых 50 тегов)
    tags_text = ", ".join(tags[:50]) if tags else "отсутствуют"
    # Экранируем динамический текст, чтобы избежать ошибок HTML-парсера
    escaped_tags_text = html.escape(tags_text)
    caption = f"🔖 <b>Теги</b>: {escaped_tags_text}"

    logging.info(f"Попытка отправить изображение, image_url: {image_url}")
    logging.info(f"Caption: {caption}")

    try:
        await bot.send_photo(message.chat.id, image_url, caption=caption, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Ошибка отправки фото: {e}")
        # Если не удалось отправить изображение, отправляем сообщение только с тегами
        await message.reply(f"Не удалось отправить изображение, но вот теги:\n{caption}", parse_mode=ParseMode.HTML)

async def main():
    logging.info("Бот запущен. Ожидание сообщений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
