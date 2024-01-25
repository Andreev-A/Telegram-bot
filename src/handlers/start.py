from aiogram import Router

from src.filters.is_private import IsPrivateFilter

start_router = Router()
start_router.message.filter(IsPrivateFilter())
