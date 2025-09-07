import telebot
from telebot import types
import threading
import time
import random
from firebase_init import *  # استدعاء كل دوال ومتغيرات Firebase

# -------- إعدادات البوت --------
BOT_TOKEN = "توكن_البوت_هنا"  # ضع توكن البوت
OWNER_ID = 123456789  # ضع معرف المالك هنا
bot = telebot.TeleBot(BOT_TOKEN)

# -------- متغيرات مساعدة --------
user_add_channel = {}
active_pairs = {}
completed_checks = {}
active_users = set()

# -------- أزرار --------
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("أضف قناة", "حذف قناة")
    markup.add("الاشتراك بالقنوات", "تعليمات البوت")
    if int(user_id) == OWNER_ID:
        markup.add("📢 اذاعة", "إعدادات البوت", "إضافة قناة إجبارية")
    return markup

def back_button():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("رجوع")
    return markup

# -------- تسجيل أي مستخدم نشط --------
@bot.message_handler(func=lambda m: True)
def ensure_active_user(message):
    user_id = str(message.chat.id)
    if user_id not in active_users:
        active_users.add(user_id)
    if not user_exists(user_id):
        add_user(user_id)
        bot.send_message(OWNER_ID, f"👤 مستخدم جديد دخل البوت:\nID: {user_id}\nالاسم: {message.from_user.first_name}\n@{message.from_user.username}")

# -------- /start --------
@bot.message_handler(commands=['start'])
def start(message):
    user_name = message.from_user.first_name
    bot.send_message(message.chat.id,
                     f"👋 مرحباً {user_name}!\nاضغط على الأزرار لاختيار الإجراء.",
                     reply_markup=main_menu(message.chat.id))

# -------- أضف قناة --------
@bot.message_handler(func=lambda m: m.text == "أضف قناة")
def add_channel_prompt(message):
    bot.send_message(message.chat.id, "📩 أرسل رابط قناتك (مثال: @mychannel)\n⚠️ يجب رفع البوت أدمن أولاً!", reply_markup=back_button())
    user_add_channel[message.chat.id] = "add_channel"

@bot.message_handler(func=lambda m: m.chat.id in user_add_channel)
def receive_channel(message):
    user_id = str(message.chat.id)
    action = user_add_channel.get(message.chat.id)
    if message.text == "رجوع":
        user_add_channel.pop(message.chat.id)
        bot.send_message(message.chat.id, "تم الإلغاء", reply_markup=main_menu(message.chat.id))
        return

    if action == "add_channel":
        channel = message.text.strip()
        try:
            chat_member = bot.get_chat_member(channel, bot.get_me().id)
            if chat_member.status not in ["administrator", "creator"]:
                bot.send_message(message.chat.id, "❌ يجب رفع البوت أدمن في القناة قبل الإضافة.")
                return
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ خطأ: {e}")
            return

        add_channel(user_id, channel)
        user_add_channel.pop(message.chat.id)
        bot.send_message(message.chat.id, f"✅ تم إضافة قناتك: {channel}", reply_markup=main_menu(message.chat.id))

# -------- إضافة قناة إجبارية للمالك --------
@bot.message_handler(func=lambda m: m.text == "إضافة قناة إجبارية" and m.chat.id == OWNER_ID)
def add_mandatory_channel(message):
    bot.send_message(message.chat.id, "📩 أرسل رابط القناة الإجبارية للمستخدمين (مثال: @mustsub)", reply_markup=back_button())
    user_add_channel[message.chat.id] = "mandatory_channel"

@bot.message_handler(func=lambda m: m.chat.id in user_add_channel)
def receive_mandatory_channel(message):
    action = user_add_channel.get(message.chat.id)
    if action == "mandatory_channel":
        if message.text == "رجوع":
            user_add_channel.pop(message.chat.id)
            bot.send_message(message.chat.id, "تم الإلغاء", reply_markup=main_menu(message.chat.id))
            return
        channel = message.text.strip()
        try:
            chat_member = bot.get_chat_member(channel, bot.get_me().id)
            if chat_member.status not in ["administrator", "creator"]:
                bot.send_message(message.chat.id, "❌ يجب رفع البوت أدمن في القناة قبل الإضافة.")
                return
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ خطأ: {e}")
            return
        set_mandatory_channel(channel)
        user_add_channel.pop(message.chat.id)
        bot.send_message(message.chat.id, f"✅ تم تعيين القناة الإجبارية: {channel}", reply_markup=main_menu(message.chat.id))

# -------- الاشتراك بالقنوات مع تحقق الاشتراك الإجباري --------
def check_mandatory(user_id):
    mandatory_channel = get_mandatory_channel()
    if not mandatory_channel:
        return True
    try:
        member = bot.get_chat_member(mandatory_channel, int(user_id))
        return member.status in ["member", "creator", "administrator"]
    except:
        return False

def start_exchange(user_id):
    all_users = get_all_users()
    available_users = [uid for uid in all_users
                       if uid != user_id
                       and get_user_channels(uid)
                       and uid not in active_pairs.values()]
    if not available_users:
        bot.send_message(int(user_id), "⏳ لا توجد قنوات متاحة حالياً، حاول لاحقاً.")
        return
    partner_id = random.choice(available_users)
    active_pairs[user_id] = partner_id
    active_pairs[partner_id] = user_id

    user_channel = get_user_channels(user_id)[0]
    partner_channel = get_user_channels(partner_id)[0]

    markup = types.InlineKeyboardMarkup()
    btn_user_sub = types.InlineKeyboardButton("🔗 اشترك في القناة الأخرى", url=f"https://t.me/{partner_channel.strip('@')}")
    btn_partner_sub = types.InlineKeyboardButton("🔗 اشترك في قناتك", url=f"https://t.me/{user_channel.strip('@')}")
    btn_check = types.InlineKeyboardButton("✅ تحقق الاشتراك", callback_data=f"check_{user_id}_{partner_id}")
    btn_next = types.InlineKeyboardButton("⏭ التالي", callback_data=f"next_{user_id}")
    markup.add(btn_user_sub, btn_partner_sub)
    markup.add(btn_check, btn_next)

    bot.send_message(int(user_id),
                     f"تم اختيار قناة للتبادل:\n\nقناة الآخر: @{partner_channel}\nقناتك: @{user_channel}",
                     reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "الاشتراك بالقنوات")
def subscribe_channels(message):
    user_id = str(message.chat.id)
    if not get_user_channels(user_id):
        bot.send_message(message.chat.id, "⚠️ يجب إضافة قناة أولاً قبل بدء التبادل.", reply_markup=main_menu(message.chat.id))
        return
    if not check_mandatory(user_id):
        bot.send_message(message.chat.id,
                         f"⚠️ يجب الاشتراك أولاً بالقناة الإلزامية: @{get_mandatory_channel()}",
                         reply_markup=main_menu(message.chat.id))
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
        partner_channel = get_user_channels(partner_id)[0]
        user_member = bot.get_chat_member(partner_channel, int(user_id))
        if user_member.status not in ["member", "creator", "administrator"]:
            bot.answer_callback_query(call.id, "❌ يجب الاشتراك أولاً")
            return
        completed_checks[key] = True
        bot.answer_callback_query(call.id, "✅ تم التحقق من الاشتراك!")
        bot.send_message(int(partner_id), f"🔔 المستخدم @{call.from_user.username} اشترك في قناتك: @{partner_channel}")
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
    # -------- إزالة الزوج الحالي من القوائم النشطة --------
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
                user_channels = get_user_channels(user_id)
                partner_channels = get_user_channels(partner_id)
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
                    bot.send_message(int(partner_id),
                                     f"⚠️ المستخدم @{user_id} غادر قناتك @{partner_channel}.\nقناته الخاصة: @{user_channel}")
                    active_pairs.pop(user_id, None)
                    active_pairs.pop(partner_id, None)
                    completed_checks.pop(f"{user_id}_{partner_id}", None)

                if not partner_in_user:
                    bot.send_message(int(user_id),
                                     f"⚠️ المستخدم @{partner_id} غادر قناتك @{user_channel}.\nقناته الخاصة: @{partner_channel}")
                    active_pairs.pop(user_id, None)
                    active_pairs.pop(partner_id, None)
                    completed_checks.pop(f"{user_id}_{partner_id}", None)

            except:
                continue
        time.sleep(30)

# تشغيل مراقبة المغادرة في خيط مستقل
threading.Thread(target=monitor_leave, daemon=True).start()

# -------- تشغيل البوت --------
bot.infinity_polling()
