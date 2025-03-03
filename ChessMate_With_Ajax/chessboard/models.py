from django.db import models
from django.contrib.auth.models import User
import chess

class Game(models.Model):
    player_white = models.ForeignKey(User, related_name='white_games', on_delete=models.CASCADE)
    player_black = models.ForeignKey(User, related_name='black_games', on_delete=models.CASCADE)
    fen = models.CharField(max_length=200, default=chess.STARTING_FEN)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    winner = models.ForeignKey(User, related_name='won_games', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Game {self.id} between {self.player_white} and {self.player_black}"

class Move(models.Model):
    game = models.ForeignKey(Game, related_name='moves', on_delete=models.CASCADE)
    player = models.ForeignKey(User, on_delete=models.CASCADE)
    uci = models.CharField(max_length=5)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.player.username}: {self.uci}"

class JournalEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    entry = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Journal by {self.user.username} for Game {self.game.id}"


class Challenge(models.Model):
    challenger = models.ForeignKey(User, related_name='challenges_sent', on_delete=models.CASCADE)
    opponent = models.ForeignKey(User, related_name='challenges_received', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    declined = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.challenger} challenged {self.opponent}"