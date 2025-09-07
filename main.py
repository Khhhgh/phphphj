import telebot, threading, time, random, json, os
from telebot import types

# -------- إعدادات البوت --------
BOT_TOKEN = "7432842437:AAFfcMPNfHyB6JkwStp-_21pfewxyCmf01c"
OWNER_ID = 1310488710
bot = telebot.TeleBot(BOT_TOKEN)

DB_FILE = "channels.json"
lock = threading.Lock()

# -------- بيانات التشغيل --------
user_add_channel = {}
queue = []
active_pairs = {}
completed_exchanges = {}  # سجل التبادلات لكل زوج
last_channel_used = {}     # لتجنب تكرار نفس القناة للشريك نفسه

# -------- تحميل / حفظ قاعدة البيانات --------
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        db = json.load(f)
else:
    db = {"users": {}, "banned": {}}
    with open(DB_FILE, "w") as f:
        json.dump(db,f,indent=4)

def save_db():
    with open(DB_FILE,"w") as f:
        json.dump(db,f,indent=4)

# -------- أزرار رئيسية --------
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ أضف قناة","❌ حذف قناة")
    markup.add("🔗 الاشتراك بالقنوات")
    return markup

def back_button():
    return types.ReplyKeyboardMarkup(resize_keyboard=True).add("رجوع")

# -------- /start --------
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f"👋 مرحباً {message.from_user.first_name}!\nاختر إجراء:", reply_markup=main_menu())

    # إشعار للمالك عند دخول مستخدم جديد
    user_id = str(message.chat.id)
    if user_id not in db["users"]:
        db["users"][user_id] = []
        save_db()
        bot.send_message(OWNER_ID,
            f"👤 مستخدم جديد دخل البوت:\n"
            f"ID: {user_id}\n"
            f"الاسم: {message.from_user.first_name}\n"
            f"@{message.from_user.username}")

# -------- إضافة قناة مع تحقق من صحتها --------
@bot.message_handler(func=lambda m: m.text=="➕ أضف قناة")
def add_channel(m):
    bot.send_message(m.chat.id,"📩 أرسل رابط القناة (مثال: @mychannel):",reply_markup=back_button())
    db["users"].setdefault(str(m.chat.id), [])
    user_add_channel[m.chat.id] = "add_channel"

@bot.message_handler(func=lambda m: m.chat.id in user_add_channel)
def receive_channel(m):
    uid = str(m.chat.id)
    if m.text=="رجوع":
        user_add_channel.pop(m.chat.id,None)
        bot.send_message(m.chat.id,"تم الإلغاء",reply_markup=main_menu())
        return
    
    channel = m.text.strip()
    
    try:
        # تحقق من وجود القناة على تيليجرام
        chat = bot.get_chat(channel)
        # تحقق من أن البوت مشرف فيها
        member = bot.get_chat_member(channel, bot.get_me().id)
        if member.status not in ["administrator","creator"]:
            bot.send_message(m.chat.id,"❌ يجب رفع البوت أدمن في القناة أولاً")
            return
    except Exception as e:
        bot.send_message(m.chat.id,f"⚠️ القناة غير صحيحة أو لا يمكن الوصول إليها: {e}")
        return

    if channel in db["users"][uid]:
        bot.send_message(m.chat.id,"⚠️ القناة موجودة مسبقاً",reply_markup=main_menu())
        return
    
    db["users"][uid].append(channel)
    save_db()
    bot.send_message(m.chat.id,f"✅ تمت إضافة القناة: {channel}",reply_markup=main_menu())
    user_add_channel.pop(m.chat.id,None)
    with lock:
        if uid not in queue and uid not in active_pairs: queue.append(uid)

# -------- حذف قناة --------
@bot.message_handler(func=lambda m: m.text=="❌ حذف قناة")
def delete_channel(m):
    uid = str(m.chat.id)
    chans = db["users"].get(uid,[])
    if not chans: bot.send_message(m.chat.id,"لا توجد قنوات",reply_markup=main_menu()); return
    markup=types.ReplyKeyboardMarkup(resize_keyboard=True)
    for c in chans: markup.add(c)
    markup.add("رجوع")
    bot.send_message(m.chat.id,"اختر قناة للحذف:",reply_markup=markup)
    user_add_channel[m.chat.id] = "delete_channel"

@bot.message_handler(func=lambda m: m.chat.id in user_add_channel and user_add_channel[m.chat.id]=="delete_channel")
def remove_channel(m):
    uid = str(m.chat.id)
    if m.text=="رجوع": user_add_channel.pop(m.chat.id,None); bot.send_message(m.chat.id,"تم الإلغاء",reply_markup=main_menu()); return
    if m.text in db["users"].get(uid,[]):
        db["users"][uid].remove(m.text); save_db()
        bot.send_message(m.chat.id,f"✅ تم حذف: {m.text}",reply_markup=main_menu())
    else: bot.send_message(m.chat.id,"⚠️ القناة غير موجودة",reply_markup=main_menu())
    user_add_channel.pop(m.chat.id,None)

# -------- الاشتراك بالقنوات --------
@bot.message_handler(func=lambda m: m.text=="🔗 الاشتراك بالقنوات")
def start_exchange(m):
    uid = str(m.chat.id)
    banned_until = db.get("banned",{}).get(uid,0)
    if time.time() < banned_until:
        remaining = int((banned_until - time.time())/60)
        bot.send_message(m.chat.id,f"❌ تم حظرك من التبادل.\n⏳ تبقى {remaining} دقيقة",reply_markup=main_menu())
        return
    elif uid in db.get("banned",{}):
        db["banned"].pop(uid)
        save_db()

    if not db["users"].get(uid):
        bot.send_message(m.chat.id,"⚠️ أضف قناة أولاً",reply_markup=main_menu()); return

    with lock:
        if uid not in queue and uid not in active_pairs:
            queue.append(uid)
            bot.send_message(m.chat.id, "⏳ تم إضافتك لقائمة الانتظار، سيتم بدء التبادل عند توفر شريك.", reply_markup=main_menu())
        match_partners()

def match_partners():
    while len(queue) >= 2:
        u1, u2 = queue.pop(0), queue.pop(0)
        active_pairs[u1] = u2
        active_pairs[u2] = u1
        completed_exchanges.pop((u1,u2),None)
        completed_exchanges.pop((u2,u1),None)
        send_exchange(u1,u2)
        send_exchange(u2,u1)

def send_exchange(uid,partner):
    partner_channels = db["users"].get(partner,["@example"])
    last_used = last_channel_used.get((uid,partner))
    available = [ch for ch in partner_channels if ch != last_used]
    if not available: available = partner_channels
    ch = random.choice(available)
    last_channel_used[(uid,partner)] = ch

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔗 قناة الشريك",url=f"https://t.me/{ch.strip('@')}"))
    markup.add(types.InlineKeyboardButton("✅ تحقق الاشتراك",callback_data=f"check_{uid}_{partner}"))
    markup.add(types.InlineKeyboardButton("⏭ التالي",callback_data=f"next_{uid}"))
    bot.send_message(int(uid),f"🔁 تبادل:\nقناة الشريك: @{ch}",reply_markup=markup)

# -------- تحقق الاشتراك --------
@bot.callback_query_handler(func=lambda c:c.data.startswith("check_"))
def check_sub(c):
    _,uid,partner=c.data.split("_")
    try:
        partner_channels = db["users"].get(partner,["@example"])
        ch = random.choice(partner_channels)
        member = bot.get_chat_member(ch,int(uid))
        if member.status not in ["member","creator","administrator"]:
            db.setdefault("banned",{})[uid] = time.time() + 900
            save_db()
            bot.answer_callback_query(c.id,"❌ لم تشترك، تم حظرك لمدة 15 دقيقه")
            with lock:
                queue[:] = [x for x in queue if x != uid]
                pid = active_pairs.pop(uid,None)
                if pid: active_pairs.pop(pid,None)
            return
        completed_exchanges[(uid,partner)] = True
        bot.answer_callback_query(c.id,"✅ تم الاشتراك!")
    except:
        bot.answer_callback_query(c.id,"⚠️ خطأ تحقق الاشتراك")

# -------- التالي --------
@bot.callback_query_handler(func=lambda c:c.data.startswith("next_"))
def next_exchange(c):
    uid = c.data.split("_")[1]
    partner = active_pairs.get(uid)
    if not partner: bot.answer_callback_query(c.id,"⚠️ لا يوجد شريك"); return
    if not completed_exchanges.get((uid,partner)):
        bot.answer_callback_query(c.id,"❌ تحقق الاشتراك أولاً"); return
    with lock:
        active_pairs.pop(uid,None)
        active_pairs.pop(partner,None)
        completed_exchanges.pop((uid,partner),None)
        queue.append(uid)
        queue.append(partner)
    bot.answer_callback_query(c.id,"⏭ جاري اختيار شريك جديد...")
    match_partners()

# -------- تشغيل البوت --------
bot.infinity_polling(timeout=10, long_polling_timeout=5)
