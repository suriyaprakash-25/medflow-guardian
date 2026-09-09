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
        # Track roles and hospitals for broadcasting
        self.user_roles: Dict[int, str] = {}
        self.user_hospitals: Dict[int, List[int]] = {}

    async def connect(self, websocket: WebSocket, user_id: int, role: str, hospital_ids: List[int] = None):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        self.user_roles[user_id] = role
        if hospital_ids is not None:
            self.user_hospitals[user_id] = hospital_ids

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                if user_id in self.user_roles:
                    del self.user_roles[user_id]
                if user_id in self.user_hospitals:
                    del self.user_hospitals[user_id]

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

    async def broadcast_to_hospital(self, message: dict, role: str, hospital_id: int):
        for user_id, user_role in self.user_roles.items():
            if user_role == role:
                user_hospitals = self.user_hospitals.get(user_id, [])
                if hospital_id in user_hospitals:
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
        
    db = SessionLocal()
    hospital_ids = []
    if user.role in ["doctor", "admin"]:
        from app.models.hospital import HospitalStaff
        affiliations = db.query(HospitalStaff).filter(
            HospitalStaff.user_id == user.id,
            HospitalStaff.is_active == True
        ).all()
        hospital_ids = [aff.hospital_id for aff in affiliations]
    db.close()

    await manager.connect(websocket, user.id, user.role, hospital_ids)
    try:
        while True:
            data = await websocket.receive_text()
            # Basic echo/ping or handle generic messages if needed
            # Most actual payloads will be sent via REST and broadcasted by the manager
    except WebSocketDisconnect:
        manager.disconnect(websocket, user.id)
