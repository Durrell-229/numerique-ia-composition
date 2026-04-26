import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academie_numerique.settings')

# Import routing after settings
django_asgi_app = get_asgi_application()

from notifications import routing as notifications_routing

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            notifications_routing.websocket_urlpatterns
        )
    ),
})
