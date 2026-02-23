from aiogram import types
from database.db import get_orders
from openpyxl import Workbook
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def back_button():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Ortga", callback_data="back_to_main"))
    return keyboard

async def export_orders_excel(message: types.Message):
    orders = get_orders()
    if not orders:
        await message.answer("📭 Buyurtma mavjud emas.", reply_markup=back_button())
        return

    wb = Workbook()
    ws = wb.active
    ws.append(["ID", "Klient", "Telefon", "Manzil", "Mahsulot", "Miqdor", "Sana"])

    for row in orders:
        # row: order_id, client_name, client_phone, client_address, product, amount, date
        ws.append(row)

    file_path = "orders.xlsx"
    wb.save(file_path)

    with open(file_path, "rb") as file:
        await message.answer_document(file, caption="📊 Buyurtmalar ro‘yxati", reply_markup=back_button())