import asyncio
import logging
import sys
import aiosqlite
import datetime
import re

from os import getenv
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.types import FSInputFile
from aiogram import F
from aiogram import Bot

import secrets

# Bot token can be obtained via https://t.me/BotFather
# TOKEN = getenv("BOT_TOKEN")
TOKEN = secrets.BOT_TOKEN
BOTNAME = 'василий'

# All handlers should be attached to the Router (or Dispatcher)

dp = Dispatcher()


async def add_to_database(telegram_id, username):    
    async with aiosqlite.connect('tg_users.db') as db:
        await db.execute('CREATE TABLE IF NOT EXISTS users (telegram_id, username, date, is_active)')
        cursor = await db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        data = await cursor.fetchone()
        if data is not None:
            return
    date = f'{datetime.date.today()}'
    print(telegram_id, username, date)
    async with aiosqlite.connect('tg_users.db') as db:        
        await db.execute("INSERT INTO users (telegram_id, username, date, is_active) VALUES (?, ?, ?, ?)", 
                         (telegram_id, username, date, 1))
        await db.commit()

async def check_user_exist(message: Message):
    async with aiosqlite.connect('tg_users.db') as db:
        await db.execute('CREATE TABLE IF NOT EXISTS users (telegram_id, username, date, is_active)')
        cursor.execute("SELECT active FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()

@dp.message(Command("register"))
async def command_start_handler(message: Message) -> None:    
    telegram_id = message.from_user.id
    username = message.from_user.username
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}, {telegram_id}, {username}!")
    await add_to_database(telegram_id, username)


# async def handle_files(message: Message, bot: Bot):
#     if message.document:
#         print('=============файл!')
#         # Пользователь прислал документ
#         file_id = message.document.file_id
#         file_name = message.document.file_name
#         file = await bot.get_file(file_id)
#         await bot.download_file(file.file_path, f"downloads/{file_name}")
#         await message.answer(f"Документ {file_name} сохранён.")


# async def save_file(bot: Bot, file_id: str, file_path: str):
#     file = await bot.get_file(file_id)
#     await bot.download_file(file.file_path, file_path)


async def save_any_file(message):
    print('def save_any_file')

    bot = message.bot

    file_id = None
    file_name = None

    if message.document:
        print('==================file!')
        file_id = message.document.file_id
        file_name = message.document.file_name

    elif message.photo:
        print('======= photo =======')
        file_id = message.photo[-1].file_id
        file_name = f"photo_{file_id}.jpg"

    elif message.video:
        file_id = message.video.file_id
        file_name = f"video_{file_id}.mp4"

    elif message.audio:
        file_id = message.audio.file_id
        file_name = f"audio_{file_id}.mp3"

    elif message.voice:
        file_id = message.voice.file_id
        file_name = f"voice_{file_id}.ogg"

    else:
        print('====== None блять! ======')
        return None  # неподдерживаемый тип

    # скачиваем
    file = await bot.get_file(file_id)
    local_path = f"downloads/{file_name}"
    print(f' flie id: {file_id}, local path: {local_path}, file name:{file_name}')
    await bot.download_file(file.file_path, local_path)
    return local_path



# @dp.message()
# async def handle_message(message: Message, bot: Bot):
#     """Обрабатывает любое сообщение"""
#     user_message = (message.text or "").lower().strip()

#     if user_message == BOTNAME:
#         await message.answer("Слушаю")
#         return  

#     # проверяем, что текст начинается с "василий " и дальше идет "проеб" или "проёб"
#     if re.match(rf"^{BOTNAME}\s+прое[бё]", user_message):
#         print('======= проёб ======')
#         await message.answer("О, проёб!))")

#         # если к сообщению приложен файл — сохраняем
#         path = await save_any_file(message, bot)
#         if path:
#             await message.answer(f"Файл сохранён в {path}")
 





@dp.message()
async def handle_message(message: Message):
    print('def handle_message')
    bot = message.bot  # доступ к объекту бота внутри обработчика
    # if message.text:
    #     user_message = message.text.lower()
    # else:
    #     user_message = ''

    user_message = (message.text or message.caption).lower().strip()
    
    if BOTNAME in user_message:        
        if re.findall('проёб|проеб', user_message):
            await message.answer('о, проёб!))')
            path = await save_any_file(message)
            print("save_any_file вернул:", path)
            if path:
                print('======== path =========')
                print(path)
                await message.answer(f"Файл сохранён в {path}")
            else:
                print(f'====== no path ===== {path}')                  
        else:
            await message.answer('слушаю?')       
    else:       
        # await message.answer("Этот тип файла пока не поддерживается.")
        await message.send_copy(chat_id=message.chat.id)

    







# @dp.message()
# async def echo_handler(message: Message, bot: Bot) -> None:
#     """
#     Handler will forward receive a message back to the sender

#     By default, message handler will handle all message types (like a text, photo, sticker etc.)
#     """
#     user_message = ''
#     try:
#         # Send a copy of the received message
#         await message.send_copy(chat_id=message.chat.id)

#         # print(message)
#         if message.text:
#             user_message = message.text.lower()
#         # if message.text.lower() == BOTNAME:
#         #     await message.answer('да, я тут!')

#         if BOTNAME in user_message:
#             await message.answer('слушаю?')          

            # if re.findall('проёб|проеб', user_message):
            #     await message.answer('о, проёб!))')             

            #     if message.document:
            #         await message.answer('о, файл!')
            #         file = await bot.get_file(message.document.file_id)

            #         # Куда сохраняем на сервере
            #         local_path = f"downloads/{message.document.file_name}"

            #         await bot.download_file(file.file_path, local_path)
            #         await message.answer(f"Файл {message.document.file_name} сохранён на сервере!")
                
            #     if message.photo:
            #         await message.answer('о, фото!')
            #         file_id = message.photo[-1].file_id
            #         file_name = f"photo_{file_id}.jpg"
            #         file = await bot.get_file(file_id)        

            #         # Куда сохраняем на сервере
            #         local_path = f"downloads/{file_name}"

            #         await bot.download_file(file.file_path, local_path)
            #         await message.answer(f"Файл {file_name} сохранён на сервере!")

        
    
        # cat = FSInputFile("kek.jpg")

    # except TypeError as e:
    #     # But not all the types is supported to be copied so need to handle it
    #     await message.answer("Nice try!")
    #     print(e)

# @dp.message()
# async def handle_any_files(message: Message, bot: Bot):
#     if message.text:
#             user_message = message.text.lower()

#     if BOTNAME in user_message:
#         await message.answer('слушаю?')          

#         if re.findall('проёб|проеб', user_message):
#             await message.answer('о, проёб!))')             
            
#             if message.document:
#                 await message.answer('о, файл!')
            #     file = await bot.get_file(message.document.file_id)

            #     # Куда сохраняем на сервере
            #     local_path = f"downloads/{message.document.file_name}"

            #     await bot.download_file(file.file_path, local_path)
            #     await message.answer(f"Файл {message.document.file_name} сохранён на сервере!")
            
            # if message.photo:
            #     await message.answer('о, фото!')
            #     file_id = message.photo[-1].file_id
            #     file_name = f"photo_{file_id}.jpg"
            #     file = await bot.get_file(file_id)        

            #     # Куда сохраняем на сервере
            #     local_path = f"downloads/{file_name}"

            #     await bot.download_file(file.file_path, local_path)
            #     await message.answer(f"Файл {file_name} сохранён на сервере!")


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

