from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_clients, delete_client

# Ortga tugmasi yaratish uchun yordamchi funksiya
def back_button():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Ortga", callback_data="back_to_main"))
    return keyboard

async def add_client_cmd(message: types.Message):
    await message.answer(
        "Ism, telefon va manzilni vergul bilan ajratib yozing.\n"
        "Misol: `Adham, 998901234567, Samarqand sh.`",
        reply_markup=back_button()
    )

async def list_clients_handler(message: types.Message):
    clients = get_clients()
    if clients:
        text = "📋 Klientlar ro'yxati:\n\n"
        for idx, c in enumerate(clients, start=1):
            text += f"{idx}. {c[1]}\n   📞 {c[2]}\n   📍 {c[3]}\n\n"
        await message.answer(text, reply_markup=back_button())
    else:
        await message.answer("⚠️ Hozircha klient yo‘q.", reply_markup=back_button())

async def show_clients_for_delete(message: types.Message):
    clients = get_clients()
    if not clients:
        await message.answer("⚠️ Hozircha klient yo‘q.")
        return

    keyboard = InlineKeyboardMarkup(row_width=1)
    for idx, c in enumerate(clients, start=1):
        button_text = f"{idx}. {c[1]} ({c[2]})"
        if len(button_text) > 50:
            button_text = button_text[:47] + "..."
        keyboard.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"del_client:{c[0]}"
        ))
    # Ortga tugmasi
    keyboard.add(InlineKeyboardButton("🔙 Ortga", callback_data="back_to_main"))
    await message.answer("O'chirmoqchi bo'lgan klientni tanlang:", reply_markup=keyboard)

async def delete_client_callback(callback: types.CallbackQuery):
    client_id = int(callback.data.split(":")[1])
    success, error = delete_client(client_id)
    if success:
        await callback.answer("✅ Klient o'chirildi")
        await callback.message.edit_text("Klient o'chirildi.", reply_markup=back_button())
    else:
        await callback.answer("❌ Xatolik: " + (error or "Noma'lum xato"), show_alert=True)