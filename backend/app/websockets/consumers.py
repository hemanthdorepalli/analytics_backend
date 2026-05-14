import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for live dashboard updates.
    Each org gets its own channel group: org_{org_id}
    """

    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        # Get org from query params
        from urllib.parse import parse_qs
        query = parse_qs(self.scope.get("query_string", b"").decode())
        org_id = query.get("org_id", [None])[0]

        if not org_id:
            await self.close(code=4002)
            return

        self.room_group_name = f"org_{org_id}"
        self.user = user
        self.org_id = org_id

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        logger.info(f"ws_connected user_id={user.id} org_id={org_id}")

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info(f"ws_disconnected close_code={close_code}")

    async def receive(self, text_data):
        """Handle ping/pong for connection health."""
        try:
            data = json.loads(text_data)
            if data.get("type") == "ping":
                await self.send(json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            pass

    # Handler for dashboard.update messages from Celery tasks
    async def dashboard_update(self, event):
        await self.send(json.dumps({
            "type": "dashboard.update",
            "data": event.get("data", {}),
        }))

    # Handler for alert.triggered messages
    async def alert_triggered(self, event):
        await self.send(json.dumps({
            "type": "alert.triggered",
            "message": event.get("message", ""),
            "alert_name": event.get("alert_name", ""),
        }))

