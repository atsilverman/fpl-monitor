#!/usr/bin/env python3
"""
WebSocket Service for FPL Monitor
Handles real-time communication between backend and iOS app
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

class WebSocketMessageType(Enum):
    """WebSocket message types"""
    NOTIFICATION = "notification"
    STATUS_UPDATE = "status_update"
    PLAYER_UPDATE = "player_update"
    GAMEWEEK_UPDATE = "gameweek_update"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"

@dataclass
class WebSocketMessage:
    """WebSocket message structure"""
    message_id: str
    message_type: WebSocketMessageType
    timestamp: datetime
    data: Dict[str, Any] = None
    user_id: Optional[str] = None
    target_users: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['message_type'] = self.message_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())

class WebSocketConnection:
    """Represents a WebSocket connection"""
    
    def __init__(self, websocket, user_id: str = None):
        self.websocket = websocket
        self.user_id = user_id
        self.connection_id = str(uuid.uuid4())
        self.connected_at = datetime.now()
        self.last_ping = datetime.now()
        self.subscriptions: Set[str] = set()
        self.is_alive = True
    
    async def send_message(self, message: WebSocketMessage) -> bool:
        """Send message to this connection"""
        try:
            await self.websocket.send_text(message.to_json())
            return True
        except Exception as e:
            print(f"Error sending message to {self.connection_id}: {e}")
            self.is_alive = False
            return False
    
    async def ping(self) -> bool:
        """Send ping to check connection health"""
        ping_message = WebSocketMessage(
            message_id=str(uuid.uuid4()),
            message_type=WebSocketMessageType.PING,
            timestamp=datetime.now()
        )
        return await self.send_message(ping_message)
    
    def subscribe(self, topic: str):
        """Subscribe to a topic"""
        self.subscriptions.add(topic)
    
    def unsubscribe(self, topic: str):
        """Unsubscribe from a topic"""
        self.subscriptions.discard(topic)
    
    def is_subscribed_to(self, topic: str) -> bool:
        """Check if subscribed to a topic"""
        return topic in self.subscriptions

class WebSocketService:
    """Service for managing WebSocket connections and real-time updates"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
        self.topic_subscribers: Dict[str, Set[str]] = {}  # topic -> set of connection_ids
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_task = None
    
    async def add_connection(self, websocket, user_id: str = None) -> str:
        """Add a new WebSocket connection"""
        connection = WebSocketConnection(websocket, user_id)
        self.connections[connection.connection_id] = connection
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection.connection_id)
        
        print(f"✅ WebSocket connection added: {connection.connection_id} (user: {user_id})")
        
        # Start heartbeat if not already running
        if not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        return connection.connection_id
    
    async def remove_connection(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            
            # Remove from user connections
            if connection.user_id and connection.user_id in self.user_connections:
                self.user_connections[connection.user_id].discard(connection_id)
                if not self.user_connections[connection.user_id]:
                    del self.user_connections[connection.user_id]
            
            # Remove from topic subscriptions
            for topic, subscribers in self.topic_subscribers.items():
                subscribers.discard(connection_id)
            
            del self.connections[connection_id]
            print(f"❌ WebSocket connection removed: {connection_id}")
    
    async def handle_message(self, connection_id: str, message_data: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        message_type = message_data.get('type')
        
        try:
            if message_type == 'ping':
                await self._handle_ping(connection)
            elif message_type == 'pong':
                await self._handle_pong(connection)
            elif message_type == 'subscribe':
                await self._handle_subscribe(connection, message_data)
            elif message_type == 'unsubscribe':
                await self._handle_unsubscribe(connection, message_data)
            else:
                print(f"Unknown message type: {message_type}")
        except Exception as e:
            print(f"Error handling message: {e}")
            await self._send_error(connection, str(e))
    
    async def broadcast_notification(self, notification_data: Dict[str, Any], target_users: List[str] = None):
        """Broadcast notification to connected users"""
        message = WebSocketMessage(
            message_id=str(uuid.uuid4()),
            message_type=WebSocketMessageType.NOTIFICATION,
            timestamp=datetime.now(),
            data=notification_data,
            target_users=target_users
        )
        
        if target_users:
            # Send to specific users
            for user_id in target_users:
                if user_id in self.user_connections:
                    for connection_id in self.user_connections[user_id]:
                        if connection_id in self.connections:
                            await self.connections[connection_id].send_message(message)
        else:
            # Broadcast to all connections
            for connection in self.connections.values():
                await connection.send_message(message)
    
    async def broadcast_status_update(self, status_data: Dict[str, Any]):
        """Broadcast status update to all connections"""
        message = WebSocketMessage(
            message_id=str(uuid.uuid4()),
            message_type=WebSocketMessageType.STATUS_UPDATE,
            timestamp=datetime.now(),
            data=status_data
        )
        
        for connection in self.connections.values():
            await connection.send_message(message)
    
    async def broadcast_player_update(self, player_data: Dict[str, Any], target_users: List[str] = None):
        """Broadcast player update to interested users"""
        message = WebSocketMessage(
            message_id=str(uuid.uuid4()),
            message_type=WebSocketMessageType.PLAYER_UPDATE,
            timestamp=datetime.now(),
            data=player_data,
            target_users=target_users
        )
        
        if target_users:
            # Send to specific users
            for user_id in target_users:
                if user_id in self.user_connections:
                    for connection_id in self.user_connections[user_id]:
                        if connection_id in self.connections:
                            await self.connections[connection_id].send_message(message)
        else:
            # Broadcast to all connections
            for connection in self.connections.values():
                await connection.send_message(message)
    
    async def _handle_ping(self, connection: WebSocketConnection):
        """Handle ping message"""
        pong_message = WebSocketMessage(
            message_id=str(uuid.uuid4()),
            message_type=WebSocketMessageType.PONG,
            timestamp=datetime.now()
        )
        await connection.send_message(pong_message)
    
    async def _handle_pong(self, connection: WebSocketConnection):
        """Handle pong message"""
        connection.last_ping = datetime.now()
    
    async def _handle_subscribe(self, connection: WebSocketConnection, message_data: Dict[str, Any]):
        """Handle subscription request"""
        topic = message_data.get('topic')
        if topic:
            connection.subscribe(topic)
            if topic not in self.topic_subscribers:
                self.topic_subscribers[topic] = set()
            self.topic_subscribers[topic].add(connection.connection_id)
            print(f"📡 Connection {connection.connection_id} subscribed to {topic}")
    
    async def _handle_unsubscribe(self, connection: WebSocketConnection, message_data: Dict[str, Any]):
        """Handle unsubscription request"""
        topic = message_data.get('topic')
        if topic:
            connection.unsubscribe(topic)
            if topic in self.topic_subscribers:
                self.topic_subscribers[topic].discard(connection.connection_id)
            print(f"📡 Connection {connection.connection_id} unsubscribed from {topic}")
    
    async def _send_error(self, connection: WebSocketConnection, error_message: str):
        """Send error message to connection"""
        error_msg = WebSocketMessage(
            message_id=str(uuid.uuid4()),
            message_type=WebSocketMessageType.ERROR,
            timestamp=datetime.now(),
            data={"error": error_message}
        )
        await connection.send_message(error_msg)
    
    async def _heartbeat_loop(self):
        """Heartbeat loop to check connection health"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                current_time = datetime.now()
                dead_connections = []
                
                for connection_id, connection in self.connections.items():
                    # Check if connection is still alive
                    time_since_ping = (current_time - connection.last_ping).total_seconds()
                    
                    if time_since_ping > self.heartbeat_interval * 2:
                        # Connection is dead
                        dead_connections.append(connection_id)
                    else:
                        # Send ping
                        await connection.ping()
                
                # Remove dead connections
                for connection_id in dead_connections:
                    await self.remove_connection(connection_id)
                    
            except Exception as e:
                print(f"Error in heartbeat loop: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        return {
            'total_connections': len(self.connections),
            'total_users': len(self.user_connections),
            'total_topics': len(self.topic_subscribers),
            'connections_by_user': {user_id: len(conns) for user_id, conns in self.user_connections.items()},
            'topic_subscribers': {topic: len(subs) for topic, subs in self.topic_subscribers.items()}
        }

# Global WebSocket service instance
websocket_service = WebSocketService()

# Example usage and testing
if __name__ == "__main__":
    # Test WebSocket message
    message = WebSocketMessage(
        message_id="test_msg_123",
        message_type=WebSocketMessageType.NOTIFICATION,
        data={"player": "Haaland", "points": 4},
        user_id="test_user_123"
    )
    
    print("WebSocket message:")
    print(message.to_json())
    
    # Test connection stats
    stats = websocket_service.get_connection_stats()
    print("\nConnection stats:")
    print(json.dumps(stats, indent=2))
