import time
from collections import defaultdict
from aiogram import types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit=3, time_limit=2):
        """
        rate_limit: nechta so'rovga ruxsat
        time_limit: qancha vaqt oralig'ida (sekund)
        """
        self.rate_limit = rate_limit
        self.time_limit = time_limit
        self.user_last_time = defaultdict(list)
        super().__init__()

    async def on_process_message(self, message: types.Message, data: dict):
        user_id = message.from_user.id
        now = time.time()
        
        # Foydalanuvchining so'nggi so'rovlari vaqtlarini tozalash
        self.user_last_time[user_id] = [t for t in self.user_last_time[user_id] if now - t < self.time_limit]
        
        if len(self.user_last_time[user_id]) >= self.rate_limit:
            # So'rovlar soni chegaradan oshdi
            await message.answer("⏳ Juda ko'p so'rov yubordingiz. Biroz kuting.")
            raise CancelHandler()  # So'rovni bekor qilish
        
        self.user_last_time[user_id].append(now)