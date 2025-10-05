import asyncio
import logging
import sys
import aiosqlite
import datetime
import re
import os
import tracemalloc


from aiogram import Bot, Dispatcher, html, Router
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
router = Router()

#Текстовые маски для фильтрации сообщений
only_name_pattern = re.compile(rf'^\s*{BOTNAME}\s*$', re.IGNORECASE)
with_extra_pattern = re.compile(rf'^\s*{BOTNAME}\s+(.+)$', re.IGNORECASE)


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

        create_activities = '''
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                deadline DATETIME DEFAULT '23:59:59',
                is_fail INTEGER DEFAULT 0,
                proof_or_fail_link TEXT,
                happened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            '''

        print("Выполняю запрос Users:")
        print(create_users)
        await db.execute(create_users)

        print("Выполняю запрос Files:")
        print(create_activities)
        await db.execute(create_activities)

        await db.commit()
        print("Таблицы Users и Files готовы.")
    

async def user_exists(message: Message):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        # Сначала убедимся, что юзер есть в таблице Users
        cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ? AND is_active = 1", (message.from_user.id,))
        row = await cursor.fetchone()
        print(f'=============== ROW: {row}')
        if not row:
            return False
        return True


@router.message(Command(commands=["register", "reg"]))
async def register_user(message: Message):
    telegram_id = message.from_user.id
    async with aiosqlite.connect(settings.DB_PATH) as db:
        # Проверяем, есть ли пользователь
        async with db.execute("SELECT telegram_id, is_active FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                # Добавляем нового пользователя
                await db.execute(
                    "INSERT INTO users (telegram_id, username, is_active) VALUES (?, ?, ?)",
                    (telegram_id, message.from_user.username, 1)
                )
                await db.commit()
                await message.answer("✅ Вы успешно зарегистрированы!")
            else:
                user_id, is_active = row
                if is_active == 0:
                    # Если был неактивным, делаем активным
                    await db.execute("UPDATE users SET is_active = 1 WHERE telegram_id = ?", (user_id,))
                    await db.commit()
                    await message.answer("♻️ Вы снова активированы!")
                else:
                    await message.answer("⚠️ Вы уже зарегистрированы и активны.")

@router.message(Command(commands=["unreg"]))
async def unregister_user(message: Message):
    telegram_id = message.from_user.id
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute("SELECT id, is_active FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                await message.answer("⚠️ Вы не зарегистрированы.")
            else:
                user_id, is_active = row
                if is_active == 0:
                    await message.answer("ℹ️ Вы уже не активны.")
                else:
                    await db.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
                    await db.commit()
                    await message.answer("❌ Вы успешно деактивированы.")
    
@router.message(Command(commands=["me"]))
async def my_info(message: Message):
    telegram_id = message.from_user.id
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute("SELECT id, telegram_id, username, free_days, added_at, is_active FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                await message.answer("⚠️ Нет нихуя, пиздец.")
            else:
                id, telegram_id, username, free_days, added_at, is_active = row
                print(row)
                print(id, telegram_id, username, free_days, added_at, is_active)
                await message.answer(f'id: {id},\nTG id: {telegram_id},\nusername: {username},\nfree_days: {free_days},\nadded_at: {added_at},\nis_active: {is_active}\n')

@router.message(Command(commands=["setvac"]))
async def set_vacation(message: Message):
    telegram_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    free_days = int(args[1])
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("UPDATE users SET free_days = ? WHERE telegram_id = ?", (free_days, telegram_id,))
        await db.commit()
        await message.answer(f'Количество отгулов изменено: {free_days}')
            

# async def save_file_to_db(telegram_id: int, file_path: str):
#     async with aiosqlite.connect(settings.DB_PATH) as db:
#         # ищем пользователя
#         async with db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
#             row = await cursor.fetchone()
#             if row is None:
#                 print(f"⚠️ Пользователь {telegram_id} не найден")
#                 return False
#             user_id = row[0]

#         created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         await db.execute(
#             "INSERT INTO activities (user_id, proof_or_fail_link, happened_at) VALUES (?, ?, ?)",
#             (user_id, file_path, created_at)
#         )
#         await db.commit()
#         print(f"✅ Файл {file_path} добавлен в базу для user_id={user_id}")
#         return True


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
    print('========== сохраняем файл... ==========')

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

    elif message.video_note:
        file_id = message.video_note.file_id
        file_name = f"video_note_{file_id}.mp4"  # видео в кружке обычно mp4

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


async def save_proof(telegram_id: int, proof_link):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        # Сначала убедимся, что юзер есть в таблице Users
        cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cursor.fetchone()

        # if row is None:
            
            # # если нет — добавляем
            # await db.execute(
            #     "INSERT INTO Users (telegram_id, username) VALUES (?, ?)",
            #     (telegram_id, username)
            # )
            # await db.commit()
            # cursor = await db.execute("SELECT id FROM Users WHERE telegram_id = ?", (telegram_id,))
            # row = await cursor.fetchone()

        user_id = row[0]

        # Формируем ссылку на сообщение
        # chat_link_id = str(chat_id).replace("-100", "")  # для супергрупп
        # proof_link = f"https://t.me/c/{chat_link_id}/{message_id}"

        # Сохраняем в Activities
        await db.execute(
            "INSERT INTO activities (user_id, proof_or_fail_link) VALUES (?, ?)",
            (user_id, proof_link)
        )
        await db.commit()

        print(f"Proof сохранён: {proof_link}")
        return proof_link
    
async def save_fail(message: Message, fail_link):
    # if await user_exists(message):
    async with aiosqlite.connect(settings.DB_PATH) as db:        
        user_id = message.from_user.id
        await db.execute("""
            INSERT INTO activities (user_id, proof_or_fail_link, is_fail)
            VALUES (?, ?, ?)
        """, (user_id, fail_link, 1))
        await db.commit()
        await message.answer(f"Файл сохранён в {fail_link}")




# async def get_statistics(message: Message):
#     # if user_exists(message):
#     async with aiosqlite.connect(settings.DB_PATH) as db:
#         cursor = await db.execute("""
#             SELECT 
#                 u.telegram_id,
#                 u.username,
#                 u.added_at,
#                 u.is_active,
#                 a.happened_at,
#                 COUNT(a.id) AS activities_count
#             FROM Users u
#             LEFT JOIN Activities a ON u.id = a.user_id
#             GROUP BY u.id
#             ORDER BY u.added_at ASC
#         """)
#         rows = await cursor.fetchall()

#     stats = []
#     for row in rows:
#         telegram_id, username, added_at, is_active, activities_count, happened_at = row
#         stats.append(
#             f"👤 {username or '—'} (ID {telegram_id})\n"
#             f"   ▶️ Активен: {'✅' if is_active else '❌'}\n"
#             f"   📅 Добавлен: {added_at}\n"
#             f"   📊 Proof-активностей: {activities_count}\n"
#         )
#     return "\n".join(stats) if stats else "Пока нет пользователей."

async def get_users_stats(user_id: int, current_month: bool = False):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        if current_month:
            query = """
                SELECT a.happened_at, a.proof_or_fail_link, a.is_fail
                FROM activities a
                WHERE a.user_id = ?
                AND DATE(a.happened_at) >= DATE('now','start of month','-1 month')
                AND DATE(a.happened_at) < DATE('now','start of month')
                ORDER BY a.happened_at ASC
            """
        else:
            query = """
                SELECT a.happened_at, a.proof_or_fail_link, a.is_fail
                FROM activities a
                WHERE a.user_id = ?
                AND DATE(a.happened_at) >= DATE('now','start of month')
                ORDER BY a.happened_at ASC
            """

        cursor = await db.execute(query, (user_id,))
        rows = await cursor.fetchall()
        await cursor.close()
        print(rows)
        return rows
    

async def get_monthly_stats(current_month: bool):
    """Возвращает статистику по всем пользователям за прошлый календарный месяц."""
    # Определяем границы прошлого месяца
    today = datetime.datetime.now()
    first_day_current_month = today.replace(day=1)
    last_day_prev_month = first_day_current_month - datetime.timedelta(days=1)
    first_day_prev_month = last_day_prev_month.replace(day=1)

    if current_month:
        start_date = first_day_current_month
        end_date = today
    else:
        start_date = first_day_prev_month.strftime("%Y-%m-%d 00:00:00")
        end_date = last_day_prev_month.strftime("%Y-%m-%d 23:59:59")

    query = """
    SELECT
        u.id AS user_id,
        u.telegram_id,
        u.username,
        u.is_active,
        a.id AS activity_id,
        a.is_fail,
        a.proof_or_fail_link,
        a.happened_at
    FROM users u
    LEFT JOIN activities a
      ON u.id = a.user_id
      AND a.happened_at BETWEEN ? AND ?
    ORDER BY u.id, a.happened_at ASC
    """

    results = []
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row  # возвращает словари
        async with db.execute(query, (start_date, end_date)) as cursor:
            async for row in cursor:
                results.append(dict(row))

    return results


@router.message()
async def handle_message(message: Message):
    print('def handle_message')
    bot = message.bot  # доступ к объекту бота внутри обработчика

    if (message.text or message.caption):
        user_message = (message.text or message.caption).lower().strip()
    else:
        user_message = ''
    
    if only_name_pattern.match(user_message):
        await message.answer('📞 Слушаю?')

    elif with_extra_pattern.match(user_message):

        if re.findall('проёб|проеб|пруф|отгул|статистика|стат', user_message):
            if await user_exists(message):
                if re.findall('проёб|проеб', user_message):
                    # await message.answer('о, проёб!))')
                    fail_path = await save_any_file(message)
                    print("save_any_file вернул:", fail_path)
                    if fail_path:
                        print('======== path =========')
                        print(fail_path)                
                        await save_fail(message, fail_path)
                    else:
                        print(f'====== no path ===== {fail_path}')
                        await message.answer('🔄 Приложите к сообщению файл с доказательством оплаты взноса и повторите команду')

                elif re.findall('пруф', user_message):
                    #проверка, существует ли пользователь:
                    async with aiosqlite.connect(settings.DB_PATH) as db:
                        cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
                        row = await cursor.fetchone()
                        if row is None:
                            await message.answer('Вы не зарегистрированы как участник челленджа!')
                        else:
                            print('=============== хоба! ===============')
                            print(f'========={message.chat.id}==========')
                            chat_link_id = str(message.chat.id).replace("-", "")  # для супергрупп
                            result_proof_link = await save_proof(
                                telegram_id=message.from_user.id,
                                proof_link = f"https://t.me/c/{chat_link_id}/{message.message_id}"
                            )
                            if result_proof_link:
                                await message.answer(f"Proof сохранён: {result_proof_link}")
                            else:
                                await message.answer(f"пруф не сохранился, я что-то нажал, и оно исчезло")
                    
                elif re.findall('отгул', user_message):
                    async with aiosqlite.connect(settings.DB_PATH) as db:
                        cursor = await db.execute("SELECT u.id, u.free_days FROM users u WHERE telegram_id = ?", (message.from_user.id,))
                        row = await cursor.fetchone()
                        free_days = row[1]
                        if free_days > 0: 
                            await message.answer("🏖 Ну, отгул - так отгул")
                            free_days -= 1
                            await db.execute("UPDATE users SET free_days = ? WHERE telegram_id = ?", (free_days, message.from_user.id,))
                            await db.commit()
                                                        
                        if free_days == 0:
                            await message.answer('🚷 У вас не осталось отгулов!')
                        else:
                            await message.answer(f'📊 У вас осталось {free_days}/3 отгулов.')                     

                elif re.findall('статистика|стат', user_message):
                    await message.answer('ща будет статистика')                              
                    statistics = await get_monthly_stats(re.findall('последняя|посл', user_message))

                    text = "📊 Статистика за прошлый месяц:\n\n"

                    for row in statistics:
                        print(row)
                        user = row["username"] or f"id{row['telegram_id']}"
                        if row["activity_id"]:
                            status = "❌ fail" if row["is_fail"] else "✅ proof"
                            link = f"[ссылка]({row['proof_or_fail_link']})" if row["proof_or_fail_link"] else ""
                            text += f"👤 {user} — {row['happened_at']} — {status} {link}\n"
                        else:
                            text += f"👤 {user} — без активностей\n"

                    await message.answer(text, parse_mode="HTML")
                            
            else:
                await message.answer('Вы не зарегестрированы в челлендже!')
        else:
            await message.answer('Я не понял 🤷‍♂️')
        
            


async def main() -> None:
    tracemalloc.start()
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    os.makedirs(downloads_folder_name, exist_ok=True) 
    await init_db()
    # And the run events dispatching
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

