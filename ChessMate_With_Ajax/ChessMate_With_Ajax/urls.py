from django.urls import path
from chessboard import views as chess_views
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', chess_views.home, name='home'),
    path('join/', chess_views.join, name='join'),
    path('login/', chess_views.user_login, name='login'),
    path('logout/', chess_views.user_logout, name='logout'),
    path('history/', chess_views.history, name='history'),
    path('rules/', chess_views.rules, name='rules'),
    path('about/', chess_views.about, name='about'),
    path('journal/', chess_views.journal, name='journal'),
    path('challenge/<int:opponent_id>/', chess_views.challenge_player, name='challenge_player'),
    path('game_state/<int:game_id>/', chess_views.game_state, name='game_state'),
    path('journal/add/<int:game_id>/', chess_views.add_journal_entry, name='add_journal_entry'),
    path('journal/edit/<int:entry_id>/', chess_views.edit_journal_entry, name='edit_journal_entry'),
    path('journal/delete/<int:entry_id>/', chess_views.delete_journal_entry, name='delete_journal_entry'),
    path('accept_challenge/<int:challenge_id>/', chess_views.accept_challenge, name='accept_challenge'),
    path('decline_challenge/<int:challenge_id>/', chess_views.decline_challenge, name='decline_challenge'),
    path('game_state/<int:game_id>/', chess_views.game_state, name='game_state'),
    path('check_active_game/', chess_views.check_active_game, name='check_active_game'),
    path('fetch_pending_challenges/', chess_views.fetch_pending_challenges, name='fetch_pending_challenges'),
    path('fetch_new_game_updates/', chess_views.fetch_new_game_updates, name='fetch_new_game_updates'),
    path('game/delete/<int:game_id>/', chess_views.delete_game, name='delete_game'),

]
