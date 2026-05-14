import os
from django.core.asgi import get_asgi_application

# Step 1: Set settings module FIRST
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Step 2: Initialize Django (loads INSTALLED_APPS, sets up registry)
django_asgi_app = get_asgi_application()

# Step 3: NOW it's safe to import from your apps
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from app.websockets.routing import websocket_urlpatterns
from app.authentication.tokens import JWTAuthMiddlewareStack

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddlewareStack(
                URLRouter(websocket_urlpatterns)
            )
        ),
    }
)