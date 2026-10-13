import logging
import asyncio
import os
from datetime import datetime, timedelta
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web

# កំណត់ Logging
logging.basicConfig(level=logging.INFO)

# កំណត់ Token និង ID ផ្សេងៗនៅទីនេះ
API_TOKEN = '8708079718:AAGWdfzl0cZRUweZsy_Mt891Up2_BwLT61o'
CHANNEL_ID = '-1003707490949'      # ID របស់ Private Channel VIP របស់អ្នក
ADMIN_GROUP_ID = '-1003904405834'  # ID របស់ Admin Group សម្រាប់ទទួលបង្កាន់ដៃ
ADMIN_CONTACT = "https://t.me/munnyneak_movie?direct"

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
scheduler = AsyncIOScheduler()

QR_PATH = "qr.jpg"
ABOUT_BANNER_PATH = "About us Banner.png"
DB_PATH = "subscriptions.db"

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            expiry_date TEXT,
            plan_name TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_subscription_custom(user_id: int, username: str, full_name: str, delta: timedelta, plan_name: str):
    expiry = datetime.now() + delta
    expiry_str = expiry.strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO subscriptions (user_id, username, full_name, expiry_date, plan_name)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, full_name, expiry_str, plan_name))
    conn.commit()
    conn.close()

def add_subscription(user_id: int, username: str, full_name: str, days: int, plan_name: str):
    add_subscription_custom(user_id, username, full_name, timedelta(days=days), plan_name)

# --- BOT HANDLERS ---
@dp.message(Command("start", "verify"))
async def cmd_start(message: types.Message):
    user_name = message.from_user.full_name or "អតិថិជន"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 ទទួលសាកល្បងឥតគិតថ្លៃ ២សប្តាហ៍", callback_data="claim_free_trial")
    builder.button(text="ℹ️ អំពីពួកយើង", callback_data="about_us")
    builder.button(text="💎 ជ្រើសរើសកញ្ចប់ VIP (Pricing)", callback_data="select_plan")
    builder.button(text="📞 ទំនាក់ទំនងផ្ទាល់", url=ADMIN_CONTACT)
    builder.adjust(1)
    
    text = (
        f"👋 សូមស្វាគមន៍ <b>{user_name}</b> មកកាន់ប្រព័ន្ធ VIP របស់យើង!\n\n"
        f"🌟 <b>Ai Legend VIP</b>\n"
        f"────────────────────────\n"
        f"🎁 <b>ពិសេស!</b> សម្រាប់សមាជិកចាស់និងថ្មី អាចចុចទទួលសិទ្ធិសាកល្បងមើលរឿងដោយឥតគិតថ្លៃរយៈពេល <b>២សប្តាហ៍ (១៤ថ្ងៃ)</b> ភ្លាមៗនៅខាងក្រោម៖"
    )
    await message.answer(text, reply_markup=builder.as_markup())

# --- មុខងារសម្រាប់សមាជិកចុចទទួល Free Trial ២សប្តាហ៍ ---
@dp.callback_query(F.data == "claim_free_trial")
async def process_free_trial(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_full_name = callback.from_user.full_name or "សមាជិក"
    username = callback.from_user.username or ""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT expiry_date, plan_name FROM subscriptions WHERE user_id = ?", (user_id,))
    existing = cursor.fetchone()
    
    if existing:
        await callback.answer("⚠️ អ្នកបានចុះឈ្មោះ ឬទទួលបានកញ្ចប់សមាជិកក្នុងប្រព័ន្ធរួចរាល់ហើយ!", show_alert=True)
        conn.close()
        return

    try:
        chat_member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if chat_member.status in ["left", "kicked"]:
            await callback.answer("❌ អ្នកត្រូវតែជាសមាជិកក្នុង Channel VIP មុនទើបអាចទទួលបានសិទ្ធិ!", show_alert=True)
            conn.close()
            return
            
        delta = timedelta(days=14)
        plan_name = "សាកល្បងឥតគិតថ្លៃ (Free 2 Weeks)"
        
        add_subscription_custom(user_id, username, user_full_name, delta=delta, plan_name=plan_name)
        expiry_date = (datetime.now() + delta).strftime("%d/%m/%Y %H:%M")
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🎬 ចូលទៅកាន់ Channel VIP", url=f"https://t.me/{CHANNEL_ID.replace('-100', '')}")
        builder.adjust(1)
        
        await callback.message.edit_text(
            f"🎉 <b>អបអរសាទរ! អ្នកទទួលបានសិទ្ធិសាកល្បង VIP ដោយឥតគិតថ្លៃ ២សប្តាហ៍ជោគជ័យ!</b>\n\n"
            f"👤 ឈ្មោះ: <b>{user_full_name}</b>\n"
            f"📦 ប្រភេទ: <b>{plan_name}</b>\n"
            f"⏳ ថ្ងៃផុតកំណត់: <code>{expiry_date}</code>\n\n"
            f"គណនីរបស់អ្នកត្រូវបានកត់ត្រាទុកក្នុងប្រព័ន្ធហើយ។ សូមរីករាយទស្សនាកម្សាន្ត!",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logging.error(f"Error in claim_free_trial: {e}")
        await callback.answer("⚠️ មានបញ្ហាក្នុងការផ្ទៀងផ្ទាត់ សូមព្យាយាមម្តងទៀត។", show_alert=True)
    finally:
        conn.close()

# --- ADMIN COMMAND: បន្ថែមសមាជិកចាស់ដោយដៃ (/addsub user_id days plan_name) ---
@dp.message(Command("addsub"))
async def cmd_add_subscription(message: types.Message):
    args = message.text.split()
    if len(args) < 3:
        await message.reply(
            "⚠️ <b>ទ្រង់ទ្រាយពាក្យបញ្ជាមិនត្រឹមត្រូវ!</b>\n"
            "សូមប្រើប្រាស់: <code>/addsub [user_id] [ចំនួនថ្ងៃ] [ឈ្មោះកញ្ចប់]</code>\n"
            "ឧទាហរណ៍: <code>/addsub 123456789 30 កញ្ចប់១ខែ</code>"
        )
        return

    try:
        target_user_id = int(args[1])
        days = int(args[2])
        plan_name = " ".join(args[3:]) if len(args) > 3 else f"{days} ថ្ងៃ"

        delta = timedelta(days=days)
        
        try:
            chat_member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=target_user_id)
            full_name = chat_member.user.full_name or "សមាជិកចាស់"
            username = chat_member.user.username or ""
        except Exception:
            full_name = "សមាជិកចាស់"
            username = ""

        add_subscription_custom(target_user_id, username, full_name, delta=delta, plan_name=plan_name)
        
        expiry_date = (datetime.now() + delta).strftime("%d/%m/%Y %H:%M")
        
        await message.reply(
            f"✅ <b>បានបន្ថែមសមាជិកជោគជ័យ!</b>\n\n"
            f"🆔 User ID: <code>{target_user_id}</code>\n"
            f"📦 កញ្ចប់: <b>{plan_name}</b>\n"
            f"⏳ ផុតកំណត់ថ្ងៃ: <code>{expiry_date}</code>"
        )
    except Exception as e:
        await message.reply(f"❌ មានកំហុសឆ្គង: {e}")

@dp.callback_query(F.data == "about_us")
async def callback_about(callback: types.CallbackQuery):
    about_text = (
        "❤️ <b>អំពីពួកយើង (About Us)</b> 🤖\n\n"
        "គ្រប់រឿងទាំងអស់មិនមានដល់ភាគបញ្ចប់ទេ ព្រោះរឿងក្រុមហ៊ុនចិនកំពុងចេញបន្ត ឬចប់រដូវកាលនីមួយៗ ហើយមួយអាទិត្យចេញតែ ១ភាគ ឬ ២ភាគប៉ុណ្ណោះ។ ប្រសិនបើរឿងពុំទាន់ចេញ ខាងពួកយើងក៏ពុំអាចបកបានដូចគ្នា។ ចំពោះថ្ងៃខ្លះរឿងចេញជាន់គ្នា ពួកយើងនឹងធ្វើរឿងដែលសំខាន់មុនគេ ✅\n\n"
        "គ្រប់រឿងទាំងអស់ខាងពួកយើងអាចមានពេលចេញតែពេលល្ងាចប៉ុណ្ណោះ ព្រោះពួកយើងទាំងអស់សុទ្ធតែមានការងាររៀងៗខ្លួន។ ករណីខ្លះពួកយើង អាចនឹងឈ្លៀតកាត់វីដេអូហើយចេញពេលព្រឹក ឬថ្ងៃ ប្រសិនបើពួកយើងមានពេលទំនេរ 🥰\n\n"
        "គ្រប់ប្រាក់ចំណូលដែលបងប្អូនបង់ចូលគ្រុប VIP ទាំងអស់ ពួកយើងយកទៅទិញរឿង និងទិញ API សម្រាប់បញ្ចូលសំឡេង និងបកប្រែ ហើយពួកយើងនឹងបន្ថែមប្រាក់ចំណូលផ្ទាល់ខ្លួនបន្ថែម ដើម្បីឱ្យបងប្អូនមានរឿងមើលជារៀងរាល់ថ្ងៃ 💌\n\n"
        "ប្រសិនបើក្រុមពួកយើងអាចរីកចម្រើន ឬអាចលែងចំណាយចំណូលផ្ទាល់ខ្លួនទៀត ពួកយើងនឹងធ្វើរឿងទាំងអស់ដែលបងប្អូនស្នើសុំ មិនថាភាគចាស់ៗ ឬថ្មីទេ ហើយពួកយើងនឹងបង្កើតល្បឿនចេញរឿង អាចមួយថ្ងៃមានលើស 15 ភាគ សម្រាប់បងប្អូនទស្សនាកម្សាន្ត 😍"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="💎 ជ្រើសរើសកញ្ចប់ VIP", callback_data="select_plan")
    builder.button(text="⬅️ ត្រឡប់ក្រោយ", callback_data="back_start")
    builder.adjust(1)
    
    try:
        if os.path.exists(ABOUT_BANNER_PATH):
            photo = FSInputFile(ABOUT_BANNER_PATH)
            await callback.message.answer_photo(photo=photo, caption=about_text, reply_markup=builder.as_markup())
        else:
            await callback.message.answer(about_text, reply_markup=builder.as_markup())
        await callback.message.delete()
    except Exception as e:
        logging.error(f"Error in callback_about: {e}")
        await callback.message.answer(about_text, reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "select_plan")
async def callback_select_plan(callback: types.CallbackQuery):
    text = (
        "💎 <b>សូមជ្រើសរើសកញ្ចប់សមាជិក VIP ដែលអ្នកត្រូវការ៖</b>\n\n"
        "• 🥇 <b>កញ្ចប់ ១ ខែ</b> = <b>$2</b> (៣០ថ្ងៃ)\n"
        "• 🥈 <b>កញ្ចប់ ២ ខែ</b> = <b>$3</b> (៦០ថ្ងៃ - សន្សំសំចៃ!)\n"
        "• 🥉 <b>កញ្ចប់ ៣ ខែ</b> = <b>$5</b> (៩០ថ្ងៃ - តម្លៃពិសេស!)\n\n"
        "👇 សូមចុចជ្រើសរើសកញ្ចប់ខាងក្រោម៖"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🥇 កញ្ចប់ ១ ខែ ($2)", callback_data="plan_1m")
    builder.button(text="🥈 កញ្ចប់ ២ ខែ ($3)", callback_data="plan_2m")
    builder.button(text="🥉 កញ្ចប់ ៣ ខែ ($5)", callback_data="plan_3m")
    builder.button(text="⬅️ ត្រឡប់ក្រោយ", callback_data="back_start")
    builder.adjust(1)
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup())
        try:
            await callback.message.delete()
        except:
            pass
    await callback.answer()

async def show_qr_for_plan(callback: types.CallbackQuery, plan_name: str, price: str, qr_filename: str = QR_PATH):
    caption_text = (
        f"💳 <b>អ្នកបានជ្រើសរើស: {plan_name} (តម្លៃ: {price})</b>\n\n"
        "1. សូមស្កេន QR Code ខាងលើដើម្បីទូទាត់ប្រាក់\n"
        "2. បន្ទាប់ពីបង់រួច <b>សូម Upload រូបភាពបង្កាន់ដៃ (Receipt Screenshot)</b> ចូលមកកាន់ Bot នេះផ្ទាល់ ដើម្បីឱ្យ Admin ពិនិត្យ។"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ ជ្រើសរើសកញ្ចប់ផ្សេង", callback_data="select_plan")
    builder.adjust(1)

    try:
        target_qr = qr_filename if os.path.exists(qr_filename) else QR_PATH
        if os.path.exists(target_qr):
            photo = FSInputFile(target_qr)
            await callback.message.answer_photo(photo=photo, caption=caption_text, reply_markup=builder.as_markup())
        else:
            await callback.message.answer(caption_text + "\n\n<i>(មិនទាន់មានរូបភាព QR Code ក្នុងប្រព័ន្ធ)</i>", reply_markup=builder.as_markup())
        await callback.message.delete()
    except Exception as e:
        logging.error(f"Error in show_qr_for_plan: {e}")
        await callback.message.answer(caption_text, reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "plan_1m")
async def plan_1(callback: types.CallbackQuery):
    await show_qr_for_plan(callback, "កញ្ចប់ ១ ខែ", "$2", "qr_1m.jpg")

@dp.callback_query(F.data == "plan_2m")
async def plan_2(callback: types.CallbackQuery):
    await show_qr_for_plan(callback, "កញ្ចប់ ២ ខែ", "$3", "qr_2m.jpg")

@dp.callback_query(F.data == "plan_3m")
async def plan_3(callback: types.CallbackQuery):
    await show_qr_for_plan(callback, "កញ្ចប់ ៣ ខែ", "$5", "qr_3m.jpg")

@dp.callback_query(F.data == "back_start")
async def callback_back(callback: types.CallbackQuery):
    user_name = callback.from_user.full_name or "អតិថិជន"
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 ទទួលសាកល្បងឥតគិតថ្លៃ ២សប្តាហ៍", callback_data="claim_free_trial")
    builder.button(text="ℹ️ អំពីពួកយើង", callback_data="about_us")
    builder.button(text="💎 ជ្រើសរើសកញ្ចប់ VIP", callback_data="select_plan")
    builder.button(text="📞 ទំនាក់ទំនងផ្ទាល់", url=ADMIN_CONTACT)
    builder.adjust(1)
    
    text = (
        f"👋 សូមស្វាគមន៍ <b>{user_name}</b> មកកាន់ប្រព័ន្ធ VIP របស់យើង!\n\n"
        f"🌟 <b>Ai Legend VIP</b>\n"
        f"────────────────────────\n"
        f"🎁 <b>ពិសេស!</b> សម្រាប់សមាជិកចាស់និងថ្មី អាចចុចទទួលសិទ្ធិសាកល្បងមើលរឿងដោយឥតគិតថ្លៃរយៈពេល <b>២សប្តាហ៍ (១៤ថ្ងៃ)</b> ភ្លាមៗនៅខាងក្រោម៖"
    )
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup())
        try:
            await callback.message.delete()
        except:
            pass
    await callback.answer()

@dp.message(F.photo)
async def handle_receipt(message: types.Message):
    user_id = message.from_user.id
    user_full_name = message.from_user.full_name or "អតិថិជន"
    username = message.from_user.username
    username_display = f"@{username}" if username else "គ្មាន Username"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⏱️ អនុម័ត ១ ម៉ោង", callback_data=f"approve_h_{user_id}_1")
    builder.button(text="⏱️ អនុម័ត ៣ ម៉ោង", callback_data=f"approve_h_{user_id}_3")
    builder.button(text="⏱️ អនុម័ត ៦ ម៉ោង", callback_data=f"approve_h_{user_id}_6")
    builder.button(text="⏱️ អនុម័ត ១២ ម៉ោង", callback_data=f"approve_h_{user_id}_12")
    builder.button(text="⏱️ អនុម័ត ២៤ ម៉ោង", callback_data=f"approve_h_{user_id}_24")
    builder.button(text="✅ អនុម័ត ១ខែ ($2)", callback_data=f"approve_d_{user_id}_30")
    builder.button(text="✅ អនុម័ត ២ខែ ($3)", callback_data=f"approve_d_{user_id}_60")
    builder.button(text="✅ អនុម័ត ៣ខែ ($5)", callback_data=f"approve_d_{user_id}_90")
    builder.button(text="❌ បដិសេធ (Reject)", callback_data=f"reject_{user_id}")
    if username:
        builder.button(text="💬 ឆាតរកអតិថិជន", url=f"https://t.me/{username}")
    builder.adjust(1)
    
    try:
        await bot.send_photo(
            chat_id=ADMIN_GROUP_ID,
            photo=message.photo[-1].file_id,
            caption=f"📨 <b>មានការស្នើសុំចូល Channel VIP ថ្មី!</b>\n"
                    f"────────────────────────\n"
                    f"👤 ឈ្មោះ: <a href=\"tg://user?id={user_id}\">{user_full_name}</a>\n"
                    f"🔗 Username: {username_display}\n"
                    f"🆔 User ID: <code>{user_id}</code>\n"
                    f"────────────────────────\n"
                    f"សូមពិនិត្យបង្កាន់ដៃ និងជ្រើសរើសកញ្ចប់/ម៉ោងដើម្បីអនុម័ត៖",
            reply_markup=builder.as_markup()
        )
        
        user_builder = InlineKeyboardBuilder()
        user_builder.button(text="📞 ទំនាក់ទំនង Admin", url=ADMIN_CONTACT)
        user_builder.button(text="🏠 ត្រឡប់ទៅទំព័រដើម", callback_data="back_start")
        user_builder.adjust(1)
        
        await message.answer(
            "⏳ <b>បានទទួលបង្កាន់ដៃរបស់អ្នកហើយ!</b>\n\n"
            "ប្រព័ន្ធបានបញ្ជូនរូបភាពរបស់អ្នកទៅកាន់ Admin រួចរាល់។ សូមរង់ចាំបន្តិច Admin នឹងពិនិត្យនិងផ្ញើ Link ចូល Channel VIP ជូនអ្នកផ្ទាល់។",
            reply_markup=user_builder.as_markup()
        )
    except Exception as e:
        logging.error(f"Error sending receipt: {e}")
        await message.answer("❌ មានបញ្ហាក្នុងការបញ្ជូនបង្កាន់ដៃទៅកាន់ Admin!")

@dp.callback_query(F.data.startswith("approve_"))
async def admin_approve(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    approval_type = parts[1]
    user_id = int(parts[2])
    val = int(parts[3])
    
    if approval_type == 'h':
        delta = timedelta(hours=val)
        plan_text = f"{val} ម៉ោង"
    else:
        delta = timedelta(days=val)
        plan_text = "១ ខែ ($2)" if val == 30 else ("២ ខែ ($3)" if val == 60 else ("៣ ខែ ($5)" if val == 90 else f"{val} ថ្ងៃ"))
    
    try:
        chat_member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        full_name = chat_member.user.full_name or "អតិថិជន"
        username = chat_member.user.username or ""
        
        add_subscription_custom(user_id, username, full_name, delta=delta, plan_name=plan_text)
        
        invite_link = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1
        )
        
        now = datetime.now()
        start_date = now.strftime("%d/%m/%Y %H:%M")
        expiry = now + delta
        expiry_date = expiry.strftime("%d/%m/%Y %H:%M")
        
        await bot.send_message(
            user_id,
            f"🎉 អបអរសាទរ! Admin បានផ្ទៀងផ្ទាត់ការបង់ប្រាក់របស់អ្នកជោគជ័យហើយ។\n\n"
            f"📦 កញ្ចប់/រយៈពេល: <b>{plan_text}</b>\n"
            f"📅 ថ្ងៃចាប់ផ្តើម: <code>{start_date}</code>\n"
            f"⏳ ថ្ងៃផុតកំណត់: <code>{expiry_date}</code>\n\n"
            f"នេះគឺជាតំណភ្ជាប់សម្រាប់ចូល Channel VIP របស់អ្នក:\n"
            f"👉 {invite_link.invite_link}"
        )
        
        new_caption = (callback.message.caption or "") + f"\n\n<b>Status: ✅ APPROVED ({plan_text})</b>"
        await callback.message.edit_caption(caption=new_caption, reply_markup=None)
        await callback.answer(f"បានអនុម័តរយៈពេល {plan_text} ជោគជ័យ!")
        
    except Exception as e:
        logging.error(f"Error in admin_approve: {e}")
        await callback.answer(f"មានកំហុសឆ្គង: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("reject_"))
async def admin_reject(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    try:
        await bot.send_message(
            user_id,
            "❌ សូមអភ័យទោស! បង្កាន់ដៃបង់ប្រាក់របស់អ្នកមិនត្រឹមត្រូវទេ។ សូមត្រួតពិនិត្យឡើងវិញ ឬទាក់ទង Admin។"
        )
        new_caption = (callback.message.caption or "") + "\n\n<b>Status: ❌ REJECTED (បានបដិសេធ)</b>"
        await callback.message.edit_caption(caption=new_caption, reply_markup=None)
        await callback.answer("បានបដិសេធសំណើនេះ។")
    except Exception as e:
        logging.error(f"Error in admin_reject: {e}")
        await callback.answer(f"មានកំហុសឆ្គង: {e}", show_alert=True)

# --- BACKGROUND CRON JOB: ពិនិត្យសមាជិកផុតកំណត់រៀងរាល់ ១៥នាទីម្តង ---
async def check_subscriptions_expiry():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("SELECT user_id, full_name FROM subscriptions WHERE expiry_date <= ?", (now_str,))
    expired_users = cursor.fetchall()
    
    for user_id, full_name in expired_users:
        try:
            await bot.ban_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            await bot.unban_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            
            await bot.send_message(
                user_id,
                "⏰ <b>សមាជិកភាព VIP របស់អ្នកបានផុតកំណត់ហើយ!</b>\n\n"
                "អ្នកត្រូវបានដកចេញពី Channel VIP ស្វ័យប្រវត្តិ។ ដើម្បីបន្តចូលទស្សនា សូមធ្វើការបង់ប្រាក់ទិញកញ្ចប់ថ្មីតាមរយៈ Bot នេះ។"
            )
            
            cursor.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
            conn.commit()
            logging.info(f"Successfully kicked expired user: {user_id} ({full_name})")
        except Exception as e:
            logging.error(f"Failed to kick user {user_id}: {e}")
            
    conn.close()

# --- WEB SERVER (AIOHTTP) សម្រាប់បំពេញលក្ខខណ្ឌ Port Binding របស់ Render ---
async def handle(request):
    return web.Response(text="Bot is running successfully!")

app = web.Application()
app.add_routes([web.get('/', handle)])

async def start_web_server():
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    init_db()
    
    # ចាប់ផ្តើម Web Server មុនគេដើម្បីបើក Port ឆ្លើយតបជាមួយ Render
    await start_web_server()
    
    # លុប Webhook ចាស់ចោលដើម្បីការពារបញ្ហា Conflict ពេល Polling
    await bot.delete_webhook(drop_pending_updates=True)
    
    scheduler.add_job(check_subscriptions_expiry, "interval", minutes=15)
    scheduler.start()
    
    logging.info("Bot with Free Trial (2 Weeks) is starting...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
