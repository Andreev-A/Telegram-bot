# from model_cyclegan import CycleGAN
# from model_nst import StyleTransfer
# from aiogram import Bot
# from aiogram.types import BufferedInputFile
# from config_reader import config
# import bot
# import logging
# import warnings
#
# warnings.filterwarnings("ignore")
#
# logging.basicConfig(level=logging.INFO)
#
#
# async def cycle_gan(message, image, type_algorithm):
#     if type_algorithm == 'horse_into_zebra':
#         wts_path = "models_wts/horse2zebra.pth"
#     elif type_algorithm == 'zebra_into_horse':
#         wts_path = "models_wts/zebra2horse.pth"
#
#     new_image = CycleGAN.run_gan(wts_path, image)
#
#     logging.info(f"Finished CycleGAN")
#
#     tmp_bot = Bot(token=config.bot_token.get_secret_value())
#     await tmp_bot.send_photo(message.chat.id, photo=BufferedInputFile(new_image.read(), filename=""))
#     await tmp_bot.send_message(message.chat.id, "Надеюсь, тебе понравилось.\n Хочешь попробовать еще раз?",
#                                reply_markup=bot.select_transform())
#     await tmp_bot.close()


# async def style_transfer(message, image_style, image_basic):
#     new_image = StyleTransfer.run_nst(image_style, image_basic)
#
#     logging.info(f"Finished Style Transfer")
#
#     tmp_bot = Bot(token=config.bot_token.get_secret_value())
#     await tmp_bot.send_photo(message.chat.id, photo=BufferedInputFile(new_image.read(), filename=""))
#     await tmp_bot.send_message(message.chat.id, "Надеюсь, тебе понравилось.\n Хочешь попробовать еще раз?",
#                                reply_markup=bot.select_transform())
#     await tmp_bot.close()
