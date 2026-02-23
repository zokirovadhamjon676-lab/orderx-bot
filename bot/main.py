from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import BOT_TOKEN
from bot.handlers.clients import (
    add_client_cmd, list_clients_handler,
    show_clients_for_delete, delete_client_callback
)
from bot.handlers.orders import (
    add_order_cmd, show_orders_for_delete, delete_order_callback
)
from bot.handlers.stats import export_orders_excel
from database.db import (
    add_client, add_order, get_clients,
    get_setting, set_setting, hash_password, check_password as db_check_password
)
import random
import logging

# Logging sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Vaqtinchalik ma'lumotlar
reset_sessions = {}              # Parolni tiklash jarayoni
change_phone_sessions = {}        # Telefon raqamni o'zgartirish jarayoni
change_password_sessions = {}     # Parolni o'zgartirish jarayoni
authenticated_users = set()       # Autentifikatsiyadan o'tgan foydalanuvchilar

# SMS yuborish (mock - hozircha konsolga chiqariladi)
def send_sms_code(phone, code):
    logger.info(f"📱 SMS kod {phone} raqamiga yuborildi: {code}")
    return True

# -------------------- Asosiy menyu tugmalari --------------------
def main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("➕ Klient qo'shish"),
        KeyboardButton("📋 Klientlar ro'yxati"),
        KeyboardButton("🛍 Buyurtma qo'shish"),
        KeyboardButton("📊 Excel export"),
        KeyboardButton("🗑 O'chirish"),
        KeyboardButton("⚙️ Sozlamalar")
    ]
    keyboard.add(*buttons)
    return keyboard

# Autentifikatsiya dekoratori
def authenticated_only(func):
    async def wrapper(message: types.Message):
        if message.from_user.id not in authenticated_users:
            await message.answer("⚠️ Avval tizimga kiring. /start ni bosing.")
            return
        return await func(message)
    return wrapper

# -------------------- START komandasi --------------------
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"User {user_id} started bot")

    # Agar foydalanuvchi reset sessionda bo'lsa
    if user_id in reset_sessions:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("✅ Davom ettirish", callback_data="continue_reset"))
        keyboard.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_reset"))
        await message.answer(
            "Sizda tugallanmagan parolni tiklash jarayoni bor. Davom ettirasizmi?",
            reply_markup=keyboard
        )
        return

    if user_id in authenticated_users:
        await message.answer("👋 Xush kelibsiz! CRM bot.", reply_markup=main_menu())
        return

    password_hash = get_setting("password_hash")
    admin_phone = get_setting("admin_phone")

    if not password_hash or not admin_phone:
        # Birinchi marta sozlash
        reset_sessions[user_id] = {'step': 'setup_phone'}
        await message.answer(
            "🤖 Bot birinchi marta ishga tushirilmoqda. Iltimos, sozlamalarni kiriting.\n"
            "Telefon raqamingizni xalqaro formatda yozing (masalan: +998901234567):"
        )
        return

    # Oddiy login ekrani
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔐 Kirish", callback_data="login"))
    keyboard.add(InlineKeyboardButton("❓ Parolni unutdingizmi?", callback_data="forgot_password"))
    await message.answer("🔒 Botdan foydalanish uchun tizimga kiring.", reply_markup=keyboard)

# -------------------- INLINE HANDLERLAR --------------------
@dp.callback_query_handler(lambda c: c.data == "login")
async def process_login(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("🔐 Parolni kiriting:")

@dp.callback_query_handler(lambda c: c.data == "forgot_password")
async def process_forgot_password(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    admin_phone = get_setting("admin_phone")
    if admin_phone:
        # Oxirgi 4 ta raqamni ko'rsatish
        masked = "*" * (len(admin_phone) - 4) + admin_phone[-4:]
        await callback.message.answer(
            f"📞 Sizning telefoningiz: {masked}\n"
            "Agar bu raqam sizniki bo‘lsa, to‘liq raqamni kiriting:"
        )
    else:
        await callback.message.answer("📞 Telefon raqamingizni xalqaro formatda yozing:")
    reset_sessions[user_id] = {'step': 'waiting_phone'}
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "continue_reset")
async def continue_reset(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    session = reset_sessions.get(user_id, {})
    step = session.get('step')
    if step == 'waiting_phone':
        await callback.message.answer("📞 Telefon raqamingizni kiriting:")
    elif step == 'waiting_code':
        await callback.message.answer("🔢 Kodni kiriting:")
    elif step == 'waiting_new_password':
        await callback.message.answer("🔐 Yangi parolni kiriting (kamida 4 belgi):")
    else:
        # Agar noma'lum step bo'lsa, resetni bekor qilish
        del reset_sessions[user_id]
        await callback.message.answer("Bekor qilindi. /start ni bosing.")

@dp.callback_query_handler(lambda c: c.data == "cancel_reset")
async def cancel_reset(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in reset_sessions:
        del reset_sessions[user_id]
    await callback.answer("Bekor qilindi.")
    await callback.message.answer("Bosh sahifa. /start ni bosing.")

# -------------------- Parolni tekshirish (HANDLER) --------------------
@dp.message_handler(lambda message: message.text and message.from_user.id not in authenticated_users and message.from_user.id not in reset_sessions and message.from_user.id not in change_phone_sessions and message.from_user.id not in change_password_sessions)
async def handle_password_input(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"Parol tekshirilmoqda: user {user_id}, parol: {message.text}")
    password_hash = get_setting("password_hash")
    if password_hash and db_check_password(message.text, password_hash):
        authenticated_users.add(user_id)
        logger.info(f"User {user_id} autentifikatsiyadan o‘tdi")
        await message.answer("✅ Parol to‘g‘ri. Xush kelibsiz!", reply_markup=main_menu())
    else:
        logger.info(f"User {user_id} noto‘g‘ri parol kiritdi")
        await message.answer("❌ Parol noto‘g‘ri. Qayta urinib ko‘ring yoki 'Parolni unutdingizmi?' tugmasini bosing.")

# -------------------- Reset jarayoni (parolni tiklash) --------------------
@dp.message_handler(lambda message: message.from_user.id in reset_sessions)
async def handle_reset(message: types.Message):
    user_id = message.from_user.id
    session = reset_sessions[user_id]
    step = session.get('step')

    if step == 'setup_phone':
        phone = message.text.strip()
        if not phone.startswith('+') or not phone[1:].isdigit():
            await message.answer("❌ Telefon raqam noto‘g‘ri formatda. Iltimos, +998901234567 shaklida yozing.")
            return
        session['phone'] = phone
        session['step'] = 'setup_password'
        await message.answer("Endi bot uchun parol o'rnating (kamida 4 belgi):")

    elif step == 'setup_password':
        password = message.text.strip()
        if len(password) < 4:
            await message.answer("❌ Parol juda qisqa. Kamida 4 belgidan iborat bo‘lsin.")
            return
        hashed = hash_password(password)
        set_setting("password_hash", hashed)
        set_setting("admin_phone", session['phone'])
        authenticated_users.add(user_id)
        del reset_sessions[user_id]
        await message.answer("✅ Bot sozlandi! Endi to‘liq foydalanishingiz mumkin.", reply_markup=main_menu())

    elif step == 'waiting_phone':
        phone = message.text.strip()
        admin_phone = get_setting("admin_phone")
        if phone != admin_phone:
            await message.answer("❌ Bu telefon raqam tizimda mavjud emas. Qayta urinib ko‘ring.")
            return
        code = str(random.randint(100000, 999999))
        session['code'] = code
        session['step'] = 'waiting_code'
        session['phone'] = phone
        send_sms_code(phone, code)
        await message.answer("✅ Sizning telefon raqamingizga 6 xonali kod yuborildi. Kodni kiriting:")

    elif step == 'waiting_code':
        user_code = message.text.strip()
        if user_code != session.get('code'):
            await message.answer("❌ Kod noto‘g‘ri. Qayta urinib ko‘ring.")
            return
        session['step'] = 'waiting_new_password'
        await message.answer("✅ Kod tasdiqlandi. Endi yangi parolni kiriting:")

    elif step == 'waiting_new_password':
        new_pass = message.text.strip()
        if len(new_pass) < 4:
            await message.answer("❌ Parol juda qisqa. Kamida 4 belgidan iborat bo‘lsin.")
            return
        hashed = hash_password(new_pass)
        set_setting("password_hash", hashed)
        authenticated_users.add(user_id)
        del reset_sessions[user_id]
        await message.answer("✅ Parol muvaffaqiyatli o‘zgartirildi. Endi tizimga kirdingiz.", reply_markup=main_menu())

# -------------------- Sozlamalar menyusi --------------------
@dp.message_handler(lambda msg: msg.text == "⚙️ Sozlamalar")
@authenticated_only
async def handle_settings_button(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📱 Telefon raqamni o'zgartirish", callback_data="change_phone"),
        InlineKeyboardButton("🔐 Parolni o'zgartirish", callback_data="change_password"),
        InlineKeyboardButton("🔙 Ortga", callback_data="back_to_main")
    )
    await message.answer("⚙️ Sozlamalar:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "change_phone")
async def change_phone_start(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    change_phone_sessions[user_id] = {'step': 'waiting_new_phone'}
    await callback.answer()
    await callback.message.answer(
        "📱 Yangi telefon raqamingizni xalqaro formatda yozing (masalan: +998901234567):"
    )

@dp.callback_query_handler(lambda c: c.data == "change_password")
async def change_password_start(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    # Yangi parolni o'zgartirish sessiyasini boshlash
    change_password_sessions[user_id] = {'step': 'waiting_old_password'}
    await callback.answer()
    await callback.message.answer("🔐 Eski parolni kiriting:")

# -------------------- Parolni o'zgartirish jarayoni --------------------
@dp.message_handler(lambda message: message.from_user.id in change_password_sessions)
@authenticated_only
async def handle_change_password(message: types.Message):
    user_id = message.from_user.id
    session = change_password_sessions[user_id]
    step = session.get('step')
    password_hash = get_setting("password_hash")

    if step == 'waiting_old_password':
        old_pass = message.text.strip()
        if db_check_password(old_pass, password_hash):
            session['step'] = 'waiting_new_password'
            await message.answer("✅ Eski parol to‘g‘ri. Endi yangi parolni kiriting (kamida 4 belgi):")
        else:
            await message.answer("❌ Eski parol noto‘g‘ri. Qayta urinib ko‘ring yoki 'Bekor qilish' uchun /start ni bosing.")

    elif step == 'waiting_new_password':
        new_pass = message.text.strip()
        if len(new_pass) < 4:
            await message.answer("❌ Parol juda qisqa. Kamida 4 belgidan iborat bo‘lsin.")
            return
        # Yangi parolni saqlash
        new_hashed = hash_password(new_pass)
        set_setting("password_hash", new_hashed)
        del change_password_sessions[user_id]
        await message.answer("✅ Parol muvaffaqiyatli o‘zgartirildi!", reply_markup=main_menu())

# -------------------- Telefon raqamni o'zgartirish jarayoni --------------------
@dp.message_handler(lambda message: message.from_user.id in change_phone_sessions)
@authenticated_only
async def handle_change_phone(message: types.Message):
    user_id = message.from_user.id
    session = change_phone_sessions[user_id]
    step = session.get('step')

    if step == 'waiting_new_phone':
        new_phone = message.text.strip()
        if not new_phone.startswith('+') or not new_phone[1:].isdigit():
            await message.answer("❌ Telefon raqam noto‘g‘ri formatda. Iltimos, +998901234567 shaklida yozing.")
            return
        code = str(random.randint(100000, 999999))
        session['new_phone'] = new_phone
        session['code'] = code
        session['step'] = 'waiting_code'
        send_sms_code(new_phone, code)
        await message.answer("✅ Yangi raqamingizga 6 xonali kod yuborildi. Kodni kiriting:")

    elif step == 'waiting_code':
        user_code = message.text.strip()
        if user_code != session.get('code'):
            await message.answer("❌ Kod noto‘g‘ri. Qayta urinib ko‘ring.")
            return
        set_setting("admin_phone", session['new_phone'])
        del change_phone_sessions[user_id]
        await message.answer("✅ Telefon raqam muvaffaqiyatli o‘zgartirildi.", reply_markup=main_menu())

# -------------------- Ortga qaytish --------------------
@dp.callback_query_handler(lambda c: c.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu())
    await callback.message.delete()

# -------------------- CALLBACK HANDLERLAR (o'chirish) --------------------
@dp.callback_query_handler(lambda c: c.data == "delete_choose_client")
async def process_delete_client_choice(callback: types.CallbackQuery):
    if callback.from_user.id not in authenticated_users:
        await callback.answer("Avval tizimga kiring.", show_alert=True)
        return
    await callback.answer()
    await show_clients_for_delete(callback.message)

@dp.callback_query_handler(lambda c: c.data == "delete_choose_order")
async def process_delete_order_choice(callback: types.CallbackQuery):
    if callback.from_user.id not in authenticated_users:
        await callback.answer("Avval tizimga kiring.", show_alert=True)
        return
    await callback.answer()
    await show_orders_for_delete(callback.message)

@dp.callback_query_handler(lambda c: c.data.startswith("del_client:"))
async def process_delete_client(callback: types.CallbackQuery):
    if callback.from_user.id not in authenticated_users:
        await callback.answer("Avval tizimga kiring.", show_alert=True)
        return
    await delete_client_callback(callback)

@dp.callback_query_handler(lambda c: c.data.startswith("del_order:"))
async def process_delete_order(callback: types.CallbackQuery):
    if callback.from_user.id not in authenticated_users:
        await callback.answer("Avval tizimga kiring.", show_alert=True)
        return
    await delete_order_callback(callback)

# -------------------- REPLY TUGMALAR --------------------
@dp.message_handler(lambda msg: msg.text == "➕ Klient qo'shish")
@authenticated_only
async def handle_add_client_button(message: types.Message):
    await add_client_cmd(message)

@dp.message_handler(lambda msg: msg.text == "📋 Klientlar ro'yxati")
@authenticated_only
async def handle_list_clients_button(message: types.Message):
    await list_clients_handler(message)

@dp.message_handler(lambda msg: msg.text == "🛍 Buyurtma qo'shish")
@authenticated_only
async def handle_add_order_button(message: types.Message):
    await add_order_cmd(message)

@dp.message_handler(lambda msg: msg.text == "📊 Excel export")
@authenticated_only
async def handle_export_button(message: types.Message):
    await export_orders_excel(message)

@dp.message_handler(lambda msg: msg.text == "🗑 O'chirish")
@authenticated_only
async def handle_delete_button(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("👤 Klient o'chirish", callback_data="delete_choose_client"),
        InlineKeyboardButton("📦 Buyurtma o'chirish", callback_data="delete_choose_order")
    )
    await message.answer("Nimani o'chirmoqchisiz?", reply_markup=keyboard)

# -------------------- UNIVERSAL HANDLER (vergul bilan yozilgan matnlar) --------------------
@dp.message_handler(lambda message: "," in message.text)
@authenticated_only
async def universal_input(message: types.Message):
    parts = [p.strip() for p in message.text.split(",")]

    if len(parts) == 2:
        # Bu faqat klient qo‘shish bo‘lishi mumkin (buyurtma 3 qism talab qiladi)
        name, phone = parts
        address = ""  # manzil ixtiyoriy, bo‘sh qoldiriladi
        add_client(name, phone, address)
        await message.answer(f"✅ Klient qo‘shildi: {name}", reply_markup=main_menu())

    elif len(parts) == 3:
        first = parts[0]
        if first.isdigit():
            # Buyurtma qo‘shish
            client_index_str, product, amount_str = parts
            try:
                client_index = int(client_index_str)
                amount = int(amount_str)
                clients = get_clients()
                if 1 <= client_index <= len(clients):
                    client_id = clients[client_index-1][0]
                    add_order(client_id, product, amount)
                    await message.answer(f"✅ Buyurtma qo‘shildi: {product}", reply_markup=main_menu())
                else:
                    await message.answer("❌ Bunday raqamli klient mavjud emas.", reply_markup=main_menu())
            except ValueError:
                await message.answer("❌ Xato: Klient raqami va miqdor son bo‘lishi kerak.", reply_markup=main_menu())
            except Exception as e:
                await message.answer(f"❌ Xato: {str(e)}", reply_markup=main_menu())
        else:
            # Klient qo‘shish (ism, telefon, manzil)
            name, phone, address = parts
            add_client(name, phone, address)
            await message.answer(f"✅ Klient qo‘shildi: {name}", reply_markup=main_menu())
    else:
        await message.answer(
            "❌ Noto‘g‘ri format. Iltimos:\n"
            "• Klient uchun: Ism, Telefon (yoki Ism, Telefon, Manzil)\n"
            "• Buyurtma uchun: Klient raqami, Mahsulot, Miqdor\n"
            "Misol: `Adham, 998901234567` yoki `1, T-shirt, 5`",
            reply_markup=main_menu()
        )

# -------------------- MATNLI KOMANDALAR --------------------
@dp.message_handler(commands=['add_client'])
@authenticated_only
async def add_client_command(message: types.Message):
    await add_client_cmd(message)

@dp.message_handler(commands=['clients'])
@authenticated_only
async def clients_command(message: types.Message):
    await list_clients_handler(message)

@dp.message_handler(commands=['add_order'])
@authenticated_only
async def add_order_command(message: types.Message):
    await add_order_cmd(message)

@dp.message_handler(commands=['export'])
@authenticated_only
async def export_command(message: types.Message):
    await export_orders_excel(message)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)