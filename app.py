#!/usr/bin/python3

import typing as t
import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram import F
from aiogram.utils.markdown import hide_link
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile
import threading
import glob
import uvicorn
from fastapi import FastAPI
import warnings
from model_cyclegan import CycleGAN
from model_nst import StyleTransfer
from src.config import load_config
from src.handlers.start import start_router
from src.middlewares.config import ConfigMiddleware

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--url", type=str, default='', help="url")
args, unknown = parser.parse_known_args()
print(args)

url = args.url

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,  # filename="OLD/py_log.log", filemode="w,"
    format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
)

config = load_config(".env")

WEBHOOK_PATH: str = f"/bot/{config.tg.token}"
WEBHOOK_URL: str = url + WEBHOOK_PATH  # config.tg.webhook_url

app = FastAPI()
bot = Bot(token=config.tg.token, parse_mode="HTML")
dp = Dispatcher()

db_users: dict = {}  # база алгоритмов пользователей

with open("Images/Styles/description.txt", encoding='utf-8') as f:
    styles_text = f.read()
styles_images = sorted([file for file in glob.glob('Images/Styles/*.jpg')])


def select_transform() -> types.InlineKeyboardMarkup:
    buttons = [
        [types.InlineKeyboardButton(text="Перенести стиль", callback_data="button_transfer_style")],
        [types.InlineKeyboardButton(text="\U0001F40E Превратить лошадь в зебру \U0001F993",
                                    callback_data="button_into_zebra")],
        [types.InlineKeyboardButton(text="\U0001F993 Превратить зебру в лошадь \U0001F40E",
                                    callback_data="button_into_horse")]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def select_style() -> types.InlineKeyboardMarkup:
    buttons = [
        [types.InlineKeyboardButton(text="1️⃣", callback_data="button_style_1"),
         types.InlineKeyboardButton(text="2️⃣", callback_data="button_style_2")],
        [types.InlineKeyboardButton(text="3️⃣", callback_data="button_style_3"),
         types.InlineKeyboardButton(text="4️⃣", callback_data="button_style_4")],
        [types.InlineKeyboardButton(text="5️⃣", callback_data="button_style_5"),
         types.InlineKeyboardButton(text="6️⃣", callback_data="button_style_6")],
        [types.InlineKeyboardButton(text="Отправить фотографию для стиля", callback_data="button_style_photo")],
        [types.InlineKeyboardButton(text="Возврат в меню", callback_data="button_menu")]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def repeat_transform() -> types.InlineKeyboardMarkup:
    buttons = [
        [types.InlineKeyboardButton(text="Повторить с выбранным стилем", callback_data="button_style_repeat")],
        [types.InlineKeyboardButton(text="Возврат в меню", callback_data="button_menu")]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


menu = (f"{hide_link('https://raw.githubusercontent.com/Andreev-A/Telegram-bot/main/images/Styles/main_image.png')}"
        "<b>Что я могу сделать:</b>\n"
        "\U00002705 Выбери мою или отправь мне свою\n"
        "         фотографию, с неё я заберу стиль\n"
        "         и перенесу его на присланное фото\n"
        "\U00002705 Если есть фотография лошади \U0001F40E,\n"
        "         то я могу превратить её в зебру \U0001F993\n"
        "\U00002705 Если есть фотография зебры \U0001F993,\n"
        "         то её можно превратить в лошадь \U0001F40E\n\n"
        "<b>Посмотри на примеры ниже и выбери</b> \U0001F447\n"
        )


@dp.message(F.text, Command('start'))
async def send_start(message: types.Message) -> None:
    db_users[message.from_user.id] = {'algorithm': '', 'style': None}
    logging.info(f"New User! Current number of users in dict: {len(db_users)}")
    await message.answer(
        f"Привет, <b>{message.from_user.first_name}</b>!  \U0001F44B\n\n"
        "Я - <b>Neural style transfer</b> бот и я создаю новые фотографии с помощью нейронных сетей.\n\n"
        f"{menu}",
        reply_markup=select_transform())


@dp.message(F.text, Command('menu'))
async def send_menu(message: types.Message) -> None:
    await message.answer(
        f"{menu}",
        reply_markup=select_transform())


@dp.message(F.text, Command('transfer_style'))
async def send_style(message: types.Message) -> None:
    await message.answer(
        f"{hide_link('https://raw.githubusercontent.com/Andreev-A/Telegram-bot/main/images/Styles/style.png')}"
        "<b>Посмотри на примеры ниже и выбери нужный стиль или пришли фото с твоим стилем</b> \U0001F447\n\n"
        f"<b>У меня есть такие картины:</b>\n{styles_text}\n",
        reply_markup=select_style())


@dp.callback_query(F.data.startswith("button_"))
async def callbacks_button(callback: types.CallbackQuery) -> None:
    action = callback.data.split("_", 1)[1]
    if action == "transfer_style":
        db_users[callback.from_user.id] = {'algorithm': '', 'style': None}
        await send_style(callback.message)
    elif action == "into_zebra":
        db_users[callback.from_user.id]['algorithm'] = 'horse_into_zebra'
        await callback.message.answer("<b>Пришли мне фотографию ЛОШАДИ</b> \U0001F40E")
    elif action == "into_horse":
        db_users[callback.from_user.id]['algorithm'] = 'zebra_into_horse'
        await callback.message.answer("<b>Пришли мне фотографию ЗЕБРЫ</b> \U0001F993")
    elif action.startswith("style"):
        if action != 'style_repeat':
            db_users[callback.from_user.id]['algorithm'] = action
        if action == "style_photo":
            await callback.message.answer("<b>Пришли мне фотографию нужного СТИЛЯ</b>")
        else:
            number = int(db_users[callback.from_user.id]['algorithm'].split("_")[1]) - 1
            style = styles_text.split('\n')[number]
            await callback.message.answer(f"Выбран стиль: {style}\n"
                                          "<b>Пришли мне фотографию, на которую перенесём стиль</b>")
    elif action == "menu":
        await send_menu(callback.message)
    await callback.answer()


async def cycle_gan(message: types.Message, image: t.Optional[t.BinaryIO], type_algorithm: str) -> None:
    wts_path = 'models_wts/horse2zebra.pth' if type_algorithm == 'horse_into_zebra' else 'models_wts/zebra2horse.pth'
    new_image = CycleGAN.run_gan(wts_path, image)
    logging.info("Finished CycleGAN")
    bot = Bot(token=config.tg.token, parse_mode="HTML")
    await bot.send_photo(message.chat.id, photo=BufferedInputFile(new_image.read(), filename=""))
    await bot.send_message(message.chat.id, "Надеюсь, тебе понравилось.\n Хочешь попробовать еще раз?",
                           reply_markup=select_transform())
    # await bot.close()


async def style_transfer(message: types.Message, image_style: t.Optional[t.Union[str, t.BinaryIO]],
                         image_basic: t.Optional[t.BinaryIO]) -> None:
    new_image = StyleTransfer.run_nst(image_style, image_basic)
    logging.info("Finished Style Transfer")
    bot = Bot(token=config.tg.token, parse_mode="HTML")
    await bot.send_photo(message.chat.id, photo=BufferedInputFile(new_image.read(), filename=""))
    await bot.send_message(message.chat.id, "Надеюсь, тебе понравилось.\n Хочешь попробовать еще раз?",
                           reply_markup=repeat_transform())
    # await bot.close()


@dp.message(F.photo)
async def download_photo(message: types.Message) -> None:
    image = message.photo[-1]
    file_info = await bot.get_file(image.file_id)
    photo = await bot.download_file(file_info.file_path)

    user_algorithm = db_users[message.from_user.id]['algorithm']
    if user_algorithm in ('horse_into_zebra', 'zebra_into_horse'):
        await message.answer("Подожди минутку и будет готово!")
        logging.info(f"Start CycleGAN {user_algorithm}")

        threading.Thread(
            target=lambda mess, img, type_algorithm:
            asyncio.run(cycle_gan(mess, img, type_algorithm)),
            args=(message, photo, user_algorithm)).start()

    elif user_algorithm.startswith("style"):
        if user_algorithm == "style_photo":
            db_users[message.from_user.id]['algorithm'] = 'style_7'
            db_users[message.from_user.id]['style'] = photo
            await message.answer("<b>Отправь фотографию, на которую надо перенести стиль</b>",
                                 parse_mode=ParseMode.HTML)
        else:
            if user_algorithm != 'style_7':
                db_users[message.from_user.id]['style'] = styles_images[int(user_algorithm.split("_")[1]) - 1]
            await message.answer(
                "Подожди не более 5 минут, и я отправлю результат  \n\U0001F40C   \U0001F40C   \U0001F40C")
            logging.info(f"Start Style Transfer")

            threading.Thread(
                target=lambda mess, style_img, basic_img:
                asyncio.run(style_transfer(mess, style_img, basic_img)),
                args=(message, db_users[message.from_user.id]['style'], photo)).start()
    else:
        await message.answer("ВЫБЕРИ что надо сделать,\nа потом отправь мне фотографии  \U0001F447",
                             reply_markup=select_transform())


@app.on_event("startup")
async def on_startup() -> None:
    await bot.set_webhook(url=WEBHOOK_URL)
    logger.info("App started")
    dp.update.outer_middleware(ConfigMiddleware(config))  # register middlewares
    dp.include_router(start_router)  # register routes


@app.post(WEBHOOK_PATH)
async def bot_webhook(update: dict) -> None:
    telegram_update = types.Update(**update)
    await dp.feed_update(bot=bot, update=telegram_update)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await bot.session.close()
    logger.info("App stopped")


async def main():
    await bot.delete_webhook()
    await dp.start_polling(bot)  # опрашиваем сервера Telegram для разработки на Windows


if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
        # asyncio.get_event_loop().run_until_complete(main())
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000) # деплой на компьютере под управлением Linux в режиме сервера

