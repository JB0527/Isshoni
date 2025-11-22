"""
WebSocket connection manager for real-time collaboration
"""
from typing import Dict, Set
from fastapi import WebSocket
import json
import asyncio


class ConnectionManager:
    def __init__(self):
        # session_id -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Connect a new WebSocket client"""
        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()

        self.active_connections[session_id].add(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        """Disconnect a WebSocket client"""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)

            # Clean up empty sessions
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast_to_session(self, session_id: str, message: dict):
        """Broadcast message to all clients in a session"""
        if session_id not in self.active_connections:
            return

        # Convert message to JSON
        json_message = json.dumps(message)

        # Send to all connections in the session
        dead_connections = set()
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_text(json_message)
            except Exception as e:
                # Mark dead connections for removal
                dead_connections.add(connection)

        # Clean up dead connections
        for connection in dead_connections:
            self.disconnect(connection, session_id)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific client"""
        json_message = json.dumps(message)
        await websocket.send_text(json_message)

    def get_session_count(self, session_id: str) -> int:
        """Get number of active connections in a session"""
        if session_id in self.active_connections:
            return len(self.active_connections[session_id])
        return 0
