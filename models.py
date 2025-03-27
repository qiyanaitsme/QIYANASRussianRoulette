from tortoise.models import Model
from tortoise.fields import IntField, CharField, BooleanField, JSONField, ForeignKeyField

class GameRoom(Model):
    id = IntField(pk=True)
    password = CharField(max_length=12, unique=True)
    player1_id = IntField()
    player1_username = CharField(max_length=32, null=True)
    player2_id = IntField(null=True)
    player2_username = CharField(max_length=32, null=True)
    is_active = BooleanField(default=True)
    current_turn = IntField(default=1)

class PlayerState(Model):
    id = IntField(pk=True)
    user_id = IntField()
    game_room = ForeignKeyField("models.GameRoom", related_name="players")
    lives = IntField(default=3)
    items = JSONField()