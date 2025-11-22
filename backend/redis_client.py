"""
Redis client for session management and PubSub
"""
import redis
import json
import os
from typing import Optional, Dict, List
from models import CanvasState, ChatMessage


class RedisClient:
    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            decode_responses=True
        )
        self.pubsub = self.client.pubsub()

    def save_canvas_state(self, session_id: str, state: CanvasState):
        """Save canvas state to Redis"""
        key = f"canvas:{session_id}"
        self.client.setex(
            key,
            3600 * 24,  # 24 hours TTL
            state.model_dump_json()
        )

    def get_canvas_state(self, session_id: str) -> Optional[CanvasState]:
        """Retrieve canvas state from Redis"""
        key = f"canvas:{session_id}"
        data = self.client.get(key)
        if data:
            return CanvasState.model_validate_json(data)
        return None

    def publish_canvas_update(self, session_id: str, state: CanvasState):
        """Publish canvas update to all subscribers"""
        channel = f"canvas_updates:{session_id}"
        self.client.publish(channel, state.model_dump_json())

    def subscribe_to_canvas(self, session_id: str):
        """Subscribe to canvas updates"""
        channel = f"canvas_updates:{session_id}"
        self.pubsub.subscribe(channel)
        return self.pubsub

    def save_chat_message(self, message: ChatMessage):
        """Save chat message to Redis Stream"""
        stream_key = f"chat:{message.session_id}"
        self.client.xadd(
            stream_key,
            {
                "user_id": message.user_id,
                "username": message.username,
                "message": message.message,
                "timestamp": message.timestamp.isoformat()
            },
            maxlen=1000  # Keep last 1000 messages
        )

    def get_chat_history(self, session_id: str, count: int = 50) -> List[ChatMessage]:
        """Retrieve chat history"""
        stream_key = f"chat:{session_id}"
        messages = self.client.xrevrange(stream_key, count=count)

        chat_messages = []
        for msg_id, msg_data in reversed(messages):
            chat_messages.append(ChatMessage(
                session_id=session_id,
                user_id=msg_data["user_id"],
                username=msg_data["username"],
                message=msg_data["message"],
                timestamp=msg_data["timestamp"]
            ))
        return chat_messages

    def publish_chat_message(self, message: ChatMessage):
        """Publish chat message to all subscribers"""
        channel = f"chat_updates:{message.session_id}"
        self.client.publish(channel, message.model_dump_json())
