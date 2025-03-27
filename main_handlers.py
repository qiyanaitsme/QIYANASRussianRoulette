from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from tortoise import Tortoise
import random
import string
from datetime import datetime
from inline import main_menu, game_menu, items_menu, rules_menu, items_description_menu
from logic import Game, ITEM_DESCRIPTIONS
from models import GameRoom, PlayerState
from config import MAX_GAMES, CHANNEL_ID

active_games = {}

class JoinGameState(StatesGroup):
    waiting_for_password = State()

WELCOME_TEXT = (
    "🎲 **Добро пожаловать в Смертельную игру!** 🎲\n\n"
    "Это напряжённая дуэль, где два игрока по очереди стреляют из револьвера, "
    "используют предметы и пытаются выжить. Выбирайте действия с умом!\n\n"
    "Нажмите кнопку ниже, чтобы начать, или узнайте больше о правилах и предметах."
)

RULES_TEXT = (
    "📜 **Правила игры** 📜\n\n"
    "1. У каждого игрока 3 жизни.\n"
    "2. В револьвере случайное число боевых, холостых и пустых патронов.\n"
    "3. Игроки ходят по очереди: можно выстрелить или использовать предмет.\n"
    "4. Боевой патрон отнимает 1 жизнь у стреляющего (если нет бронежилета).\n"
    "5. Некоторые предметы требуют выстрела после использования.\n"
    "6. Побеждает тот, кто останется в живых. Возможна ничья!\n\n"
    "Удачи в игре!"
)

async def start_command(message: types.Message):
    await message.answer(WELCOME_TEXT, reply_markup=main_menu(), parse_mode="Markdown")

async def create_game(callback: types.CallbackQuery):
    if len(active_games) >= MAX_GAMES:
        await callback.message.edit_text(
            "Достигнут лимит игр! Подождите, пока одна из комнат освободится.",
            reply_markup=main_menu()
        )
        return
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    username = callback.from_user.username or str(callback.from_user.id)
    room = await GameRoom.create(
        password=password,
        player1_id=callback.from_user.id,
        player1_username=username
    )
    game = Game(callback.from_user.id, username)
    active_games[room.id] = game
    await PlayerState.create(user_id=callback.from_user.id, game_room=room, items=game.players[1]["items"])
    await callback.message.edit_text(
        f"Комната создана!\nПароль: `{password}`\nОжидаем второго игрока...",
        reply_markup=None,
        parse_mode="Markdown"
    )

async def join_game(callback: types.CallbackQuery):
    await callback.message.edit_text("Введите пароль комнаты:")
    await JoinGameState.waiting_for_password.set()

async def process_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    room = await GameRoom.filter(password=password, is_active=True, player2_id__isnull=True).first()
    if not room:
        await message.answer("Комната не найдена или уже занята! Попробуйте снова:", reply_markup=main_menu())
        await state.finish()
        return
    
    username = message.from_user.username or str(message.from_user.id)
    room.player2_id = message.from_user.id
    room.player2_username = username
    room.current_turn = 1
    await room.save()
    
    game = active_games[room.id]
    game.update_player2(message.from_user.id, username)
    player2_state = await PlayerState.create(user_id=message.from_user.id, game_room=room, items=game.players[2]["items"])
    if not player2_state:
        await message.answer("Ошибка при создании игрока! Попробуйте снова.", reply_markup=main_menu())
        await state.finish()
        return
    
    player1_state = await PlayerState.filter(game_room=room, user_id=room.player1_id).first()
    await message.bot.send_message(
        room.player1_id,
        "Второй игрок подключился! Игра начинается.\n" + game.get_status(1),
        reply_markup=game_menu(player1_state.items),
        parse_mode="Markdown"
    )
    await message.answer(
        "Вы вошли в игру! Ожидайте хода первого игрока.\n" + game.get_status(2),
        reply_markup=None,
        parse_mode="Markdown"
    )
    await state.finish()

async def game_action(callback: types.CallbackQuery):
    room = await GameRoom.filter(player1_id=callback.from_user.id).first() or \
           await GameRoom.filter(player2_id=callback.from_user.id).first()
    if not room or room.id not in active_games:
        await callback.answer("Игра не найдена!", show_alert=True)
        return
    
    game = active_games[room.id]
    player_num = 1 if room.player1_id == callback.from_user.id else 2
    if game.current_player != player_num:
        await callback.answer("Сейчас не ваш ход!", show_alert=True)
        return
    
    player_state = await PlayerState.filter(user_id=callback.from_user.id, game_room=room).first()
    
    if callback.data == "shoot":
        bullet, result, item_replenish = game.shoot()
        player_state.items = game.players[player_num]["items"]
        await player_state.save()
        text = f"🔫 **Выстрел**: {'Боевой! (-1 жизнь)' if bullet == 'live' else 'Холостой' if bullet == 'blank' else 'Пустой'}"
        if result:
            text += f"\n{result}"
        if item_replenish:
            text += f"\n{item_replenish}"
        text += f"\n\n{game.get_status(player_num)}"
        
        if game.players[1]["lives"] <= 0 and game.players[2]["lives"] <= 0:
            text += f"\n\n**🤝 Ничья! Оба игрока погибли!**"
            await end_game(room, callback.message.bot)
        elif game.players[1]["lives"] <= 0:
            text += f"\n\n**🏆 Победитель: @{game.players[2]['username']} ({game.players[2]['tgid']})**\n**💀 Проигравший: @{game.players[1]['username']} ({game.players[1]['tgid']})**"
            await end_game(room, callback.message.bot, game.players[2], game.players[1])
        elif game.players[2]["lives"] <= 0:
            text += f"\n\n**🏆 Победитель: @{game.players[1]['username']} ({game.players[1]['tgid']})**\n**💀 Проигравший: @{game.players[2]['username']} ({game.players[2]['tgid']})**"
            await end_game(room, callback.message.bot, game.players[1], game.players[2])
        else:
            await notify_opponent(room, game, callback.message.bot, player_num)
        await callback.message.edit_text(text, reply_markup=game_menu(player_state.items, game.players[player_num]["must_shoot"]), parse_mode="Markdown")
    
    elif callback.data == "use_item":
        if game.players[player_num]["must_shoot"]:
            await callback.answer("Вы должны выстрелить!", show_alert=True)
            return
        if not player_state.items:
            await callback.answer("У вас нет предметов!", show_alert=True)
            return
        await callback.message.edit_text(f"Выберите предмет:\n\n{game.get_status(player_num)}", reply_markup=items_menu(player_state.items), parse_mode="Markdown")
    
    elif callback.data.startswith("item_"):
        if game.players[player_num]["must_shoot"]:
            await callback.answer("Вы должны выстрелить!", show_alert=True)
            return
        item = callback.data.replace("item_", "")
        result = game.use_item(item)
        await player_state.fetch_related("game_room")
        player_state.items = game.players[player_num]["items"]
        await player_state.save()
        
        text = f"📦 **Предмет**: {item}\n{result}\n\n{game.get_status(player_num)}"
        if game.players[1]["lives"] <= 0 and game.players[2]["lives"] <= 0:
            text += f"\n\n**🤝 Ничья! О ESS игрока погибли!**"
            await end_game(room, callback.message.bot)
        elif game.players[1]["lives"] <= 0:
            text += f"\n\n**🏆 Победитель: @{game.players[2]['username']} ({game.players[2]['tgid']})**\n**💀 Проигравший: @{game.players[1]['username']} ({game.players[1]['tgid']})**"
            await end_game(room, callback.message.bot, game.players[2], game.players[1])
        elif game.players[2]["lives"] <= 0:
            text += f"\n\n**🏆 Победитель: @{game.players[1]['username']} ({game.players[1]['tgid']})**\n**💀 Проигравший: @{game.players[2]['username']} ({game.players[2]['tgid']})**"
            await end_game(room, callback.message.bot, game.players[1], game.players[2])
        else:
            await notify_opponent(room, game, callback.message.bot, player_num)
        await callback.message.edit_text(text, reply_markup=game_menu(player_state.items, game.players[player_num]["must_shoot"]), parse_mode="Markdown")
    
    elif callback.data == "back_to_game":
        await callback.message.edit_text(game.get_status(player_num), reply_markup=game_menu(player_state.items, game.players[player_num]["must_shoot"]), parse_mode="Markdown")

async def notify_opponent(room, game, bot, current_player):
    opponent_id = room.player2_id if current_player == 1 else room.player1_id
    opponent_num = 2 if current_player == 1 else 1
    opponent_state = await PlayerState.filter(user_id=opponent_id, game_room=room).first()
    
    if opponent_state is None:
        await bot.send_message(opponent_id, "Ошибка состояния игры. Игра завершена.", reply_markup=main_menu())
        await end_game(room, bot)
        return
    
    await bot.send_message(
        opponent_id,
        "Ваш ход!\n" + game.get_status(opponent_num),
        reply_markup=game_menu(opponent_state.items, game.players[opponent_num]["must_shoot"]),
        parse_mode="Markdown"
    )

async def end_game(room, bot, winner=None, loser=None):
    game_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    end_message = "🎲 **Игра окончена!**"
    if winner and loser:
        end_message += f"\n🏆 **Победитель**: @{winner['username']} ({winner['tgid']})\n💀 **Проигравший**: @{loser['username']} ({loser['tgid']})"
    elif not winner and not loser:
        end_message += "\n🤝 **Ничья! Оба игрока погибли!**"
    end_message += "\n\nВернитесь в меню для новой игры!"
    
    for player_id in [room.player1_id, room.player2_id]:
        if player_id:
            await bot.send_message(player_id, end_message, reply_markup=main_menu(), parse_mode="Markdown")
    
    channel_message = (
        f"🎲 **Результат игры** 🎲\n"
        f"**Игроки**: @{room.player1_username} ({room.player1_id}) vs @{room.player2_username} ({room.player2_id})\n"
        f"**Дата**: {game_date}\n"
    )
    if winner and loser:
        channel_message += f"**Победитель**: @{winner['username']} ({winner['tgid']})\n**Проигравший**: @{loser['username']} ({loser['tgid']})"
    else:
        channel_message += "**Итог**: Ничья! Оба игрока погибли!"
    
    try:
        await bot.send_message(CHANNEL_ID, channel_message, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка при отправке в канал: {e}")
    
    del active_games[room.id]
    await room.delete()

async def show_rules(callback: types.CallbackQuery):
    await callback.message.edit_text(RULES_TEXT, reply_markup=rules_menu(), parse_mode="Markdown")

async def show_items(callback: types.CallbackQuery):
    items_text = "📦 **Описание предметов** 📦\n\n"
    for item, desc in ITEM_DESCRIPTIONS.items():
        items_text += f"**{item}**: {desc}\n"
    await callback.message.edit_text(items_text, reply_markup=items_description_menu(), parse_mode="Markdown")

async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu(), parse_mode="Markdown")

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_command, commands=["start"])
    dp.register_callback_query_handler(create_game, lambda c: c.data == "create_game")
    dp.register_callback_query_handler(join_game, lambda c: c.data == "join_game")
    dp.register_callback_query_handler(show_rules, lambda c: c.data == "show_rules")
    dp.register_callback_query_handler(show_items, lambda c: c.data == "show_items")
    dp.register_callback_query_handler(back_to_main, lambda c: c.data == "back_to_main")
    dp.register_message_handler(process_password, state=JoinGameState.waiting_for_password)
    dp.register_callback_query_handler(game_action, lambda c: c.data in ["shoot", "use_item", "back_to_game"] or c.data.startswith("item_"))