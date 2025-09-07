import telebot
from telebot import types
import json
import os
import random
import threading
import time

# -------- إعدادات البوت --------
BOT_TOKEN = "7432842437:AAFfcMPNfHyB6JkwStp-_21pfewxyCmf01c"
OWNER_ID = 1310488710  # ضع هنا معرف مالك البوت
bot = telebot.TeleBot(BOT_TOKEN)

# -------- قاعدة البيانات --------
DB_FILE = "channels.json"
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        db = json.load(f)
else:
    db = {"users": {}}
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

# -------- متغيرات مساعدة --------
user_add_channel = {}
active_pairs = {}
completed_checks = {}
active_users = set()
mandatory_channel = None  # القناة الإلزامية

# -------- دالة إرسال آمن --------
def safe_send(user_id, text, reply_markup=None):
    try:
        bot.send_message(int(user_id), text, reply_markup=reply_markup)
    except Exception as e:
        print(f"⚠️ خطأ عند إرسال رسالة للمستخدم {user_id}: {e}")

# -------- أزرار --------
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("أضف قناة", "حذف قناة")
    markup.add("الاشتراك بالقنوات", "تعليمات البوت")
    if user_id == OWNER_ID:
        markup.add("📢 اذاعة", "إعدادات البوت", "إضافة قناة إجبارية")
    return markup

def back_button():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("رجوع")
    return markup

# -------- تسجيل أي مستخدم نشط (آمن) --------
@bot.message_handler(func=lambda m: True)
def ensure_active_user(message):
    # تجاهل الرسائل الخاصة بالأوامر أو الأزرار
    commands_and_buttons = [
        "/start", "أضف قناة", "حذف قناة", "الاشتراك بالقنوات", "تعليمات البوت",
        "📢 اذاعة", "إعدادات البوت", "إضافة قناة إجبارية", "رجوع"
    ]
    if message.text in commands_and_buttons:
        return
    user_id = str(message.chat.id)
    if user_id not in active_users:
        active_users.add(user_id)
    if user_id not in db["users"]:
        db["users"][user_id] = []
        save_db()
        safe_send(OWNER_ID, f"👤 مستخدم جديد دخل البوت:\nID: {user_id}\nالاسم: {message.from_user.first_name}\n@{message.from_user.username}")

# -------- /start --------
@bot.message_handler(commands=['start'])
def start(message):
    user_name = message.from_user.first_name
    safe_send(message.chat.id,
              f"👋 مرحباً {user_name}!\nاضغط على الأزرار لاختيار الإجراء.",
              reply_markup=main_menu(message.chat.id))

# -------- أضف قناة --------
@bot.message_handler(func=lambda m: m.text == "أضف قناة")
def add_channel_prompt(message):
    safe_send(message.chat.id, "📩 أرسل رابط قناتك (مثال: @mychannel)\n⚠️ يجب رفع البوت أدمن أولاً!", reply_markup=back_button())
    user_add_channel[message.chat.id] = "add_channel"

# -------- إضافة قناة إجبارية للمالك --------
@bot.message_handler(func=lambda m: m.text == "إضافة قناة إجبارية" and m.chat.id == OWNER_ID)
def set_mandatory_channel(message):
    safe_send(message.chat.id, "📩 أرسل رابط القناة الإلزامية (مثال: @mandatorychannel)", reply_markup=back_button())
    user_add_channel[message.chat.id] = "mandatory_channel"

# -------- حذف قناة --------
@bot.message_handler(func=lambda m: m.text == "حذف قناة")
def delete_channel_prompt(message):
    user_id = str(message.chat.id)
    if user_id not in db["users"] or not db["users"][user_id]:
        safe_send(message.chat.id, "⚠️ لا توجد قنوات لحذفها.", reply_markup=main_menu(message.chat.id))
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for ch in db["users"][user_id]:
        markup.add(ch)
    markup.add("رجوع")
    user_add_channel[message.chat.id] = "delete_channel"
    safe_send(message.chat.id, "اختر القناة التي تريد حذفها:", reply_markup=markup)

# -------- استقبال أي قناة (إضافة/حذف/إلزامية) --------
@bot.message_handler(func=lambda m: m.chat.id in user_add_channel)
def handle_channel_actions(message):
    user_id = str(message.chat.id)
    action = user_add_channel.get(message.chat.id)

    if message.text == "رجوع":
        user_add_channel.pop(message.chat.id)
        safe_send(message.chat.id, "تم الإلغاء", reply_markup=main_menu(message.chat.id))
        return

    if action == "add_channel":
        channel = message.text.strip()
        try:
            chat_member = bot.get_chat_member(channel, bot.get_me().id)
            if chat_member.status not in ["administrator", "creator"]:
                safe_send(message.chat.id, "❌ يجب رفع البوت أدمن في القناة قبل الإضافة.")
                return
        except Exception as e:
            safe_send(message.chat.id, f"⚠️ خطأ: {e}")
            return
        if user_id not in db["users"]:
            db["users"][user_id] = []
        if channel in db["users"][user_id]:
            safe_send(message.chat.id, "⚠️ القناة مضافة مسبقاً.")
            return
        db["users"][user_id].append(channel)
        save_db()
        user_add_channel.pop(message.chat.id)
        safe_send(message.chat.id, f"✅ تم إضافة قناتك: {channel}", reply_markup=main_menu(message.chat.id))

    elif action == "mandatory_channel" and message.chat.id == OWNER_ID:
        global mandatory_channel
        channel = message.text.strip()
        try:
            chat_member = bot.get_chat_member(channel, bot.get_me().id)
            if chat_member.status not in ["administrator", "creator"]:
                safe_send(message.chat.id, "❌ يجب رفع البوت أدمن في القناة قبل الإضافة.")
                return
        except Exception as e:
            safe_send(message.chat.id, f"⚠️ خطأ: {e}")
            return
        mandatory_channel = channel
        user_add_channel.pop(message.chat.id)
        safe_send(message.chat.id, f"✅ تم تعيين القناة الإلزامية: {channel}", reply_markup=main_menu(message.chat.id))

    elif action == "delete_channel":
        if message.text in db["users"].get(user_id, []):
            db["users"][user_id].remove(message.text)
            save_db()
            safe_send(message.chat.id, f"✅ تم حذف القناة: {message.text}", reply_markup=main_menu(message.chat.id))
        else:
            safe_send(message.chat.id, "⚠️ القناة غير موجودة.", reply_markup=main_menu(message.chat.id))
        user_add_channel.pop(message.chat.id)

# -------- التحقق من الاشتراك بالقناة الإلزامية --------
def check_mandatory(user_id):
    if not mandatory_channel:
        return True
    try:
        member = bot.get_chat_member(mandatory_channel, int(user_id))
        return member.status in ["member", "creator", "administrator"]
    except:
        return False

# -------- بدء التبادل --------
def start_exchange(user_id):
    for uid in list(active_pairs.keys()):
        pid = active_pairs[uid]
        key = f"{uid}_{pid}"
        if completed_checks.get(key):
            active_pairs.pop(uid)
    available_users = [uid for uid in db["users"] 
                       if uid != user_id 
                       and uid in active_users
                       and db["users"][uid] 
                       and uid not in active_pairs.values()]
    if not available_users:
        safe_send(user_id, "⏳ لا توجد قنوات متاحة حالياً، حاول لاحقاً.")
        return
    partner_id = random.choice(available_users)
    active_pairs[user_id] = partner_id
    active_pairs[partner_id] = user_id
    user_channel = db["users"][user_id][0]
    partner_channel = db["users"][partner_id][0]

    markup = types.InlineKeyboardMarkup()
    btn_user_sub = types.InlineKeyboardButton("🔗 اشترك في القناة الأخرى", url=f"https://t.me/{partner_channel.strip('@')}")
    btn_partner_sub = types.InlineKeyboardButton("🔗 اشترك في قناتك", url=f"https://t.me/{user_channel.strip('@')}")
    btn_check = types.InlineKeyboardButton("✅ تحقق الاشتراك", callback_data=f"check_{user_id}_{partner_id}")
    btn_next = types.InlineKeyboardButton("⏭ التالي", callback_data=f"next_{user_id}")
    markup.add(btn_user_sub, btn_partner_sub)
    markup.add(btn_check, btn_next)

    safe_send(user_id,
              f"تم اختيار قناة للتبادل:\n\nقناة الآخر: @{partner_channel}\nقناتك: @{user_channel}",
              reply_markup=markup)

# -------- الاشتراك بالقنوات --------
@bot.message_handler(func=lambda m: m.text == "الاشتراك بالقنوات")
def subscribe_channels(message):
    user_id = str(message.chat.id)
    if user_id not in db["users"] or not db["users"][user_id]:
        safe_send(message.chat.id, "⚠️ يجب إضافة قناة أولاً قبل بدء التبادل.", reply_markup=main_menu(message.chat.id))
        return
    if not check_mandatory(user_id):
        safe_send(message.chat.id, f"⚠️ يجب الاشتراك أولاً بالقناة الإلزامية: @{mandatory_channel}", reply_markup=main_menu(message.chat.id))
        return
    start_exchange(user_id)

# -------- تحقق الاشتراك صارم --------
@bot.callback_query_handler(func=lambda call: call.data.startswith("check_"))
def check_subscription(call):
    parts = call.data.split("_")
    user_id, partner_id = parts[1], parts[2]
    key = f"{user_id}_{partner_id}"
    if completed_checks.get(key):
        bot.answer_callback_query(call.id, "تم التحقق مسبقًا.")
        return
    try:
        partner_channel = db["users"][partner_id][0]
        try:
            user_member = bot.get_chat_member(partner_channel, int(user_id))
            if user_member.status not in ["member", "creator", "administrator"]:
                bot.answer_callback_query(call.id, "❌ يجب الاشتراك أولاً")
                return
        except:
            bot.answer_callback_query(call.id, "❌ المستخدم لم يشترك أو لا يمكن التحقق.")
            return
        completed_checks[key] = True
        bot.answer_callback_query(call.id, "✅ تم التحقق من الاشتراك!")
        safe_send(partner_id, f"🔔 المستخدم @{call.from_user.username} اشترك في قناتك: @{partner_channel}")
    except Exception as e:
        bot.answer_callback_query(call.id, f"⚠️ خطأ: {e}")

# -------- زر التالي --------
@bot.callback_query_handler(func=lambda call: call.data.startswith("next_"))
def next_exchange(call):
    user_id = call.data.split("_")[1]
    if user_id not in active_pairs:
        bot.answer_callback_query(call.id, "⚠️ لا يوجد زوج نشط حالياً.")
        return
    partner_id = active_pairs[user_id]
    key = f"{user_id}_{partner_id}"
    if not completed_checks.get(key):
        bot.answer_callback_query(call.id, "❌ يجب التحقق من الاشتراك قبل الضغط التالي.")
        return
    active_pairs.pop(user_id, None)
    active_pairs.pop(partner_id, None)
    completed_checks.pop(key, None)
    bot.answer_callback_query(call.id, "⏭ جاري اختيار قناة جديدة...")
    start_exchange(user_id)

# -------- مراقبة المغادرة فعلية --------
def monitor_leave():
    while True:
        for user_id in list(active_pairs.keys()):
            partner_id = active_pairs.get(user_id)
            if not partner_id:
                continue
            try:
                user_channels = db["users"].get(user_id, [])
                partner_channels = db["users"].get(partner_id, [])
                if not user_channels or not partner_channels:
                    continue
                user_channel = user_channels[0]
                partner_channel = partner_channels[0]

                try:
                    user_member = bot.get_chat_member(partner_channel, int(user_id))
                    user_in_partner = user_member.status in ["member", "creator", "administrator"]
                except:
                    user_in_partner = False

                try:
                    partner_member = bot.get_chat_member(user_channel, int(partner_id))
                    partner_in_user = partner_member.status in ["member", "creator", "administrator"]
                except:
                    partner_in_user = False

                if not user_in_partner:
                    safe_send(partner_id,
                              f"⚠️ المستخدم @{user_id} غادر قناتك @{partner_channel}.\nقناته الخاصة: @{user_channel}")
                    active_pairs.pop(user_id, None)
                    active_pairs.pop(partner_id, None)
                    completed_checks.pop(f"{user_id}_{partner_id}", None)

                if not partner_in_user:
                    safe_send(user_id,
                              f"⚠️ المستخدم @{partner_id} غادر قناتك @{user_channel}.\nقناته الخاصة: @{partner_channel}")
                    active_pairs.pop(user_id, None)
                    active_pairs.pop(partner_id, None)
                    completed_checks.pop(f"{user_id}_{partner_id}", None)
            except:
                continue
        time.sleep(30)

threading.Thread(target=monitor_leave, daemon=True).start()

# -------- تشغيل البوت --------
bot.infinity_polling()
