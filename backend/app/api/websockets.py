from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
from app.core.config import settings
from jose import jwt, JWTError
from app.core.database import SessionLocal
from app.models.user import User

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Maps user_id -> List[WebSocket]
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Track roles for broadcasting
        self.user_roles: Dict[int, str] = {}

    async def connect(self, websocket: WebSocket, user_id: int, role: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        self.user_roles[user_id] = role

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                if user_id in self.user_roles:
                    del self.user_roles[user_id]

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

    async def broadcast_to_role(self, message: dict, role: str):
        for user_id, user_role in self.user_roles.items():
            if user_role == role:
                if user_id in self.active_connections:
                    for connection in self.active_connections[user_id]:
                        await connection.send_json(message)

    async def broadcast_to_all(self, message: dict):
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                await connection.send_json(message)

manager = ConnectionManager()

def verify_token(token: str) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
        
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    db.close()
    return user

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    user = verify_token(token)
    if not user:
        await websocket.close(code=1008)
        return
        
    await manager.connect(websocket, user.id, user.role)
    try:
        while True:
            data = await websocket.receive_text()
            # Basic echo/ping or handle generic messages if needed
            # Most actual payloads will be sent via REST and broadcasted by the manager
    except WebSocketDisconnect:
        manager.disconnect(websocket, user.id)
