from django.contrib import admin
from chessboard.models import Game, Challenge, Move, JournalEntry
# Register your models here.
admin.site.register(Game)
admin.site.register(Challenge)
admin.site.register(Move)
admin.site.register(JournalEntry)