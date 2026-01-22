#!/usr/bin/env python3
"""
WebSocket Fallback for SSE

Provides WebSocket support as a fallback/alternative to Server-Sent Events
for more reliable real-time updates.
"""
import json
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime
from queue import Queue
from flask import request

from agents.utils.logger import get_logger

logger = get_logger("websocket")

# Try to import WebSocket support
try:
    from flask_socketio import SocketIO, emit, join_room, leave_room
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    SocketIO = None
    logger.warning("WebSocket support not available. Install: pip install flask-socketio")

# =============================================================================
# WEBSOCKET MANAGER
# =============================================================================

class WebSocketManager:
    """
    Manages WebSocket connections for real-time updates.
    
    Features:
    - Room-based messaging
    - Automatic reconnection handling
    - Fallback to SSE if WebSocket unavailable
    - Connection tracking
    """
    
    def __init__(self, socketio: Optional[SocketIO] = None):
        """
        Initialize WebSocket manager.
        
        Args:
            socketio: SocketIO instance (created if None and available)
        """
        self.socketio = socketio
        self.connected_clients: Dict[str, Dict] = {}
        self.rooms: Dict[str, List[str]] = {}  # room -> [client_ids]
        self.message_history: List[Dict] = []
        self.max_history = 100
        
        if WEBSOCKET_AVAILABLE and self.socketio is None:
            # Create SocketIO instance
            from flask import Flask
            app = Flask(__name__)
            self.socketio = SocketIO(app, cors_allowed_origins="*")
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up WebSocket event handlers."""
        if not self.socketio:
            return
        
        @self.socketio.on('connect')
        def on_connect(auth):
            """Handle client connection."""
            client_id = request.sid
            self.connected_clients[client_id] = {
                "connected_at": datetime.now().isoformat(),
                "rooms": [],
            }
            logger.info(f"WebSocket client connected: {client_id}")
            emit('connected', {"client_id": client_id, "message": "Connected to PokeAgent"})
        
        @self.socketio.on('disconnect')
        def on_disconnect():
            """Handle client disconnection."""
            client_id = request.sid
            if client_id in self.connected_clients:
                # Leave all rooms
                for room in self.connected_clients[client_id]["rooms"]:
                    self.leave_room(client_id, room)
                del self.connected_clients[client_id]
            logger.info(f"WebSocket client disconnected: {client_id}")
        
        @self.socketio.on('join_room')
        def on_join_room(data):
            """Handle client joining a room."""
            client_id = request.sid
            room = data.get('room', 'default')
            self.join_room(client_id, room)
        
        @self.socketio.on('leave_room')
        def on_leave_room(data):
            """Handle client leaving a room."""
            client_id = request.sid
            room = data.get('room', 'default')
            self.leave_room(client_id, room)
    
    def join_room(self, client_id: str, room: str):
        """Add client to a room."""
        if not self.socketio:
            return
        
        if room not in self.rooms:
            self.rooms[room] = []
        
        if client_id not in self.rooms[room]:
            self.rooms[room].append(client_id)
            join_room(room, sid=client_id)
            
            if client_id in self.connected_clients:
                self.connected_clients[client_id]["rooms"].append(room)
            
            logger.debug(f"Client {client_id} joined room {room}")
    
    def leave_room(self, client_id: str, room: str):
        """Remove client from a room."""
        if not self.socketio:
            return
        
        if room in self.rooms and client_id in self.rooms[room]:
            self.rooms[room].remove(client_id)
            leave_room(room, sid=client_id)
            
            if client_id in self.connected_clients:
                if room in self.connected_clients[client_id]["rooms"]:
                    self.connected_clients[client_id]["rooms"].remove(room)
            
            logger.debug(f"Client {client_id} left room {room}")
    
    def emit_to_room(self, room: str, event: str, data: Dict):
        """Emit event to all clients in a room."""
        if not self.socketio:
            return
        
        self.socketio.emit(event, data, room=room)
        logger.debug(f"Emitted {event} to room {room}", extra={"clients": len(self.rooms.get(room, []))})
    
    def emit_to_all(self, event: str, data: Dict):
        """Emit event to all connected clients."""
        if not self.socketio:
            return
        
        self.socketio.emit(event, data)
        
        # Store in history
        self.message_history.append({
            "event": event,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        })
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        
        logger.debug(f"Emitted {event} to all clients", extra={"clients": len(self.connected_clients)})
    
    def get_stats(self) -> Dict:
        """Get WebSocket connection statistics."""
        return {
            "available": WEBSOCKET_AVAILABLE,
            "connected_clients": len(self.connected_clients),
            "rooms": {room: len(clients) for room, clients in self.rooms.items()},
            "total_rooms": len(self.rooms),
            "message_history_count": len(self.message_history),
        }


# Global WebSocket manager
_ws_manager: Optional[WebSocketManager] = None

def get_websocket_manager() -> Optional[WebSocketManager]:
    """Get or create global WebSocket manager."""
    global _ws_manager
    if _ws_manager is None and WEBSOCKET_AVAILABLE:
        _ws_manager = WebSocketManager()
    return _ws_manager
