import asyncio
import logging
import sys
import aiosqlite
import datetime
import re
import os

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.types import FSInputFile
from aiogram import F
from aiogram import Bot

import settings
import private_settings

# Bot token can be obtained via https://t.me/BotFather
# TOKEN = os.getenv("BOT_TOKEN")
TOKEN = private_settings.BOT_TOKEN
BOTNAME = settings.BOTNAME

# All handlers should be attached to the Router (or Dispatcher)
downloads_folder_name = settings.DOWNLOADS_DIR
dp = Dispatcher()


async def init_db():
    print('============== создаётся бд =================')

    async with aiosqlite.connect(settings.DB_PATH) as db:
        create_users = '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username VARCHAR,
            free_days INTEGER DEFAULT 3,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )'''

        create_files = '''
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                is_fail INTEGER DEFAULT 0,
                file_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            '''

        print("Выполняю запрос Users:")
        print(create_users)
        await db.execute(create_users)

        print("Выполняю запрос Files:")
        print(create_files)
        await db.execute(create_files)

        await db.commit()
        print("Таблицы Users и Files готовы.")
    


@dp.message(Command(commands=["register", "reg"]))
async def register_user(message: Message):
    telegram_id = message.from_user.id
    async with aiosqlite.connect(settings.DB_PATH) as db:
        # Проверяем, есть ли пользователь
        async with db.execute("SELECT id, active FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                # Добавляем нового пользователя
                await db.execute(
                    "INSERT INTO users (telegram_id, active) VALUES (?, ?)",
                    (telegram_id, 1)
                )
                await db.commit()
                await message.answer("✅ Вы успешно зарегистрированы!")
            else:
                user_id, active = row
                if active == 0:
                    # Если был неактивным, делаем активным
                    await db.execute("UPDATE users SET active = 1 WHERE id = ?", (user_id,))
                    await db.commit()
                    await message.answer("♻️ Вы снова активированы!")
                else:
                    await message.answer("⚠️ Вы уже зарегистрированы и активны.")

@dp.message(Command(commands=["unreg"]))
async def unregister_user(message: Message):
    telegram_id = message.from_user.id
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute("SELECT id, active FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                await message.answer("⚠️ Вы не зарегистрированы.")
            else:
                user_id, active = row
                if active == 0:
                    await message.answer("ℹ️ Вы уже не активны.")
                else:
                    await db.execute("UPDATE Users SET active = 0 WHERE id = ?", (user_id,))
                    await db.commit()
                    await message.answer("❌ Вы успешно деактивированы.")


# async def add_user_to_database(telegram_id, username):    
#     async with aiosqlite.connect('tg_users.db') as db:
#         await db.execute('CREATE TABLE IF NOT EXISTS users (telegram_id, username, date, is_active)')
#         cursor = await db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
#         data = await cursor.fetchone()
#         if data is not None:
#             return



#     date = f'{datetime.date.today()}'Но он
#     print(telegram_id, username, date)
#     async with aiosqlite.connect('tg_users.db') as db:        
#         await db.execute("INSERT INTO users (telegram_id, username, date, is_active) VALUES (?, ?, ?, ?)", 
#                          (telegram_id, username, date, 1))
#         await db.commit()

# async def check_user_exist(message: Message):
#     async with aiosqlite.connect('tg_users.db') as db:
#         await db.execute('CREATE TABLE IF NOT EXISTS users (telegram_id, username, date, is_active)')
#         cursor.execute("SELECT active FROM users WHERE telegram_id = ?", (telegram_id,))
#         row = cursor.fetchone()



async def save_file_to_db(telegram_id: int, file_path: str):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        # ищем пользователя
        async with db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                print(f"⚠️ Пользователь {telegram_id} не найден")
                return False
            user_id = row[0]

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(
            "INSERT INTO Files (user_id, file_path, created_at) VALUES (?, ?, ?)",
            (user_id, file_path, created_at)
        )
        await db.commit()
        print(f"✅ Файл {file_path} добавлен в базу для user_id={user_id}")
        return True


# @dp.message(Command("register"))
# async def command_start_handler(message: Message) -> None:
#     telegram_id = message.from_user.id
#     username = message.from_user.username
#     await message.answer(f"Hello, {html.bold(message.from_user.full_name)}, {telegram_id}, {username}!")
#     await add_user_to_database(telegram_id, username)


def get_extension(message: Message) -> str:
    if message.document:
        return os.path.splitext(message.document.file_name)[1]  # оригинальное расширение
    elif message.photo:
        return ".jpg"  # Telegram фото без имени файла
    elif message.video:
        return os.path.splitext(message.video.file_name)[1] if message.video.file_name else ".mp4"
    elif message.audio:
        return os.path.splitext(message.audio.file_name)[1] if message.audio.file_name else ".mp3"
    elif message.voice:
        return ".ogg"  # всегда OGG
    else:
        return ""
    

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

    now = datetime.datetime.now()
    date_folder = now.strftime("%Y-%m")
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")  # для имени файла


    save_folder = os.path.join(downloads_folder_name, str(message.chat.id), date_folder)
    os.makedirs(save_folder, exist_ok=True)

    # расширение
    extension = get_extension(message)

    file_name = f'{str(message.from_user.id)}_{timestamp}{extension}'

    # скачиваем
    file = await bot.get_file(file_id)
    local_path = os.path.join(save_folder, file_name)
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
    os.makedirs(downloads_folder_name, exist_ok=True) 
    await init_db()
    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

