"""WebSocket connection management for real-time order book and trade streaming."""

from __future__ import annotations

from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections grouped by session_id."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            try:
                self.active_connections[session_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, session_id: str, message: dict[str, Any]) -> None:
        """Broadcast a message to all active WebSocket clients for a session."""
        if session_id not in self.active_connections:
            return

        dead_connections: list[WebSocket] = []
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(session_id, dead)


ws_manager = ConnectionManager()
