import os
import time
import telebot
import requests
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# رسالة الترحيب عند /start
@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "👋 أهلاً بك! البوت شغال الآن. أرسل رابط Instagram لتحميل الفيديو مباشرة.")

# إعداد Chrome لتشغيل Headless على Heroku
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")

# استخدام Service لتجنب خطأ executable_path
service = Service(executable_path=os.environ.get("CHROMEDRIVER_PATH"))
driver = webdriver.Chrome(service=service, options=chrome_options)

@bot.message_handler(func=lambda message: True)
def download_instagram(message):
    urls = message.text.strip().split()  # دعم عدة روابط مفصولة بمسافة
    for url in urls:
        if "instagram.com" not in url:
            bot.reply_to(message, f"❌ هذا ليس رابط Instagram صالح: {url}")
            continue

        bot.reply_to(message, f"⏳ جاري التحميل من SSK: {url}")

        try:
            driver.get("https://sssinstagram.com/ar")
            time.sleep(2)

            input_box = driver.find_element(By.NAME, "url")
            input_box.clear()
            input_box.send_keys(url)

            submit_btn = driver.find_element(By.XPATH, '//button[contains(text(),"Download")]')
            submit_btn.click()
            time.sleep(5)

            download_link = driver.find_element(By.CLASS_NAME, "btn-download").get_attribute("href")

            if download_link:
                file_response = requests.get(download_link)
                file_stream = BytesIO(file_response.content)
                file_stream.name = f"insta_video_{urls.index(url)}.mp4"
                bot.send_document(message.chat.id, file_stream)
            else:
                bot.reply_to(message, f"❌ لم أتمكن من العثور على رابط التحميل: {url}")

        except Exception as e:
            bot.reply_to(message, f"❌ حدث خطأ مع الرابط {url}: {e}")

bot.infinity_polling()
