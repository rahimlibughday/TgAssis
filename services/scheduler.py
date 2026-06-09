import asyncio
import datetime
import json
import aiosqlite
from aiogram import Bot, types
from services.llm_service import llm

DB_PATH = "database.db"
llm_lock = asyncio.Lock()

async def generate_day_schedule(theme: str) -> list:
    """Шаг 1: Быстрое создание расписания с жестким форматированием"""
    def _sync():
        # Кардинально меняем структуру, убирая любые совпадения с промптом Шага 2
        prompt = (
    f"<|im_start|>system\n"
    f"Ты — строгий генератор JSON. Ты выводишь только валидные JSON-массивы. "
    f"Не пиши обычный текст, вступления или блоки markdown. Только чистый JSON.\n"
    f"Задача: Создай расписание из 2 постов для темы: '{theme}'.\n"
    f"Ожидаемый формат строго:\n"
    f"[\n"
    f"  {{\"time\": \"10:30\", \"subtheme\": \"Конкретная подтема\"}},\n"
    f"  {{\"time\": \"16:15\", \"subtheme\": \"Другая конкретная подтема\"}}\n"
    f"]<|im_end|>\n"
    f"<|im_start|>user\n"
    f"Сгенерируй JSON для темы: '{theme}'<|im_end|>\n"
    f"<|im_start|>assistant\n["
)
        # Мы сами пишем открывающую скобку "[", вынуждая модель продолжить JSON
        response = llm(prompt, max_tokens=300, temperature=0.2) 
        
        # Дописываем скобку обратно для парсера, так как мы передали её в промпт
        res_text = "[" + response["choices"][0]["text"].strip()
        return res_text

    raw_json = await asyncio.to_thread(_sync)
    try:
        start_idx = raw_json.find('[')
        end_idx = raw_json.rfind(']') + 1
        if start_idx != -1 and end_idx != 0:
            raw_json = raw_json[start_idx:end_idx]
        return json.loads(raw_json)
    except Exception as e:
        print(f"[ERROR JSON]: Ошибка расписания: {e}. Ответ: {raw_json}")
        return []
    

async def generate_single_post(subtheme: str) -> str:
    """Шаг 2: Генерация ЕМКОГО поста с примером безопасной HTML-разметки"""
    def _sync():
        prompt = (
            f"System: Ты — профессиональный отраслевой эксперт и главный редактор. "
            f"Ты пишешь статьи для Telegram-канала на грамотном русском языке. Без латиницы и воды.\n\n"
            f"ЖЕСТКИЕ ПРАВИЛА ХТМЛ-РАЗМЕТКИ:\n"
            f"1. Допускается использовать ТОЛЬКО ДВА тега: <b>текст</b> для жирного и <i>текст</i> для курсива.\n"
            f"2. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать теги <strong>, <em>, Markdown-звездочки (*) или нижние подчеркивания (_).\n"
            f"3. Каждая открытая скобка тега ДОЛЖНА быть закрыта: если написал <b>, обязан в конце слова/фразы поставить </b>. Никогда не оставляй теги открытыми!\n"
            f"4. ОБЪЕМ: 1000–2500 символов с пробелами (2-3 коротких абзаца) и ровно ОДИН вопрос в конце.\n\n"
            f"ПРИМЕР ИДЕАЛЬНОГО ОТВЕТА:\n"
            f"<b>Заголовок поста</b>\n"
            f"Вот пример текста, где мы выделяем <b>важные слова</b> жирным тегом. А здесь мы можем использовать <i>курсив для терминов</i>. Все теги строго закрываются внутри одной строки.\n\n"
            f"Как вы думаете, применим ли этот подход на практике?\n"
            f"User: Напиши емкий пост с использованием безопасных тегов <b> и <i> на тему: '{subtheme}'.\n"
            f"Assistant:"
        )
        
        response = llm(
            prompt, 
            max_tokens=600, 
            temperature=0.6, # Немного снизил для стабильности тегов
            stop=["<|im_end|>", "<|endoftext|>", "User:", "System:"] 
        )
        return response["choices"][0]["text"].strip()

    return await asyncio.to_thread(_sync)


async def send_admin_notification(bot: Bot, channel: str, event_type: str, data: dict = None):
    """
    Универсальная функция для отправки уведомлений администраторам канала.
    
    Допустимые event_type:
    - 'staging_success'    : Контент-план на день успешно сгенерирован и записан в БД
    - 'generation_started' : Бот зафиксировал тайм-аут и приступает к написанию лонгрида
    - 'post_published'     : Пост успешно сгенерирован и опубликован в канал
    - 'post_failed'        : Произошла ошибка на этапе генерации или отправки в Telegram
    """
    if data is None:
        data = {}

    # Формируем HTML-текст сообщения в зависимости от типа события
    if event_type == "staging_success":
        schedule = data.get("schedule", [])
        text = (
            f"📋 <b>[Контент-план создан]</b>\n"
            f"Для канала <b>{channel}</b> успешно сгенерировано расписание на сегодня!\n\n"
            f"<b>Всего постов:</b> {len(schedule)}\n"
        )
        for idx, item in enumerate(schedule, 1):
            t = item.get('time', '12:00')
            sub = item.get('subtheme', 'Без подтемы')
            text += f"{idx}. 🕒 <b>{t}</b> — {sub}\n"

    elif event_type == "generation_started":
        pub_time = data.get("pub_time", "00:00")
        topic = data.get("topic", "Без темы")
        text = (
            f"🚀 <b>[Запуск генерации]</b>\n"
            f"Время <b>{pub_time}</b>. Начинаю сборку лонгрида для канала <b>{channel}</b>.\n\n"
            f"📝 <b>Тема:</b> {topic}\n"
            f"⏳ <i>Процесс пошел, это займет 1-2 минуты...</i>"
        )

    elif event_type == "post_published":
        pub_time = data.get("pub_time", "00:00")
        topic = data.get("topic", "Без темы")
        text = (
            f"🔥 <b>[Успешная публикация]</b>\n"
            f"Пост в канал <b>{channel}</b> успешно улетел!\n\n"
            f"🕒 <b>Запланированное время:</b> {pub_time}\n"
            f"📝 <b>Тема:</b> {topic}"
        )

    elif event_type == "post_failed":
        pub_time = data.get("pub_time", "00:00")
        topic = data.get("topic", "Без темы")
        error = data.get("error", "Неизвестная ошибка")
        text = (
            f"❌ <b>[Ошибка публикации]</b>\n"
            f"Не удалось отправить пост в канал <b>{channel}</b>!\n\n"
            f"🕒 <b>Время поста:</b> {pub_time}\n"
            f"📝 <b>Тема:</b> {topic}\n"
            f"⚠️ <b>Ошибка:</b> <code>{error}</code>"
        )
    else:
        print(f"[⚠️ Нотификатор]: Передан неизвестный event_type: '{event_type}'")
        return

    # Запрашиваем админов канала и рассылаем уведомления в ЛС
    try:
        admins = await bot.get_chat_administrators(chat_id=channel)
        for admin in admins:
            # Отправляем только реальным пользователям, игнорируем других ботов
            if not admin.user.is_bot:
                try:
                    await bot.send_message(chat_id=admin.user.id, text=text, parse_mode="HTML")
                except Exception as send_err:
                    # Бот не сможет написать админу, если тот не нажал /start в ЛС у бота
                    print(f"[⚠️ Нотификатор]: Не удалось отправить в ЛС пользователю {admin.user.id}: {send_err}")
    except Exception as e:
        print(f"[❌ Нотификатор]: Ошибка сбора списка админов для чата {channel}: {e}")

async def posting_loop(bot: Bot):
    days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    
    while True:
        now = datetime.datetime.now()
        current_day = days[now.weekday()]
        current_date_str = now.strftime("%Y-%m-%d")
        current_time_str = now.strftime("%H:%M")
        
        # Открываем базу на весь цикл проверки
        async with aiosqlite.connect(DB_PATH) as db:
            
            # === ЭТАП 1: ЛЕГКИЙ СТЭЙДЖИНГ РАСПИСАНИЯ ===
            async with db.execute(
                "SELECT id FROM channel_posts WHERE created_at = ?", (current_date_str,)
            ) as c:
                has_posts_today = await c.fetchone()
                
            # ИСПРАВЛЕНО: Этот IF теперь НАХОДИТСЯ внутри async with db
            if not has_posts_today:
                print(f"[🤖 Планировщик]: Проверяю планы и создаю расписание на сегодня ({current_date_str})...")
                
                async with db.execute(
                    "SELECT channel, post_ideas FROM WEEKLY_PLANS WHERE day_name = ?", (current_day,)
                ) as cursor:
                    active_plans = await cursor.fetchall()
                    
                for channel, theme in active_plans:
                    try:
                        member = await bot.get_chat_member(chat_id=channel, user_id=bot.id)
                        if member.status not in ['administrator', 'creator']:
                            print(f"[⚠️ Пропуск]: Бот не админ в {channel}")
                            continue
                            
                        async with llm_lock:
                            schedule = await generate_day_schedule(theme)
                        
                        if not schedule:
                            print(f"[⚠️ Пропуск]: Модель вернула пустой список для {channel}")
                            continue

                        for item in schedule:
                            post_time = item.get('time', '12:00')
                            post_topic = item.get('subtheme', 'Новая подтема')
                            
                            await db.execute("""
                                INSERT INTO channel_posts (channel, day_name, post_text, publish_at_time, status, created_at)
                                VALUES (?, ?, ?, ?, 'pending', ?)
                            """, (channel, current_day, post_topic, post_time, current_date_str))
                        
                        await db.commit()
                        print(f"[📋 Стейджинг]: Расписание для {channel} успешно загружено ({len(schedule)} постов).")
                        await send_admin_notification(
                            bot=bot, 
                            channel=channel, 
                            event_type="staging_success", 
                            data={"schedule": schedule} # Передаем массив со временем и темами
                        )
                                        

                    except Exception as e:
                        print(f"[⚠️ Ошибка стейджинга {channel}]: {e}")

            # === ЭТАП 2: ГЕНЕРАЦИЯ ПОСТА И ПУБЛИКАЦИЯ ===
            # ИСПРАВЛЕНО: Этот блок теперь ТОЖЕ внутри общего async with db
            async with db.execute("""
                SELECT id, channel, post_text, publish_at_time FROM channel_posts 
                WHERE created_at = ? AND status = 'pending' AND publish_at_time <= ?
            """, (current_date_str, current_time_str)) as ready_cursor:
                ready_posts = await ready_cursor.fetchall()
                
            for post_id, channel, target_subtheme, pub_time in ready_posts:
                print(f"[🚀 Постинг]: Время {pub_time}. Генерирую емкий лонгрид для {channel}...")
                await send_admin_notification(
                    bot=bot, 
                    channel=channel, 
                    event_type="generation_started", 
                    data={"pub_time": pub_time, "topic": target_subtheme}
                )
                try:
                    async with llm_lock:
                        full_post_text = await generate_single_post(target_subtheme)
                    
                    msg = await bot.send_message(chat_id=channel, text=full_post_text, parse_mode="HTML")
                    
                    await db.execute("""
                        UPDATE channel_posts 
                        SET status = 'published', post_text = ?, message_id = ? 
                        WHERE id = ?
                    """, (full_post_text, msg.message_id, post_id))
                    await db.commit()
                    print(f"[🔥 Успех]: Пост на тему '{target_subtheme}' опубликован!")
                    await send_admin_notification(
                        bot=bot, 
                        channel=channel, 
                        event_type="post_published", 
                        data={"pub_time": pub_time, "topic": target_subtheme}
                    )
                except Exception as post_err:
                    print(f"[❌ Ошибка публикации]: {post_err}")
                    await send_admin_notification(
                        bot=bot, 
                        channel=channel, 
                        event_type="post_failed", 
                        data={"pub_time": pub_time, "topic": target_subtheme, "error": str(post_err)}
                    )
                    
        # Соединение закрылось автоматически, спим 20 секунд до следующего круга
        await asyncio.sleep(20)

async def choose_channel_topic():
    system_prompt = (
        "Ты — эксперт-теолог и футуролог. Ты пишешь строго на русском языке.\n"
        "Твоя задача — предложить ОДНУ тему для канала. Без кавычек, без лишних слов.\n"
        "СТРОГОЕ ПРАВИЛО: Ответ должен быть не длиннее 5 слов!\n"
        "Пример ответа: 'Психология будущего'"
        )

    prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\nПредложи тему<|im_end|>\n<|im_start|>assistant\n"

    def _sync():
        response = llm(
            prompt,
            max_tokens=15,
            temperature=0.8,
            stop=["\n", "<|im_end|>", "User:", "System:"]
        )
        return response['choices'][0]['text'].strip()

    async with llm_lock:
        text = await asyncio.to_thread(_sync)
        
  
    clean_text = text.replace('"', '').replace("'", "").replace("\n", " ").strip()
        
    if len(clean_text) > 80:
        # Режем строго по словам, чтобы не оборвать букву на полуслове
        words = clean_text.split()
        clean_text = " ".join(words[:5]) # Берем только первые 5 слов
        
    return clean_text