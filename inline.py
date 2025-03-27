from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🎮 Создать игру", callback_data="create_game"))
    kb.add(InlineKeyboardButton("🔗 Войти в игру", callback_data="join_game"))
    kb.add(InlineKeyboardButton("📜 Правила", callback_data="show_rules"))
    kb.add(InlineKeyboardButton("📦 Предметы", callback_data="show_items"))
    return kb

def game_menu(items, must_shoot=False):
    kb = InlineKeyboardMarkup()
    if must_shoot:
        kb.add(InlineKeyboardButton("🔫 Выстрелить", callback_data="shoot"))
    else:
        if items:
            kb.add(InlineKeyboardButton("📦 Использовать предмет", callback_data="use_item"))
        kb.add(InlineKeyboardButton("🔫 Выстрелить", callback_data="shoot"))
    return kb

def items_menu(items):
    kb = InlineKeyboardMarkup()
    for item in items:
        kb.add(InlineKeyboardButton(item, callback_data=f"item_{item}"))
    kb.add(InlineKeyboardButton("⬅ Назад", callback_data="back_to_game"))
    return kb

def rules_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⬅ В главное меню", callback_data="back_to_main"))
    return kb

def items_description_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⬅ В главное меню", callback_data="back_to_main"))
    return kb