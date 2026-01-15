import logging
import asyncio
import random

from aiogram.filters import Command
from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext



logging.basicConfig(level=logging.INFO)

API_TOKEN = '8590969495:AAEtOVdLqcHeUQ5xdw0QBFCsD2SnBJU5gUY'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

main_router = Router()
dp.include_router(main_router)
dictionary = {'cat': ['кот', 'кошка'], 'dog': ['собака'], 'tiger': ['тигр']}
stats = {}


class Form(StatesGroup):
    eng_word = State()
    rus_trans = State()

class Testing(StatesGroup):
    waiting_answer = State()

class DeleteWord(StatesGroup):
    eng_word_del = State()

def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text='✅Добавить', callback_data='add')
    kb.button(text='❓Тестирование', callback_data='testing')
    kb.button(text='❌Удалить', callback_data='delete')
    kb.button(text='📈Статистика', callback_data='stats')
    kb.button(text='📚Вывод словаря', callback_data='output')
    kb.adjust(2)
    return kb.as_markup()

@main_router.message(Command('start'))
async def start(message: types.Message):
    await message.answer('Привет, я твой новый чат-бот!', reply_markup=main_menu())

@main_router.callback_query(F.data == 'add')
async def add(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer(text='Напишите слово на английском🌎')
    await call.answer()
    await state.set_state(Form.eng_word)

@main_router.message(Form.eng_word)
async def get_eng_word(message: types.Message, state: FSMContext):
    await state.update_data(eng_word=message.text)
    await message.answer('Напишите перевод слова на русском ❓:')
    await state.set_state(Form.rus_trans)

@main_router.message(Form.rus_trans)
async  def get_rus_trans(message: types.Message, state: FSMContext):
    await state.update_data(rus_trans=message.text)
    await message.answer('Слово успешно добавлено 😎')
    data = await state.get_data()
    eng_word = data.get('eng_word')
    rus_trans = data.get('rus_trans')
    translations = [word.strip(',.!?1234567890 ') for word in rus_trans.split(', ')]
    dictionary[eng_word] = dictionary.get(eng_word, []) + translations
    if eng_word not in stats:
        stats[eng_word] = [0, 0]
    await message.answer('Выберите действие:', reply_markup=main_menu())

def ensure_stats_key(eng: str):
    if eng not in stats:
        stats[eng] = [0, 0]

@main_router.callback_query(F.data == 'testing')
async def testing(call: types.CallbackQuery, state: FSMContext):
    words = list(dictionary.items())
    if len(words) == 0:
        await call.message.answer('Словарь пуст! Сначала добавьте слова!')
        await call.answer()
        return
    correct_stats = {}
    random.shuffle(words)
    await state.set_state(Testing.waiting_answer)
    await state.update_data(
        words=words,
        idx=0,
        correct=0,
        correct_stats=correct_stats,
    )
    await call.message.answer('Начинаем тестирование!')
    await call.answer()
    await send_next_word(state, call.message.chat.id, call.bot, call)

async def send_next_word(state: FSMContext, chat_id: int, bot, message):
    data = await state.get_data()
    words = data['words']
    idx = data['idx']
    if idx >= len(words):
        correct = data['correct']
        total = len(words)
        correct_stats = data.get('correct_stats', {})
        text = (
            f"Тест завершен!\n"
            f"Результат: {correct}/{total}\n\n"
            f"Статистика по словам(верно/всего):\n"
            +"\n".join(
                f"-{eng}: {v[0]}/{v[1]}"
                for eng, v in correct_stats.items()
            )
        )
        await bot.send_message(chat_id, text)
        await state.clear()
        await message.answer('Выберите действие:', reply_markup=main_menu())
        return
    eng, rus_list = words[idx]
    await state.update_data(current_eng=eng, current_rus=rus_list)

    await bot.send_message(
        chat_id,
        f"Переведи слово: **{eng}**",
        parse_mode="Markdown"
    )

@main_router.message(Testing.waiting_answer)
async def testing_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    eng = data["current_eng"]
    rus_list = data["current_rus"]
    user_answer = (message.text or "").strip().lower()
    variants = [r.lower() for r in rus_list]
    correct_stats = data.get("correct_stats", {})
    if eng not in correct_stats:
        correct_stats[eng] = [0, 0]

    correct_stats[eng][1] += 1
    ensure_stats_key(eng)
    stats[eng][1] += 1

    if user_answer in variants:
        await message.answer("Верно!")
        await state.update_data(correct=data["correct"] + 1)

        correct_stats[eng][0] += 1
        stats[eng][0] += 1
    else:
        await message.answer(f"Неправильно! Правильно: {', '.join(rus_list)}")
    idx = data["idx"] + 1
    await state.update_data(idx=idx, correct_stats=correct_stats)
    await send_next_word(state, message.chat.id, message.bot, message)


@main_router.callback_query(F.data == 'delete')
async def delete_word_prompt(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(action='deleting')
    message_text = f"Введите слово, которое хотели бы удалить на английском:"

    await call.message.answer(message_text)
    await call.answer()
    await state.set_state(DeleteWord.eng_word_del)


@main_router.message(DeleteWord.eng_word_del)
async def handle_delete_word(message: types.Message, state: FSMContext):
    data = await state.get_data()
    word = message.text.strip().lower()
    if word in dictionary:
        dictionary.pop(word)
        stats.pop(word, None)
        await message.answer(f'✅ Слово "{word}" удалено!')
    else:
        await message.answer(f'❌ Слово "{word}" не найдено!')
    await message.answer('Выберите действие:', reply_markup=main_menu())

@main_router.callback_query(F.data == 'stats')
async def show_stats(call: types.CallbackQuery):
    result = 'Статистика изученных слов: \n'
    for word in stats:
        stats[word][0], stats[word][1] = stats[word]
        percent = (stats[word][0] / stats[word][1]) * 100
        if percent >= 80:
            advice = 'Отлично усвоено!'
        elif percent >= 60:
            advice = 'Хорошо усвоено!'
        elif percent >= 40:
            advice = 'Нужно повторить!'
        else:
            advice = 'Требуется серьезная работа!'
        result += f'- {word} {stats[word][0]} из {stats[word][1]}: {percent:.0f}% - {advice}\n'
    await call.message.answer(text=result)
    await call.answer()
    await call.message.answer('Выберите действие:', reply_markup=main_menu())
    await call.answer()

@main_router.callback_query(F.data == 'output')
async def output(call: types.CallbackQuery):
    result = 'Ваш словарь: \n'
    i = 1
    for key, value in dictionary.items():
        result += f"{i}. {key} - {', '.join(value)}\n"
        i += 1
    await call.message.answer(text=result)
    await call.answer()
    await call.message.answer('Выберите действие:', reply_markup=main_menu())
    await call.answer()


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

