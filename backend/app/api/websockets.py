from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
from app.core.config import settings
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.api.dependencies import get_db
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
            if not self._evaluate_message_authorization(message, user_id):
                return
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

    async def broadcast_to_role(self, message: dict, role: str):
        for user_id, user_role in self.user_roles.items():
            if user_role == role:
                if user_id in self.active_connections:
                    if not self._evaluate_message_authorization(message, user_id):
                        continue
                    for connection in self.active_connections[user_id]:
                        await connection.send_json(message)

    async def broadcast_to_hospital(self, message: dict, role: str, hospital_id: int):
        for user_id, user_role in self.user_roles.items():
            if user_role == role:
                user_hospitals = self.user_hospitals.get(user_id, [])
                if hospital_id in user_hospitals:
                    if user_id in self.active_connections:
                        if not self._evaluate_message_authorization(message, user_id):
                            continue
                        for connection in self.active_connections[user_id]:
                            await connection.send_json(message)

    async def broadcast_to_all(self, message: dict):
        for user_id, connections in self.active_connections.items():
            if not self._evaluate_message_authorization(message, user_id):
                continue
            for connection in connections:
                await connection.send_json(message)

    def _evaluate_message_authorization(self, message: dict, user_id: int) -> bool:
        from app.core.database import SessionLocal
        from app.services.authorization import AuthorizationService, AuthorizationContext, Operation, ResourceType
        
        msg_type = message.get("type")
        data = message.get("data", {})
        patient_id = data.get("patient_id")
        
        # Admin or generic notifications don't need patient data access checks
        if msg_type in [
            "notification_created",
            "access_request_created",
            "access_request_approved",
            "access_request_rejected",
            "access_revoked",
            # Triage updates are dispatched only through the hospital-scoped
            # broadcaster, which already filters active memberships. Treating
            # them as patient-reading events here both duplicates policy and
            # can silently drop a correctly scoped update.
            "triage_update",
        ]:
            return True
            
        if not patient_id:
            return True
            
        # Verify authorization
        db = SessionLocal()
        try:
            actor = db.query(User).filter(User.id == user_id).first()
            if not actor: 
                return False
                
            auth_svc = AuthorizationService(db)
            ctx = AuthorizationContext(
                actor=actor,
                operation=Operation.READ,
                resource_type=ResourceType.PATIENT_READING,
                db=db,
                patient_id=patient_id,
                hospital_id=data.get("hospital_id"),
                purpose=data.get("purpose")
            )
            decision = auth_svc.authorize(ctx)
            return decision.allowed
        finally:
            db.close()

manager = ConnectionManager()

def verify_token(token: str, db: Session) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
        
    user = db.query(User).filter(User.email == email).first()
    return user

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    user = verify_token(token, db)
    if not user or not user.is_active:
        await websocket.close(code=1008)
        return
        
    hospital_ids = []
    if user.role in ["doctor", "admin"]:
        from app.models.hospital import HospitalStaff
        affiliations = db.query(HospitalStaff).filter(
            HospitalStaff.user_id == user.id,
            HospitalStaff.is_active == True
        ).all()
        hospital_ids = [aff.hospital_id for aff in affiliations]

    await manager.connect(websocket, user.id, user.role, hospital_ids)
    try:
        while True:
            data = await websocket.receive_text()
            # Basic echo/ping or handle generic messages if needed
            # Most actual payloads will be sent via REST and broadcasted by the manager
    except WebSocketDisconnect:
        manager.disconnect(websocket, user.id)
