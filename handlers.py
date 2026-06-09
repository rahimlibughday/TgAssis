from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from time import sleep



from keyboards import get_check_admin_keyboard, get_topic_keyboard, start_make_content_plan_keyboard, start_work_on_channel_keyboard
from database import save_user_data, get_user_data, save_weekly_plan
from services.llm_service import generate_content_plan
from services.scheduler import choose_channel_topic

router = Router()

class Registration(StatesGroup):
    waiting_for_channel = State()
    waiting_for_admin_check = State()
    waiting_for_topic = State()


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        f"Привет {message.from_user.first_name}! Начинаем настройку твоего личного ИИ агента.\n\n"
        "Отправь ссылку на свой канал в формате @channel_name")
    
    await state.set_state(Registration.waiting_for_channel)

@router.message(Registration.waiting_for_channel)
async def check_channel_link(message: types.Message, state: FSMContext):
    channel = message.text.strip()
    if not channel.startswith('@') or len(channel) < 2:
        await message.answer("Пожалуйста, отправь корректную ссылку на канал в формате @channel_name")
        return
    
    await state.update_data(channel=channel)

    await message.answer(
        "Отлично! Теперь добавь меня в свой канал с правами **правами администратора** и правами на публикацию постов.\n\n"
        "Затем нажми кнопку ниже 👇",
        reply_markup=get_check_admin_keyboard()
    )

    await state.set_state(Registration.waiting_for_admin_check)

@router.callback_query(F.data == "check_admin_rights", Registration.waiting_for_admin_check)
async def check_admin_rights(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    channel = user_data.get("channel")

    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=bot.id)
        if member.status in ["administrator", "creator"]:
            await callback_query.message.answer(
                "Отлично! Теперь выбери тему для своего ИИ агента или оставь выбор на ИИ.",
                reply_markup=get_topic_keyboard()
            )
            await state.set_state(Registration.waiting_for_topic)

        else:
            await callback_query.message.answer(
                "Похоже, у меня нет прав администратора в твоем канале. Пожалуйста, добавь меня с правами администратора и попробуй снова."
            )
    except TelegramBadRequest:
        await callback_query.message.answer(
            "Похоже, я не могу получить доступ к твоему каналу. Пожалуйста, убедись, что ты правильно указал ссылку и добавил меня в канал с правами администратора."
        )

@router.callback_query(F.data == "topic_ai_choose", Registration.waiting_for_topic)
async def choose_topic(call: types.CallbackQuery, state: FSMContext):

    topic = await choose_channel_topic()
    if len(topic) > 100:
        topic = topic[:100]

    await db_finish_registration(
        user_id=call.from_user.id,
        username=call.from_user.username,
        paragraph=topic[:100],
        state=state,
        event=call
    )

@router.message(Registration.waiting_for_topic)
async def receive_topic(message: types.Message, state: FSMContext):
    await db_finish_registration(
        user_id=message.from_user.id,
        username=message.from_user.username,
        paragraph=message.text,
        state=state,
        event=message
    )

async def db_finish_registration(user_id: int, username: str, paragraph: str, state: FSMContext, event):
    user_data = await state.get_data()
    channel = user_data.get("channel")

    await save_user_data(
        user_id=user_id,
        username=username,
        channel=channel,
        paragraph=paragraph
    )

    await state.clear()

    info_message = ("Настройка завершена!"
                    f"\n\nТвой канал: {channel}"
                    f"\nТематика канала: {paragraph}")
    
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(info_message, reply_markup=start_make_content_plan_keyboard())
    else:
        await event.answer(info_message)

        await event.answer("Что бы начать работу агента, нажмите на кнопку внизу.\n\n"
                       "Вот следующие шаги:\n"
                       "1. ИИ агент создаст контент план на 1 неделю вместе с полным роад мап, который ты сможешь оценить и если-что изменить.\n"
                       "2. После утверждения контент плана, ИИ агент будет создавать посты для твоего канала и публиковать их по расписанию.\n\n"
                       "3. ИИ агент будет анализировать вовлеченность аудитории и оптимизировать контент план для максимального роста канала.\n\n"
                       "4. Ты всегда сможешь посмотреть статистику канала и эффективность публикаций, а также вносить изменения в настройки ИИ агента для достижения лучших результатов.\n\n",
                       reply_markup=start_make_content_plan_keyboard())
    

@router.callback_query(F.data == "start_content_plan")
async def start_ai_generation(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    await call.message.answer("ИИ агент начал создавать контент план для твоего канала. Это может занять некоторое время, пожалуйста, подожди...")
    await call.answer()

    user_info = await get_user_data(user_id=user_id)

    if not user_info or user_info[0] is None or user_info[1] is None:
        await call.message.answer("Похоже, я не могу найти информацию о твоем канале. Пожалуйста, начни настройку заново с помощью команды /start.")
        return
    
    channel, topic = user_info

    try:
        plan_data = await generate_content_plan(channel_name=channel, topic=topic)

        if "Ошибка" in plan_data:
            await call.message.answer("Похоже, произошла ошибка при генерации контент плана. Пожалуйста, попробуй снова позже.")
            return
        
        await save_weekly_plan(user_id=user_id, channel=channel, plan_dict=plan_data)

        text = f"📋 Ваш контент план на неделю для канала {channel}:\n\n"

        for day, ideas in plan_data.items():
            text += f"📅 {day}:\n{ideas}\n\n"
        
        text += "Если вы хотите снова сгенерировать контент план, просто нажмите кнопку ниже."

        await call.message.answer(text, reply_markup=start_make_content_plan_keyboard())
        await call.message.answer("Начинать работу над твоим каналом?", reply_markup=start_work_on_channel_keyboard())


    except Exception as e:
        await call.message.answer("Произошла ошибка при генерации контент плана. Пожалуйста, попробуй снова позже.")
        print(f"[ERROR] LLM: Error generating content plan: {e}")

@router.callback_query(F.data == "start_work_on_channel")
async def start_work_on_channel(call: types.CallbackQuery, state: FSMContext):
    await state.clear()

    await call.message.edit_text(
        "🎬 **ИИ-Агент успешно запущен в фоновом режиме!**\n\n"
        "Чтобы автопостинг и аналитика начали работать, выполни два простых шага:\n"
        "1. **Добавь этого бота в свой канал** в качестве Администратора.\n"
        "2. Дай боту разрешение на **публикацию сообщений** (Post Messages).\n\n"
        "🤖 **Как это работает:**\n"
        "Каждое утро ИИ смотрит тему дня из утвержденного контент-плана, сам генерирует пачку постов на сегодня, распределяет их по времени и загружает в систему стейджинга.\n\n"
        "⏱ Бот автоматически опубликует посты, как только наступит выбранное им время.\n\n"
        "🛑 **Как остановить ИИ-Агента?**\n"
        "Просто удали бота из администраторов канала. Он сразу потеряет доступ и перестанет слать посты.")
    
    await call.answer()