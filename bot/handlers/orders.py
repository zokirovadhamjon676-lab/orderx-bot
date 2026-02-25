from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_clients, get_orders, delete_order

async def add_order_cmd(message: types.Message):
    clients = get_clients()
    if not clients:
        await message.answer("⚠️ Avval klient qo‘shing: /add_client")
        return

    text = "Mavjud klientlar:\n"
    for idx, c in enumerate(clients, start=1):
        text += f"{idx}. {c[1]} (📞 {c[2]})\n"
    text += (
        "\nBuyurtma qo‘shish uchun: `klient_raqami, mahsulot, miqdor`\n"
        "Masalan: `1, Anor, 5kg`\n"
        "(Klient raqami yuqoridagi ro'yxatdagi raqam)"
    )
    await message.answer(text)

async def show_orders_for_delete(message: types.Message):
    orders = get_orders()
    if not orders:
        await message.answer("📭 Buyurtma mavjud emas.")
        return

    keyboard = InlineKeyboardMarkup(row_width=1)
    for idx, o in enumerate(orders, start=1):
        # o: order_id, client_name, phone, address, product, amount, date
        text = f"{idx}. {o[1]} - {o[4]} ({o[5]} dona)"
        if len(text) > 50:
            text = text[:47] + "..."
        keyboard.add(InlineKeyboardButton(
            text=text,
            callback_data=f"del_order:{o[0]}"
        ))
    keyboard.add(InlineKeyboardButton("🔙 Ortga", callback_data="back_to_main"))
    await message.answer("O'chirmoqchi bo'lgan buyurtmani tanlang:", reply_markup=keyboard)

async def delete_order_callback(callback: types.CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    success, error = delete_order(order_id)
    if success:
        await callback.answer("✅ Buyurtma o'chirildi")
        await callback.message.edit_text("Buyurtma o'chirildi.")
    else:
        await callback.answer("❌ Xatolik: " + (error or "Noma'lum xato"), show_alert=True)