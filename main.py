import telebot
import json
import os

# Сюда вставь свой токен от BotFather
TOKEN = '8214844447:AAGrB1Kg-zgPj3jx1kHUEtyYpDxJs-c0cfw'
bot = telebot.TeleBot(TOKEN)

# Настройка подсказок-команд в самой кнопке Menu
bot.set_my_commands([
    telebot.types.BotCommand("/start", "Перезапустить бота"),
    telebot.types.BotCommand("/add", "Добавить игрока (Пример: /add Дамир)"),
    telebot.types.BotCommand("/players", "Список всех участников"),
    telebot.types.BotCommand("/match", "Записать матч (Пример: /match Дамир Арман 3 1)"),
    telebot.types.BotCommand("/table", "Показать таблицу турнира"),
    telebot.types.BotCommand("/help", "Инструкция как пользоваться")
])

# Наша "база данных" в оперативной памяти
# Пока бот запущен, данные хранятся здесь.
players = {}
# Функция сохранения данных в файл
def save_data():
    with open('fifo_data.json', 'w', encoding='utf-8') as f:
        json.dump(players, f, ensure_ascii=False, indent=4)

# Функция загрузки данных при старте
def load_data():
    global players
    if os.path.exists('fifo_data.json'):
        with open('fifo_data.json', 'r', encoding='utf-8') as f:
            players = json.load(f)

# Сразу вызываем загрузку, чтобы бот вспомнил старых игроков
load_data()

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Бот для FIFA готов! \nЧтобы добавить игрока, напиши: /add Имя")

# ШАГ 1: Бот получает команду /add и задает вопрос
@bot.message_handler(commands=['add'])
def start_add_player(message):
    msg = bot.send_message(message.chat.id, "Введите имя нового игрока:")
    # Говорим боту: "Жди следующее сообщение и передай его в функцию save_player_name"
    bot.register_next_step_handler(msg, save_player_name)

# ШАГ 2: Бот получает имя и сохраняет его
def save_player_name(message):
    name = message.text.strip()
    
    if name in players:
        bot.reply_to(message, f"Игрок {name} уже есть в списке!")
    else:
        players[name] = {
            'games': 0, 'wins': 0, 'draws': 0, 'losses': 0, 
            'goals_scored': 0, 'goals_conceded': 0, 'points': 0
        }
        save_data()
        bot.reply_to(message, f"✅ Игрок {name} добавлен в турнир!")


# Команда для просмотра списка игроков
@bot.message_handler(commands=['players'])
def show_players(message):
    if not players:
        bot.reply_to(message, "В турнире пока нет игроков.")
    else:
        list_text = "📋 Список участников:\n"
        for name in players:
            list_text += f"- {name}\n"
        bot.reply_to(message, list_text)

# ШАГ 1: Бот получает команду /match (из меню или текстом)
@bot.message_handler(commands=['match'])
def start_match_record(message):
    if not players:
        bot.reply_to(message, "❌ В турнире еще нет игроков! Сначала добавь их через /add")
        return
    
    # Бот просто задает вопрос и НЕ ПЫТАЕТСЯ ничего считать сразу
    msg = bot.send_message(
        message.chat.id, 
        "Введите результат матча в формате:\n`Игрок1 Игрок2 Счет1 Счет2` \n\nПример: `Дамир Арман 3 1`",
        parse_mode="Markdown"
    )
    
    # А вот теперь мы говорим: "Жди следующее сообщение и отправь его в функцию calculate_match"
    bot.register_next_step_handler(msg, calculate_match)

# ШАГ 2: Бот получил твое сообщение с именами и цифрами
def calculate_match(message):
    try:
        parts = message.text.split()
        
        if len(parts) != 4:
            bot.reply_to(message, "❌ Ошибка! Нужно ввести 4 значения через пробел: Игрок1 Игрок2 Счет1 Счет2.")
            return

        p1_name, p2_name = parts[0], parts[1]
        p1_score, p2_score = int(parts[2]), int(parts[3])

        if p1_name not in players or p2_name not in players:
            bot.reply_to(message, f"❌ Игрока {p1_name} или {p2_name} нет в списке!")
            return

        # --- Тот же код расчета, что был раньше ---
        players[p1_name]['goals_scored'] += p1_score
        players[p1_name]['goals_conceded'] += p2_score
        players[p2_name]['goals_scored'] += p2_score
        players[p2_name]['goals_conceded'] += p1_score
        players[p1_name]['games'] += 1
        players[p2_name]['games'] += 1

        if p1_score > p2_score:
            players[p1_name]['wins'] += 1
            players[p1_name]['points'] += 3
            players[p2_name]['losses'] += 1
        elif p1_score < p2_score:
            players[p2_name]['wins'] += 1
            players[p2_name]['points'] += 3
            players[p1_name]['losses'] += 1
        else:
            players[p1_name]['draws'] += 1
            players[p1_name]['points'] += 1
            players[p2_name]['draws'] += 1
            players[p2_name]['points'] += 1

        bot.reply_to(message, f"✅ Результат записан: {p1_name} {p1_score}:{p2_score} {p2_name}")
        save_data()
        
    except ValueError:
        bot.reply_to(message, "❌ Ошибка! Счет должен быть числами. Попробуй еще раз через /match")
    except Exception as e:
        bot.reply_to(message, "❌ Что-то пошло не так. Попробуй еще раз.")

# Команда для просмотра таблицы
@bot.message_handler(commands=['table'])
def show_table(message):
    if not players:
        bot.reply_to(message, "Таблица пуста.")
        return

    # Сортируем игроков по очкам (от большего к меньшему)
    sorted_players = sorted(players.items(), key=lambda x: x[1]['points'], reverse=True)

    table_text = "🏆 **ТУРНИРНАЯ ТАБЛИЦА:**\n\n"
    table_text += "Игрок | И | О | З:П\n"
    table_text += "-------------------\n"

    for name, stats in sorted_players:
        table_text += f"{name} | {stats['games']} | {stats['points']} | {stats['goals_scored']}:{stats['goals_conceded']}\n"

    bot.send_message(message.chat.id, table_text, parse_mode="Markdown")

# Запуск бота
print("Бот запущен и ждет игроков...")
bot.infinity_polling()