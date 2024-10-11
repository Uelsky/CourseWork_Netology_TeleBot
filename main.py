import json
import psycopg2
import random

from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from psycopg import create_db, new_user, search_words, adding_word



print('\n'.join([
        "Enter name of your DB",
        "Enter username",
        "Enter password",
        "Enter telegram token",
        "====================="
    ]))

db_name = input()
login = input()
password = input()
token_bot = input()

conn = psycopg2.connect(
        database = db_name,
        user = login,
        password = password
    )

with conn.cursor() as cur:

    create_db(cur)

    print('Start telegram bot...')

    state_storage = StateMemoryStorage()
    bot = TeleBot(token_bot, state_storage=state_storage)

    known_users = []
    userStep = {}
    buttons = []


    def show_hint(*lines):
        return '\n'.join(lines)


    def show_target(data):
        return f"{data['target_word']} -> {data['translate_word']}"


    class Command:
        ADD_WORD = 'Добавить слово ➕'
        DELETE_WORD = 'Удалить слово🔙'
        NEXT = 'Дальше ⏭'


    class MyStates(StatesGroup):
        target_word = State()
        translate_word = State()
        another_words = State()


    def get_user_step(uid):
        if uid in userStep:
            return userStep[uid]
        else:
            known_users.append(uid)
            userStep[uid] = 0
            print("New user detected, who hasn't used \"/start\" yet")
            return 0


    @bot.message_handler(commands=['cards', 'start'])
    def create_cards(message):
        cid = message.chat.id
        if cid not in known_users:
            known_users.append(cid)
            userStep[cid] = 0
            new_user(cur, cid)
            bot.send_message(cid, '\n'.join(["Привет 👋",
                                             "Давай попрактикуемся в английском языке.",
                                             "Тренировки можешь проходить в удобном для себя темпе."
                                             ]))
        markup = types.ReplyKeyboardMarkup(row_width=2)

        buttons = []
        words = search_words(cur, cid)
        random.shuffle(words)
        target_word = words[0][1]  # брать из БД
        translate = words[0][0]  # брать из БД
        target_word_btn = types.KeyboardButton(target_word)
        buttons.append(target_word_btn)
        others = [i[1] for i in words[1:4]]  # брать из БД
        other_words_btns = [types.KeyboardButton(word) for word in others]
        buttons.extend(other_words_btns)
        random.shuffle(buttons)
        next_btn = types.KeyboardButton(Command.NEXT)
        add_word_btn = types.KeyboardButton(Command.ADD_WORD)
        delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
        buttons.extend([next_btn, add_word_btn, delete_word_btn])

        markup.add(*buttons)

        greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
        bot.send_message(message.chat.id, greeting, reply_markup=markup)
        bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['target_word'] = target_word
            data['translate_word'] = translate
            data['other_words'] = others


    @bot.message_handler(func=lambda message: message.text == Command.NEXT)
    def next_cards(message):
        create_cards(message)


    @bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
    def delete_word(message):
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            print(data['target_word'])  # удалить из БД


    @bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
    def add_word(message):
        cid = message.chat.id
        userStep[cid] = 1

        print(message.text)  # сохранить в БД


    @bot.message_handler(func=lambda message: True, content_types=['text'])
    def message_reply(message):
        buttons = []
        text = message.text
        markup = types.ReplyKeyboardMarkup(row_width=2)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            target_word = data['target_word']
            if text == target_word:
                hint = show_target(data)
                hint_text = ["Отлично!❤", hint]
                next_btn = types.KeyboardButton(Command.NEXT)
                add_word_btn = types.KeyboardButton(Command.ADD_WORD)
                delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
                buttons.extend([next_btn, add_word_btn, delete_word_btn])
                hint = show_hint(*hint_text)
            else:
                hint = show_hint("Допущена ошибка!",
                                 f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
        markup.add(*buttons)
        bot.send_message(message.chat.id, hint, reply_markup=markup)


    bot.add_custom_filter(custom_filters.StateFilter(bot))

    bot.infinity_polling(skip_pending=True)

conn.close()