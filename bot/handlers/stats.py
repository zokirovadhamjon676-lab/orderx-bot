from aiogram import types
from database.db import get_orders
from openpyxl import Workbook
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os

def back_button():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Ortga", callback_data="back_to_main"))
    return keyboard

async def export_orders_excel(message: types.Message):
    orders = get_orders()
    if not orders:
        await message.answer("📭 Buyurtma mavjud emas.", reply_markup=back_button())
        return

    # Fayl nomi
    file_path = "orders.xlsx"
    
    try:
        wb = Workbook()
        ws = wb.active
        ws.append(["№", "Klient", "Telefon", "Manzil", "Mahsulot", "Miqdor", "Sana"])

        for idx, row in enumerate(orders, start=1):
            # row: order_id, client_name, phone, address, product, amount, date
            ws.append([idx, row[1], row[2], row[3], row[4], row[5], row[6]])

        wb.save(file_path)

        # Faylni yuborish
        with open(file_path, "rb") as file:
            await message.answer_document(
                types.InputFile(file, filename="buyurtmalar.xlsx"),
                caption="📊 Buyurtmalar ro‘yxati",
                reply_markup=back_button()
            )

        # Faylni o‘chirish (ixtiyoriy)
        os.remove(file_path)

    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")