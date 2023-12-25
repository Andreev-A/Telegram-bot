import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from config_reader import config
from aiogram import F
from aiogram.utils.markdown import hide_link
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile
import threading
import glob
import warnings
import transform_image
from model_cyclegan import CycleGAN
from model_nst import StyleTransfer

warnings.filterwarnings("ignore")

from flask import Flask
app = Flask(__name__)
@app.route('/')
def hello_world():
    return 'Hello from Telegramm bot!'



logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.INFO, filename="OLD/py_log.log", filemode="w",
#                     format="%(asctime)s %(levelname)s %(message)s")  # логирование

bot = Bot(token=config.bot_token.get_secret_value(), parse_mode="HTML")  # объект бота

dp = Dispatcher()  # диспетчер

db_users = {}  # база алгоритмов пользователей

with open("Images/Styles/description.txt", encoding='utf-8') as f:
    styles_text = f.read()
styles_images = sorted([file for file in glob.glob('Images/Styles/*.jpg')])


def select_transform():
    buttons = [
        [types.InlineKeyboardButton(text="Перенести стиль", callback_data="button_transfer_style")],
        [types.InlineKeyboardButton(text="\U0001F40E Превратить лошадь в зебру \U0001F993",
                                    callback_data="button_into_zebra")],
        [types.InlineKeyboardButton(text="\U0001F993 Превратить зебру в лошадь \U0001F40E",
                                    callback_data="button_into_horse")]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def select_style():
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


menu = (f"{hide_link('https://raw.githubusercontent.com/Andreev-A/Telegram-bot/main/images/examples/main_image.png')}"
        f"<b>Что я могу сделать:</b>\n"
        f"\U00002705 Выбери мою или отправь мне свою\n"
        f"         фотографию, с неё я заберу стиль\n"
        f"         и перенесу его на присланное тобой фото\n"
        f"\U00002705 Если есть фотография лошади \U0001F40E,\n"
        f"         то я могу превратить её в зебру \U0001F993\n"
        f"\U00002705 Если есть фотография зебры \U0001F993,\n"
        f"         то её можно превратить в лошадь \U0001F40E\n\n"
        f"<b>Посмотри на примеры ниже и выбери</b> \U0001F447\n"
        )


@dp.message(F.text, Command('start'))
async def send_start(message: types.Message):
    db_users[message.from_user.id] = {'algorithm': '', 'style': None}
    logging.info(f"New User! Current number of users in dict: {len(db_users)}")
    await message.answer(
        f"Привет, <b>*{message.from_user.first_name}*</b>! \U0001F44B\n\n"
        f"Я - <b>*Neural style transfer*</b> бот и я создаю новые фотографии с помощью нейронных сетей.\n\n"
        f"{menu}",
        parse_mode=ParseMode.HTML, reply_markup=select_transform())


@dp.message(F.text, Command('menu'))
async def send_menu(message: types.Message):
    await message.answer(
        f"{menu}",
        parse_mode=ParseMode.HTML, reply_markup=select_transform())


async def send_style(message: types.Message):
    await message.answer(
        f"{hide_link('https://raw.githubusercontent.com/Andreev-A/Telegram-bot/main/images/examples/screen_31.png')}"
        f"<b>Посмотри на примеры ниже и выбери нужный стиль или пришли фото с твоим стилем</b> \U0001F447\n\n"
        f"<b>У меня есть такие картины:</b>\n{styles_text}\n",
        parse_mode=ParseMode.HTML, reply_markup=select_style())


@dp.callback_query(F.data.startswith("button_"))
async def callbacks_button(callback: types.CallbackQuery):
    action = callback.data.split("_", 1)[1]
    if action == "transfer_style":
        db_users[callback.from_user.id] = {'algorithm': '', 'style': None}
        await send_style(callback.message)
    elif action == "into_zebra":
        db_users[callback.from_user.id]['algorithm'] = 'horse_into_zebra'
        await callback.message.answer("<b>Пришли мне фотографию ЛОШАДИ</b> \U0001F40E", parse_mode=ParseMode.HTML)
    elif action == "into_horse":
        db_users[callback.from_user.id]['algorithm'] = 'zebra_into_horse'
        await callback.message.answer("<b>Пришли мне фотографию ЗЕБРЫ</b> \U0001F993", parse_mode=ParseMode.HTML)
    elif action.startswith("style"):
        if action == "style_photo":
            await callback.message.answer("<b>Пришли мне фотографию нужного СТИЛЯ</b>", parse_mode=ParseMode.HTML)
        else:
            style = styles_text.split('\n')[int(action.split("_")[1]) - 1]
            await callback.message.answer(f"Выбран стиль: {style}\n"
                                          "<b>Пришли мне фотографию, на которую перенесём стиль</b>",
                                          parse_mode=ParseMode.HTML)
        db_users[callback.from_user.id]['algorithm'] = action
    elif action == "menu":
        await send_menu(callback.message)
    await callback.answer()


async def cycle_gan(message, image, type_algorithm):
    if type_algorithm == 'horse_into_zebra':
        wts_path = "models_wts/horse2zebra.pth"
    elif type_algorithm == 'zebra_into_horse':
        wts_path = "models_wts/zebra2horse.pth"
    new_image = CycleGAN.run_gan(wts_path, image)
    logging.info(f"Finished CycleGAN")
    bot = Bot(token=config.bot_token.get_secret_value(), parse_mode="HTML")
    await bot.send_photo(message.chat.id, photo=BufferedInputFile(new_image.read(), filename=""))
    await bot.send_message(message.chat.id, "Надеюсь, тебе понравилось.\n Хочешь попробовать еще раз?",
                           reply_markup=select_transform())
    # await bot.close()


async def style_transfer(message, image_style, image_basic):
    new_image = StyleTransfer.run_nst(image_style, image_basic)
    logging.info(f"Finished Style Transfer")
    bot = Bot(token=config.bot_token.get_secret_value(), parse_mode="HTML")
    await bot.send_photo(message.chat.id, photo=BufferedInputFile(new_image.read(), filename=""))
    await bot.send_message(message.chat.id, "Надеюсь, тебе понравилось.\n Хочешь попробовать еще раз?",
                           reply_markup=select_transform())
    # await bot.close()


@dp.message(F.photo)
async def download_photo(message: types.Message, bot: Bot):
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
            db_users[message.from_user.id]['algorithm'] = 'style_custom'
            db_users[message.from_user.id]['style'] = photo
            await message.answer("<b>Отправь фотографию, на которую надо перенести стиль</b>",
                                 parse_mode=ParseMode.HTML)
        else:
            if user_algorithm != 'style_custom':
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


# Запуск процесса поллинга новых апдейтов
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

    # while True:
    #     try:
    #         bot.polling(none_stop=True)
    #
    #     except Exception as e:
    #         print(e)
    #         time.sleep(15)
