import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ChessMate_with_WebSockets.settings")

from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chessboard.routing  # Ensure 'chessboard' is your app's name

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chessboard.routing.websocket_urlpatterns
        )
    ),
})
