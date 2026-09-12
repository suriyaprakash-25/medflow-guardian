from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.api.dependencies import get_db
from app.models.user import User

router = APIRouter()

WS_AUTH_PROTOCOL = "medflow.jwt"


@dataclass(frozen=True)
class WebSocketPrincipal:
    user: User
    expires_at: datetime


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.user_roles: Dict[int, str] = {}
        self.user_hospitals: Dict[int, List[int]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        role: str,
        hospital_ids: Optional[List[int]] = None,
    ):
        # The JWT itself is an offered subprotocol but is never echoed back. Only
        # the fixed application protocol is selected in the handshake response.
        await websocket.accept(subprotocol=WS_AUTH_PROTOCOL)
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
                self.user_roles.pop(user_id, None)
                self.user_hospitals.pop(user_id, None)

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id not in self.active_connections:
            return
        if not self._evaluate_message_authorization(
            message, user_id, delivery_scope="personal"
        ):
            return
        for connection in list(self.active_connections[user_id]):
            await connection.send_json(message)

    async def broadcast_to_role(self, message: dict, role: str):
        for user_id, user_role in list(self.user_roles.items()):
            if user_role != role or user_id not in self.active_connections:
                continue
            if not self._evaluate_message_authorization(
                message,
                user_id,
                delivery_scope="role",
                expected_role=role,
            ):
                continue
            for connection in list(self.active_connections[user_id]):
                await connection.send_json(message)

    async def broadcast_to_hospital(self, message: dict, role: str, hospital_id: int):
        for user_id, user_role in list(self.user_roles.items()):
            if user_role != role or user_id not in self.active_connections:
                continue
            # Cached affiliations are only an optimization. The authorization
            # evaluator below re-checks live database membership before send.
            if hospital_id not in self.user_hospitals.get(user_id, []):
                continue
            if not self._evaluate_message_authorization(
                message,
                user_id,
                delivery_scope="hospital",
                expected_role=role,
                hospital_id=hospital_id,
            ):
                continue
            for connection in list(self.active_connections[user_id]):
                await connection.send_json(message)

    async def broadcast_to_all(self, message: dict):
        # There is no security-safe generic broadcast in the current domain.
        # Unknown/global event delivery is intentionally default-denied.
        for user_id, connections in list(self.active_connections.items()):
            if not self._evaluate_message_authorization(
                message, user_id, delivery_scope="all"
            ):
                continue
            for connection in list(connections):
                await connection.send_json(message)

    def _evaluate_message_authorization(
        self,
        message: dict,
        user_id: int,
        *,
        delivery_scope: str,
        expected_role: Optional[str] = None,
        hospital_id: Optional[int] = None,
    ) -> bool:
        """Authorize one outbound event using authoritative server-side state.

        Message payload identifiers are lookup keys only. They never become proof
        of ownership, membership, consent, or recipient identity. Unknown event
        types and incomplete event data are denied.
        """
        from app.core.database import SessionLocal
        from app.models.access import DocumentAccessRequest, DocumentAccessGrant
        from app.models.document import MedicalDocument
        from app.models.hospital import HospitalStaff, Visit
        from app.models.notification import Notification
        from app.models.monitoring import Message
        from app.models.triage import TriageRequest
        from app.services.authorization import (
            AuthorizationService,
            AuthorizationContext,
            Operation,
            ResourceType,
        )

        if delivery_scope not in {"personal", "role", "hospital", "all"}:
            return False

        msg_type = message.get("type")
        data = message.get("data")
        if not isinstance(msg_type, str) or not isinstance(data, dict):
            return False

        db = SessionLocal()
        try:
            actor = db.query(User).filter(User.id == user_id).first()
            if not actor or not actor.is_active:
                return False
            if expected_role is not None and actor.role != expected_role:
                return False

            if msg_type == "message" and delivery_scope == "personal":
                message_id = data.get("id")
                if not isinstance(message_id, int):
                    return False
                row = db.query(Message).filter(Message.id == message_id).first()
                return bool(row and row.receiver_id == user_id)

            if msg_type == "notification_created" and delivery_scope == "personal":
                notification_id = data.get("notification_id")
                if not isinstance(notification_id, int):
                    return False
                row = db.query(Notification).filter(Notification.id == notification_id).first()
                return bool(row and row.user_id == user_id)

            if msg_type == "document_uploaded" and delivery_scope == "personal":
                document_id = data.get("document_id")
                if not isinstance(document_id, int):
                    return False
                row = db.query(MedicalDocument).filter(MedicalDocument.id == document_id).first()
                return bool(row and row.patient_id == user_id)

            if msg_type in {
                "access_request_created",
                "access_request_approved",
                "access_request_rejected",
            } and delivery_scope == "personal":
                request_id = data.get("request_id")
                if not isinstance(request_id, int):
                    return False
                row = db.query(DocumentAccessRequest).filter(
                    DocumentAccessRequest.id == request_id
                ).first()
                if not row:
                    return False
                if msg_type == "access_request_created":
                    return row.patient_id == user_id
                return row.requesting_doctor_id == user_id

            if msg_type == "access_revoked" and delivery_scope == "personal":
                grant_id = data.get("grant_id")
                if not isinstance(grant_id, int):
                    return False
                row = db.query(DocumentAccessGrant).filter(
                    DocumentAccessGrant.id == grant_id
                ).first()
                return bool(row and row.doctor_id == user_id)

            if msg_type == "triage_update":
                triage_id = data.get("id")
                if not isinstance(triage_id, int):
                    return False
                triage = db.query(TriageRequest).filter(TriageRequest.id == triage_id).first()
                if not triage:
                    return False
                if delivery_scope == "personal":
                    return triage.patient_id == user_id
                if delivery_scope == "hospital":
                    if hospital_id is None or triage.hospital_id != hospital_id:
                        return False
                    membership = db.query(HospitalStaff).filter(
                        HospitalStaff.user_id == user_id,
                        HospitalStaff.hospital_id == hospital_id,
                        HospitalStaff.is_active == True,
                    ).first()
                    return bool(membership and actor.role == "doctor")
                return False

            if msg_type == "reading" and delivery_scope == "role":
                patient_id = data.get("patient_id")
                if actor.role != "doctor" or not isinstance(patient_id, int):
                    return False

                # Derive candidate organization context from authoritative visits
                # and active memberships rather than trusting a payload hospital_id.
                visits = db.query(Visit).filter(
                    Visit.patient_id == patient_id,
                    Visit.doctor_id == actor.id,
                ).all()
                for visit in visits:
                    membership = db.query(HospitalStaff).filter(
                        HospitalStaff.user_id == actor.id,
                        HospitalStaff.hospital_id == visit.hospital_id,
                        HospitalStaff.is_active == True,
                    ).first()
                    if not membership:
                        continue
                    decision = AuthorizationService(db).authorize(
                        AuthorizationContext(
                            actor=actor,
                            operation=Operation.LIST,
                            resource_type=ResourceType.PATIENT_READING,
                            db=db,
                            patient_id=patient_id,
                            hospital_id=visit.hospital_id,
                            purpose="TREATMENT",
                        )
                    )
                    if decision.allowed:
                        return True
                return False

            # No generic event type is safe by default, including events with no
            # patient_id. This closes the former missing-patient-id allow path.
            return False
        finally:
            db.close()


manager = ConnectionManager()


def _extract_subprotocol_token(websocket: WebSocket) -> Optional[str]:
    """Extract a bearer JWT from the WebSocket subprotocol offer.

    Browser WebSocket APIs cannot set Authorization headers. Supplying the JWT as
    a secondary Sec-WebSocket-Protocol value keeps it out of request URLs and
    common URL/access logs. The fixed `medflow.jwt` protocol is the only value the
    server echoes in the handshake response.
    """
    raw = websocket.headers.get("sec-websocket-protocol")
    if not raw:
        return None
    offered = [part.strip() for part in raw.split(",") if part.strip()]
    if len(offered) != 2 or offered[0] != WS_AUTH_PROTOCOL:
        return None
    return offered[1]


def verify_token(token: str, db: Session) -> Optional[WebSocketPrincipal]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        expires_at_raw = payload.get("exp")
        if not isinstance(email, str) or not isinstance(expires_at_raw, (int, float)):
            return None

        # Compose safely with the separate R1 token-stage remediation: once those
        # claims are present, a pre-auth token can never establish a WebSocket.
        token_type = payload.get("token_type")
        if token_type is not None and token_type != "access":
            return None
        if payload.get("mfa_verified") is False:
            return None

        expires_at = datetime.fromtimestamp(expires_at_raw, tz=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            return None
    except (JWTError, ValueError, TypeError, OverflowError):
        return None

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        return None
    return WebSocketPrincipal(user=user, expires_at=expires_at)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    token = _extract_subprotocol_token(websocket)
    principal = verify_token(token, db) if token else None
    if not principal:
        await websocket.close(code=1008)
        return

    user = principal.user
    hospital_ids: List[int] = []
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
            seconds_remaining = (
                principal.expires_at - datetime.now(timezone.utc)
            ).total_seconds()
            if seconds_remaining <= 0:
                await websocket.close(code=1008, reason="Access token expired")
                break
            try:
                # Even an idle socket is closed at the JWT expiration boundary.
                await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=seconds_remaining,
                )
            except asyncio.TimeoutError:
                await websocket.close(code=1008, reason="Access token expired")
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, user.id)
