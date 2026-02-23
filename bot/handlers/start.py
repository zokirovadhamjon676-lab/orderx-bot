from aiogram import types

async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Xush kelibsiz! CRM bot.\n\n"
        "Buyruqlar:\n"
        "/add_client - Klient qo‘shish\n"
        "/clients - Klientlar ro‘yxati\n"
        "/add_order - Buyurtma qo‘shish\n"
        "/export - Excel export"
    )