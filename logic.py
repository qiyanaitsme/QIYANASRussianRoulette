import random

ITEMS = [
    "🍫 Шоколадка", "📞 Телефон", "🔄 Смена барабана", "🎯 Замена патрона", "🎇 Выстрел в воздух",
    "🩺 Аптечка", "🔍 Лупа", "🛡️ Бронежилет", "💣 Граната", "🔫 Дополнительный патрон", "⏳ Песочные часы"
]
LIVE_BULLET, BLANK_BULLET, EMPTY = "live", "blank", "empty"
ITEM_DESCRIPTIONS = {
    "🍫 Шоколадка": "Восстанавливает 1 жизнь (макс. 3).",
    "📞 Телефон": "Мама подскажет тип следующего патрона (10% правда).",
    "🔄 Смена барабана": "Перемешивает оставшиеся патроны.",
    "🎯 Замена патрона": "Меняет случайный патрон на пустой.",
    "🎇 Выстрел в воздух": "Пропускает ваш ход.",
    "🩺 Аптечка": "Восстанавливает до 2 жизней (макс. 3).",
    "🔍 Лупа": "Показывает количество боевых патронов в барабане.",
    "🛡️ Бронежилет": "Защищает от следующего боевого патрона (одноразовый).",
    "💣 Граната": "Наносит 1 урон противнику напрямую.",
    "🔫 Дополнительный патрон": "Добавляет 1 случайный патрон в барабан.",
    "⏳ Песочные часы": "Пропускает ход противника оппонента."
}

class Game:
    def __init__(self, player1_id, player1_username, player2_id=None, player2_username=None):
        self.players = {
            1: {"lives": 3, "items": self._generate_items(), "tgid": player1_id, "username": player1_username or str(player1_id), "armor": False, "skip_next": False, "must_shoot": False},
            2: {"lives": 3, "items": self._generate_items(), "tgid": player2_id, "username": player2_username or str(player2_id) if player2_id else "Ожидается", "armor": False, "skip_next": False, "must_shoot": False}
        }
        self.revolver = self._generate_revolver()
        self.current_player = 1
        self.last_damage = None

    def _generate_items(self):
        items = []
        for _ in range(6):
            item = random.choice(ITEMS)
            if item != "🍫 Шоколадка" and item != "🩺 Аптечка" and item in items:
                continue
            items.append(item)
        return items

    def _generate_revolver(self, size=6):
        live = random.randint(1, 3)
        blank = random.randint(1, 2)
        empty = size - live - blank
        bullets = [LIVE_BULLET] * live + [BLANK_BULLET] * blank + [EMPTY] * empty
        random.shuffle(bullets)
        return bullets

    def _add_random_item(self, player_num):
        if not self.players[player_num]["items"]:
            new_item = random.choice(ITEMS)
            self.players[player_num]["items"].append(new_item)
            return f"🎁 Вы получили новый предмет: {new_item}!"
        return None

    def update_player2(self, player2_id, player2_username):
        self.players[2]["tgid"] = player2_id
        self.players[2]["username"] = player2_username or str(player2_id)

    def shoot(self):
        if not self.revolver:
            self.revolver = self._generate_revolver()
        bullet = self.revolver.pop(0)
        shooter = self.current_player
        target = 3 - shooter
        
        if bullet == LIVE_BULLET:
            if self.players[shooter]["armor"]:
                self.players[shooter]["armor"] = False
                self.last_damage = None
                result = "🛡️ Бронежилет защитил вас от урона!"
            else:
                self.players[shooter]["lives"] -= 1
                self.last_damage = (shooter, target)
                result = None
        else:
            self.last_damage = None
            result = None
        
        self.players[shooter]["must_shoot"] = False
        item_replenish = self._add_random_item(shooter)
        
        if self.players[target]["skip_next"]:
            self.players[target]["skip_next"] = False
            self.current_player = shooter
        else:
            self.current_player = target
        return bullet, result, item_replenish

    def use_item(self, item):
        player = self.players[self.current_player]
        opponent = self.players[3 - self.current_player]
        if item not in player["items"]:
            return "Предмет уже использован!"
        player["items"].remove(item)
        
        if item == "🍫 Шоколадка" and player["lives"] < 3:
            player["lives"] += 1
            result = "✅ Вы восстановили 1 жизнь!"
        elif item == "📞 Телефон":
            truth = random.random() < 0.1
            next_bullet = self.revolver[0] if self.revolver else EMPTY
            result = f"📞 Мама говорит: следующий {'холостой' if next_bullet == BLANK_BULLET else 'боевой' if next_bullet == LIVE_BULLET else 'пустой'} {'(правда)' if truth else '(может врать)'}"
        elif item == "🔄 Смена барабана":
            random.shuffle(self.revolver)
            result = "🔄 Барабан перемешан!"
        elif item == "🎯 Замена патрона" and self.revolver:
            self.revolver[random.randint(0, len(self.revolver) - 1)] = EMPTY
            result = "🎯 Один патрон заменен на пустой!"
        elif item == "🎇 Выстрел в воздух":
            self.current_player = 3 - self.current_player
            result = "🎇 Вы пропустили ход!"
        elif item == "🩺 Аптечка" and player["lives"] < 3:
            player["lives"] = min(3, player["lives"] + 2)
            result = "✅ Вы восстановили до 2 жизней!"
        elif item == "🔍 Лупа":
            live_count = sum(1 for bullet in self.revolver if bullet == LIVE_BULLET)
            result = f"🔍 Боевых патронов в барабане: {live_count}"
        elif item == "🛡️ Бронежилет":
            player["armor"] = True
            result = "🛡️ Вы надели бронежилет!"
        elif item == "💣 Граната":
            opponent["lives"] -= 1
            self.last_damage = (self.current_player, 3 - self.current_player)
            result = "💣 Вы нанесли 1 урон противнику!"
        elif item == "🔫 Дополнительный патрон":
            new_bullet = random.choice([LIVE_BULLET, BLANK_BULLET, EMPTY])
            self.revolver.append(new_bullet)
            result = f"🔫 Добавлен {'боевой' if new_bullet == LIVE_BULLET else 'холостой' if new_bullet == BLANK_BULLET else 'пустой'} патрон!"
        elif item == "⏳ Песочные часы":
            opponent["skip_next"] = True
            result = "⏳ Противник пропустит следующий ход!"
        else:
            result = "✅ Предмет использован!"
        
        item_replenish = self._add_random_item(self.current_player)
        if item_replenish:
            result += f"\n{item_replenish}"
        
        player["must_shoot"] = True
        return result

    def get_status(self, player_num=None):
        p1 = self.players[1]
        p2 = self.players[2]
        status = (
            f"🎲 **Статус игры**\n"
            f"❤️ Жизни:\n"
            f"  • @{p1['username']} ({p1['tgid']}) — {p1['lives']}\n"
            f"  • @{p2['username']} ({p2['tgid']}) — {p2['lives']}\n"
            f"👉 Ход: @{self.players[self.current_player]['username']} ({self.players[self.current_player]['tgid']})"
        )
        if player_num:
            items = self.players[player_num]["items"]
            items_text = "Нет" if not items else "\n  • " + "\n  • ".join(items)
            status += f"\n\n📦 **Ваши предметы**: {items_text}"
            if self.players[player_num]["armor"]:
                status += "\n🛡️ У вас активен бронежилет!"
            if self.players[player_num]["skip_next"]:
                status += "\n⏳ Ваш следующий ход пропущен!"
            if self.players[player_num]["must_shoot"]:
                status += "\n🔫 Вы должны выстрелить!"
        if self.last_damage:
            shooter, target = self.last_damage
            status += (
                f"\n\n💥 **Урон**: @{self.players[shooter]['username']} ({self.players[shooter]['tgid']}) ➡️ "
                f"@{self.players[target]['username']} ({self.players[target]['tgid']})"
            )
        return status