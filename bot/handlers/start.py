import asyncio
import logging

from aiogram import Bot, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from sqlalchemy.future import select

from bot.config import WEBAPP_BASE_URL, REGISTRATION_URL
from bot.database.db import SessionLocal
from bot.database.models import User, Referral, ReferralInvite
from bot.database.save_step import save_step

router = Router()
awaiting_ids = {}

# --- Klawiatury ---

how_it_works_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Dowiedz się, jak to działa", callback_data="how_it_works")],
        [InlineKeyboardButton(text="🆘 Pomoc", callback_data="help")]
    ]
)

instruction_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Uzyskaj dostęp do instrukcji", callback_data="get_instruction")],
        [InlineKeyboardButton(text="🆘 Pomoc", callback_data="help")]
    ]
)

reg_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔗 LINK DO REJESTRACJI", callback_data="reg_link")],
        [InlineKeyboardButton(text="✅ ZAREJESTROWAŁEM SIĘ", callback_data="registered")],
        [InlineKeyboardButton(text="⬅️ Wróć", callback_data="back_to_start")],
        [InlineKeyboardButton(text="🆘 Pomoc", callback_data="help")]
    ]
)

games_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 MINES 💎", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/minesexplorer-pl")),
            InlineKeyboardButton(text="⚽ GOAL ⚽", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/goalrush-pl"))
        ],
        [
            InlineKeyboardButton(text="✈️ AVIATRIX ✈️", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/aviatrixflymod-pl")),
            InlineKeyboardButton(text="🥅 PENALTY 🥅", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/penaltygame-pl"))
        ],
        [InlineKeyboardButton(text="🆘 Pomoc", callback_data="help")]
    ]
)

# --- Wiadomość startowa ---

async def send_start_text(bot: Bot, target, is_edit: bool = False):
    text = (
        "👋 Witaj!\n\n"
        "Witaj w bocie, który służy do uzyskiwania dochodu w grach online dzięki automatycznej analizie.\n\n"
        "System został zaprojektowany tak, aby nawet nowicjusz mógł szybko zrozumieć i zacząć działać bez trudności i doświadczenia.\n\n"
        "💰 Użytkownicy, którzy dokładnie stosują się do instrukcji, zarabiają 100–300$ już pierwszego dnia, pracując z telefonu i z domu.\n\n"
        "❗️ Ważne:\n"
        "❌ Nie trzeba niczego łamać\n"
        "❌ Nie potrzeba specjalistycznej wiedzy\n"
        "❌ Wszystko jest już ustawione dla Ciebie\n\n"
        "Cały proces jest opisany krok po kroku — 10–15 minut, i w pełni wiesz, co robić dalej.\n\n"
        "👇 Naciśnij przycisk poniżej:"
    )
    if is_edit:
        await target.edit_text(text=text, reply_markup=how_it_works_keyboard)
    else:
        await bot.send_message(chat_id=target, text=text, reply_markup=how_it_works_keyboard)

    username = target.from_user.username or f"user_{target.from_user.id}"

    async with SessionLocal() as session:
        await save_step(session, target.from_user.id, "start", username)


async def send_access_granted_message(bot: Bot, message: Message, user_lang: str):
    keyboard = games_keyboard
    text = (
        "✅ DOSTĘP PRZYZNANY ✅\n\n"
        "🔴 Instrukcja:\n"
        "1️⃣ Wybierz grę poniżej\n"
        "2️⃣ Otwórz ją na stronie\n"
        "3️⃣ Otrzymaj sygnał i powtórz go w grze ➕ 🐝"
    )
    await message.answer(text, reply_markup=keyboard)

    username = message.from_user.username or f"user_{message.from_user.id}"

    async with SessionLocal() as session:
        await save_step(session, message.from_user.id, "access_granted", username=username)


# --- Obsługa /start ---

@router.message(CommandStart())
async def start_handler(message: Message):
    try:
        await message.answer(
            "👋 Witaj!\n\n"
            "Witaj w bocie, który służy do uzyskiwania dochodu w grach online dzięki automatycznej analizie.\n\n"
            "System został zaprojektowany tak, aby nawet nowicjusz mógł szybko zrozumieć i zacząć działać bez trudności i doświadczenia.\n\n"
            "💰 Użytkownicy, którzy dokładnie stosują się do instrukcji, zarabiają 100–300$ już pierwszego dnia, pracując z telefonu i z domu.\n\n"
            "❗️ Ważne:\n"
            "❌ Nie trzeba niczego łamać\n"
            "❌ Nie potrzeba specjalistycznej wiedzy\n"
            "❌ Wszystko jest już ustawione dla Ciebie\n\n"
            "Cały proces jest opisany krok po kroku — 10–15 minut, i w pełni wiesz, co robić dalej.\n\n"
            "👇 Naciśnij przycisk poniżej:",
            reply_markup=how_it_works_keyboard
        )

        # Obsługa zaproszeń
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
                            f"👤 Nowy użytkownik {message.from_user.id} przyszedł przez link: /start={bot_tag}. "
                            f"Kazyno: {invite.casino_link}"
                        )
                    else:
                        logging.warning(f"⚠️ Invite znaleziony, ale Referral nie znaleziony")
                else:
                    logging.warning(
                        f"⚠️ Użytkownik {message.from_user.id} przyszedł z nieistniejącym bot_tag: {bot_tag}")
        username = message.from_user.username or f"user_{message.from_user.id}"

        async with SessionLocal() as session:
            await save_step(session, message.from_user.id, "start", username)

    except Exception as e:
        logging.error(f"❌ Błąd w /start: {str(e)}")
        await message.answer("Wystąpił błąd podczas startu bota.")


# --- Dalej według instrukcji ---

@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery):
    await callback.answer()
    await send_start_text(bot=callback.bot, target=callback.message, is_edit=True)


@router.callback_query(F.data == "how_it_works")
async def how_it_works(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "Podstawą systemu jest Telegram-bot z modułem analitycznym, który działa na statystykach mini-gier i powtarzalnych scenariuszach.\n\n"
        "⚙️ Co dokładnie robi:\n"
        " • 📊 Analizuje serie wygranych i przegranych\n"
        " • 🔄 Identyfikuje powtarzalne wzory\n"
        " • ✅ Pokazuje optymalną sekwencję działań\n\n"
        "<b>🛡 Nie ryzykujesz na ślepo i nie podejmujesz decyzji „na szczęście”.</b>\n\n"
        "Twoim zadaniem jest powtarzanie schematu podanego przez bota na prawdziwej platformie.\n\n"
        "👇 Naciśnij przycisk poniżej:",
        reply_markup=instruction_keyboard,
        parse_mode="HTML"
    )
    username = callback.message.from_user.username or f"user_{callback.message.from_user.id}"

    async with SessionLocal() as session:
        await save_step(session, callback.from_user.id, "how_it_works", username)


@router.callback_query(F.data == "get_instruction")
async def get_instruction(callback: CallbackQuery):
    await callback.answer()

    await callback.message.answer(
        "1️⃣ Zarejestruj konto na platformie, do której podłączony jest bot (link poniżej).\n"
        "2️⃣ Po rejestracji skopiuj ID swojego konta.\n"
        "3️⃣ Wyślij ID do bota.\n\n"
        "💡 Dlaczego? Bot musi zsynchronizować się z Twoim profilem.\n"
        "⚠️ Bez ID bot nie będzie mógł aktywować analityki.\n"
        "🎥 Poniżej znajduje się krótka instrukcja wideo."
    )

    # video_file_id = "BAACAgIAAxkBAAP-aYyjHmJ-SnA7LwJqXIg_DPWxYWcAAtaUAAK4F2FIJBwFkbz1ATo6BA"
    # await callback.message.answer_video(video=video_file_id)
    #
    # await asyncio.sleep(15)

    await callback.message.answer(
        "💸 Twój pierwszy zysk jest już blisko! Jeden krok dzieli Cię od startu. "
        "Zarejestruj się teraz, aby zarobić pierwsze pieniądze już dziś.",
        reply_markup=reg_inline_keyboard
    )
    username = callback.message.from_user.username or f"user_{callback.message.from_user.id}"

    async with SessionLocal() as session:
        await save_step(session, callback.from_user.id, "instruction", username)


# --- Rejestracja użytkownika przez przycisk ---

@router.callback_query(F.data == "reg_link")
async def send_registration_link(callback: CallbackQuery):
    await callback.answer()

    async with SessionLocal() as session:
        user_result = await session.execute(
            select(User).filter_by(telegram_id=callback.from_user.id)
        )
        user = user_result.scalar()

        referral_link = REGISTRATION_URL
        if user and user.bot_tag:
            invite_result = await session.execute(
                select(ReferralInvite).filter_by(bot_tag=user.bot_tag)
            )
            invite = invite_result.scalar_one_or_none()
            if invite:
                referral_link = invite.casino_link
        logging.info(f"Wygenerowano link rejestracyjny dla użytkownika {callback.from_user.id}: {referral_link}")
        await callback.message.answer(f"Oto link do rejestracji: {referral_link}")
    username = callback.message.from_user.username or f"user_{callback.from_user.id}"

    async with SessionLocal() as session:
        await save_step(session, callback.from_user.id, "reg_link", username)


@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("Napisz do wsparcia:\n@support_username")


@router.callback_query(F.data == "registered")
async def registered(callback: CallbackQuery):
    await callback.answer()
    awaiting_ids[callback.from_user.id] = True
    await callback.message.answer("🔢 Podaj ID swojego nowego konta (tylko cyfry)")


# --- Sprawdzenie ID użytkownika ---

@router.message()
async def process_user_message(message: Message):
    if message.video:
        logging.info(f"Received video from user {message.from_user.id}: {message.video.file_id}")
        return
    if message.text.startswith("/"):
        print(f"❓ Niezrozumiana komenda: {message.text}")
        await message.answer("❗ Nieznana komenda.")
        return

    if message.from_user.id not in awaiting_ids:
        return

    if not message.text.isdigit():
        await message.answer("❌ Wpisz tylko cyfry.")
        return
    username = message.from_user.username or f"user_{message.from_user.id}"

    async with SessionLocal() as session:
        await save_step(session, message.from_user.id, "entered_id", username)

    await message.answer("🔍 Sprawdzam ID w bazie...")
    await send_access_granted_message(message.bot, message, "pl")
    awaiting_ids.pop(message.from_user.id, None)


# --- Nieznane callbacki ---

@router.callback_query()
async def catch_unhandled_callbacks(callback: CallbackQuery):
    known_callbacks = [
        "help", "how_it_works", "get_instruction",
        "registered", "reg_link",
        "admin_stats", "admin_add", "admin_remove", "user_list",
        "admin_list", "add_ref_link", "remove_ref_link", "referral_stats"
    ]

    if callback.data not in known_callbacks:
        await callback.answer()
        async with SessionLocal() as session:
            user_result = await session.execute(select(User).filter_by(telegram_id=callback.from_user.id))
            user = user_result.scalar()

        text = "Kliknąłeś nieznany przycisk!"
        await callback.message.answer(text)
