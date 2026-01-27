from aiogram import Bot, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from aiogram.filters import CommandStart
from sqlalchemy.future import select

from bot.database.db import SessionLocal
from bot.database.models import User, Referral, ReferralInvite
from bot.config import WEBAPP_BASE_URL, REGISTRATION_URL
import logging

router = Router()
awaiting_ids = {}

# --- Клавиатуры ---

how_it_works_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Дізнатись, як це працює", callback_data="how_it_works")]
    ]
)

instruction_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Отримати доступ до інструкції", callback_data="get_instruction")]
    ]
)

reg_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔗 ПОСИЛАННЯ ДЛЯ РЕЄСТРАЦІЇ", callback_data="reg_link")],
        [InlineKeyboardButton(text="✅ Я ЗАРЕЄСТРУВАВСЯ", callback_data="registered")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_start")]
    ]
)

games_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 MINES 💎", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/minesexplorer_ukr")),
            InlineKeyboardButton(text="⚽ GOAL ⚽", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/goalrush_ukr"))
        ],
        [
            InlineKeyboardButton(text="✈️ AVIATRIX ✈️", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/aviatrixflymod_ukr")),
            InlineKeyboardButton(text="🥅 PENALTY 🥅", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/penaltygame_ukr"))
        ],
    ]
)

# --- Сообщение старта ---

async def send_start_text(bot: Bot, target, is_edit: bool = False):
    text = (
        "👋 Вітаю!\n\n"
        "Ти потрапив у бот, який використовують для отримання доходу на онлайн-іграх за допомогою автоматизованої аналітики.\n\n"
        "Система створена так, щоб навіть новачок міг швидко розібратись і почати діяти без складнощів та досвіду.\n\n"
        "💰 Користувачі, які чітко дотримуються інструкцій, заробляють 100–300$ вже з першого дня, працюючи з телефону та з дому.\n\n"
        "❗️ Важливо:\n"
        "❌ нічого зламувати не потрібно\n"
        "❌ спеціальних знань не потрібно\n"
        "❌ все вже налаштовано за тебе\n\n"
        "Увесь процес розписаний покроково — 10–15 хвилин, і ти повністю розумієш, що робити далі.\n\n"
        "👇 Тисни кнопку нижче:"
    )
    if is_edit:
        await target.edit_text(text=text, reply_markup=how_it_works_keyboard)
    else:
        await bot.send_message(chat_id=target, text=text, reply_markup=how_it_works_keyboard)


async def send_access_granted_message(bot: Bot, message: Message, user_lang: str):
    # user_lang оставляем как параметр, чтобы не ломать остальную логику
    keyboard = games_keyboard
    text = (
        "✅ ДОСТУП ОТРИМАНО ✅\n\n"
        "🔴 Інструкція:\n"
        "1️⃣ Виберіть гру нижче\n"
        "2️⃣ Відкрийте її на сайті\n"
        "3️⃣ Отримайте сигнал і повторіть його в грі ➕ 🐝"
    )
    await message.answer(text, reply_markup=keyboard)


# --- Обработчик /start ---

@router.message(CommandStart())
async def start_handler(message: Message):
    try:
        await message.answer(
            "👋 Вітаю!\n\n"
        "Ти потрапив у бот, який використовують для отримання доходу на онлайн-іграх за допомогою автоматизованої аналітики.\n\n"
        "Система створена так, щоб навіть новачок міг швидко розібратись і почати діяти без складнощів та досвіду.\n\n"
        "💰 Користувачі, які чітко дотримуються інструкцій, заробляють 100–300$ вже з першого дня, працюючи з телефону та з дому.\n\n"
        "❗️ Важливо:\n"
        "❌ нічого зламувати не потрібно\n"
        "❌ спеціальних знань не потрібно\n"
        "❌ все вже налаштовано за тебе\n\n"
        "Увесь процес розписаний покроково — 10–15 хвилин, і ти повністю розумієш, що робити далі.\n\n"
        "👇 Тисни кнопку нижче:",
            reply_markup=how_it_works_keyboard
        )

        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            bot_tag = parts[1].strip()
            async with SessionLocal() as session:
                invite_result = await session.execute(
                    select(ReferralInvite).filter_by(bot_tag=bot_tag)
                )
                invite = invite_result.scalar_one_or_none()

                if invite:
                    await session.refresh(invite)
                    referral = await session.get(Referral, invite.referral_id)
                    if referral:
                        user_result = await session.execute(
                            select(User).filter_by(telegram_id=message.from_user.id)
                        )
                        user = user_result.scalar()

                        if not user:
                            user = User(
                                telegram_id=message.from_user.id,
                                username=message.from_user.username,
                                ref_tag=referral.tag,
                                bot_tag=bot_tag
                            )
                        else:
                            user.ref_tag = referral.tag
                            user.bot_tag = bot_tag

                        session.add(user)
                        await session.commit()

                        logging.info(
                            f"👤 Новый пользователь {message.from_user.id} пришёл по ссылке: /start={bot_tag}. "
                            f"Казино: {invite.casino_link}"
                        )
                    else:
                        logging.warning(f"⚠️ Invite найден, но Referral не найден")
                else:
                    logging.warning(f"⚠️ Пользователь {message.from_user.id} пришёл с несуществующим bot_tag: {bot_tag}")

    except Exception as e:
        logging.error(f"❌ Ошибка в /start: {str(e)}")
        await message.answer("Произошла ошибка при старте.")


# --- Дальше по инструкции ---

@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery):
    await callback.answer()
    await send_start_text(bot=callback.bot, target=callback.message, is_edit=True)


@router.callback_query(F.data == "how_it_works")
async def how_it_works(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "Основа системи — Telegram-бот з аналітичним модулем, який працює зі статистикою міні-ігор та повторюваними сценаріями.\n"
        "⚙️ Що саме він робить:\n"
        " • 📊 Аналізує серії виграшів і програшів\n"
        " • 🔄 Визначає повторювані патерни\n"
        " • ✅ Показує оптимальну послідовність дій\n"
        "🛡 Ти не ризикуєш навмання і не приймаєш рішення «на удачу».\n"
        "Твоє завдання просте: повторювати готову схему, яку дає бот, вже на реальній платформі.\n"
        "👇 Тисни кнопку нижче:",
        reply_markup=instruction_keyboard
    )


@router.callback_query(F.data == "get_instruction")
async def get_instruction(callback: CallbackQuery):
    await callback.answer()

    await callback.message.answer(
        "1️⃣ Зареєструй акаунт на платформі, до якої підключений бот (посилання нижче).\n"
        "2️⃣ Після реєстрації скопіюй ID свого акаунта.\n"
        "3️⃣ Надішли ID сюди в бот.\n\n"
        "💡 Для чого це потрібно? Це необхідно, щоб система синхронізувалася саме з твоїм профілем.\n"
        "⚠️ Без ID бот не зможе активувати аналітику.\n"
        "🎥 Нижче я додав коротку відео-інструкцію, щоб тобі було простіше."
    )

    # Вставка "псевдо відео" картинкою
    await callback.message.answer_photo(
        photo="https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png"
    )

    await callback.message.answer(
        "💸 Твій перший прибуток вже зовсім поруч! Всього один крок відділяє тебе від старту. "
        "Реєструйся зараз, щоб заробити свої перші гроші вже сьогодні.",
        reply_markup=reg_inline_keyboard
    )


# --- Регистрация пользователя через кнопку ---

@router.callback_query(F.data == "reg_link")
async def send_registration_link(callback: CallbackQuery):
    await callback.answer()

    async with SessionLocal() as session:
        user_result = await session.execute(
            select(User).filter_by(telegram_id=callback.from_user.id)
        )
        user = user_result.scalar()

        referral_link = REGISTRATION_URL  # fallback
        if user and user.bot_tag:
            invite_result = await session.execute(
                select(ReferralInvite).filter_by(bot_tag=user.bot_tag)
            )
            invite = invite_result.scalar_one_or_none()
            if invite:
                referral_link = invite.casino_link

        await callback.message.answer(f"Ось посилання для реєстрації: {referral_link}")


@router.callback_query(F.data == "registered")
async def registered(callback: CallbackQuery):
    await callback.answer()
    awaiting_ids[callback.from_user.id] = True
    await callback.message.answer("🔢 Вкажи ID свого нового акаунта (тільки цифри)")


# --- Проверка ID пользователя ---

@router.message()
async def process_user_message(message: Message):
    if message.text.startswith("/"):
        print(f"❓ Ненадіслана команда: {message.text}")
        await message.answer("❗ Невідома команда.")
        return

    if message.from_user.id not in awaiting_ids:
        return

    if not message.text.isdigit():
        await message.answer("❌ Введи тільки цифри.")
        return

    await message.answer("🔍 Перевіряю ID у базі...")
    await send_access_granted_message(message.bot, message, "uk")
    awaiting_ids.pop(message.from_user.id, None)


# --- Неизвестные колбэки ---

@router.callback_query()
async def catch_unhandled_callbacks(callback: CallbackQuery):
    known_callbacks = [
        "how_it_works", "get_instruction",
        "registered", "reg_link",
        "admin_stats", "admin_add", "admin_remove", "user_list",
        "admin_list", "add_ref_link", "remove_ref_link", "referral_stats"
    ]

    if callback.data not in known_callbacks:
        await callback.answer()
        async with SessionLocal() as session:
            user_result = await session.execute(select(User).filter_by(telegram_id=callback.from_user.id))
            user = user_result.scalar()

        text = "Ви натиснули невідому кнопку!"
        await callback.message.answer(text)
