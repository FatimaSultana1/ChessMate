from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/game/<int:game_id>/', consumers.GameConsumer.as_asgi()),
    path('ws/user/<int:user_id>/', consumers.UserConsumer.as_asgi()),
    path('ws/new_game/', consumers.NewGameConsumer.as_asgi()),
]