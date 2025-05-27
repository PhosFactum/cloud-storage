# src/handlers.py
from aiogram import types
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.sleep.reminders import set_sleep_reminder
from src.sleep.advice import get_sleep_advice
from src.workout.generator import generate_workout
from keyboards import (
    main_menu_keyboard,
    sleep_menu_keyboard,
    workout_levels_keyboard,
)
from src.database import (
    save_workout,
    get_user_workouts,
    save_sleep_data,
)
from src.sleep.charts import fetch_sleep_data, create_sleep_chart

# Define FSM states for sleep
class SleepStates(StatesGroup):
    waiting_for_sleep_time = State()
    waiting_for_sleep_input = State()

async def send_welcome(message: Message):
    # Greet the user and show main menu
    await message.answer(
        "Привет! Я — HabitQuest, твой помощник по ЗОЖ. Выбери действие:",
        reply_markup=main_menu_keyboard(),
    )


# Sleep handlers
async def handle_sleep_command(message: Message):
    # Open sleep submenu
    await show_sleep_menu(message)

async def show_sleep_menu(message: Message):
    # Display sleep options
    await message.answer(
        "Выберите опцию по сну:",
        reply_markup=sleep_menu_keyboard(),
    )

async def handle_sleep_menu(message: Message, state: FSMContext):
    # Handle user selection in sleep submenu
    text = message.text
    if text == "🛌 Напоминание":
        # Ask user for reminder time
        await message.answer("Во сколько поставить напоминание? Введите время в формате HH:MM")
        await state.set_state(SleepStates.waiting_for_sleep_time)
    elif text == "ℹ️ Совет по сну":
        await handle_advice(message)
    elif text == "⏰ Ввести время сна":
        # Prompt user to log sleep interval
        await message.answer("Введите время сна и подъёма в формате HH:MM-HH:MM")
        await state.set_state(SleepStates.waiting_for_sleep_input)
    elif text == "📊 Статистика":
        # Show sleep statistics
        await show_sleep_stats(message)
    elif text == "↩️ Назад":
        # Return to main menu
        await message.answer("Главное меню:", reply_markup=main_menu_keyboard())
        await state.clear()

async def handle_advice(message: Message):
    # Send sleep advice
    advice = get_sleep_advice()
    await message.answer(f"Совет по сну: {advice}")

async def process_sleep_time(message: Message, state: FSMContext):
    # Process reminder time input and schedule
    time_str = message.text.strip()
    await set_sleep_reminder(message, time_str)
    await state.clear()

async def process_sleep_input(message: Message, state: FSMContext):
    try:
        sleep_time, wake_time = message.text.split('-')
        sleep_time = sleep_time.strip()
        wake_time = wake_time.strip()

        # Сохраняем в базу
        save_sleep_data(
            user_id=message.from_user.id,
            sleep_time=sleep_time,
            wake_time=wake_time
        )

        await message.answer(
            "✅ Время сна сохранено!\n"
            f"🛌 Засыпание: {sleep_time}\n"
            f"⏰ Пробуждение: {wake_time}",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()

    except ValueError:
        await message.answer("Неверный формат. Введите как: 23:00-07:30")


async def show_sleep_stats(message: Message):
    try:
        df = fetch_sleep_data(message.from_user.id)
        if df.empty:
            await message.answer(
                "У вас пока нет записей о сне. "
                "Введите время сна через меню '⏰ Ввести время сна'",
                reply_markup=main_menu_keyboard()
            )
            return

        buf = create_sleep_chart(df)
        await message.answer_photo(
            types.BufferedInputFile(buf.read(), filename="sleep_stats.png"),
            caption="Ваша статистика сна за последние 7 дней",
            reply_markup=main_menu_keyboard()
        )
        buf.close()

    except Exception as e:
        await message.answer(
            f"Ошибка при построении графика: {e}",
            reply_markup=main_menu_keyboard()
        )


# Trainings handlers
async def handle_train_command(message: Message):
    # Redirect to training menu
    await handle_train_text(message)

async def handle_train_text(message: Message):
    # Show workout levels
    await message.answer(
        "Выбери уровень тренировки:",
        reply_markup=workout_levels_keyboard(),
    )

async def handle_my_trainings_command(message: Message):
    # Redirect to my trainings
    await handle_my_trainings_button(message)

async def handle_my_trainings_button(message: Message):
    # Show user's saved workouts
    workouts = get_user_workouts(message.from_user.id)
    if not workouts:
        await message.answer("У тебя пока нет сохранённых тренировок 💤")
        return
    response = "🏋️‍♂️ Твои 3 последние тренировки:\n\n"
    for date, level, exercises in workouts:
        response += (
            f"📅 {date}\n"
            f"🔸 Уровень: {level.title()}\n"
            f"📋 Упражнения:\n{exercises}\n\n"
        )
    await message.answer(response.strip())

async def handle_level_callback(callback: CallbackQuery):
    # Generate and save workout based on level
    mapping = {"level_easy": "лёгкая", "level_medium": "средняя", "level_hard": "тяжёлая"}
    level = mapping.get(callback.data)
    workout = generate_workout(level=level)
    save_workout(
        user_id=callback.from_user.id,
        level=level,
        exercises=workout,
    )
    await callback.message.answer(f"Твоя тренировка ({level.title()}):\n{workout}")
    await callback.answer()
