"""WebSocket 라우터 - 작업 상태 실시간 알림"""

import asyncio
import logging
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger(__name__)

# 연결된 WebSocket 클라이언트 관리
# key: user_id, value: 해당 사용자의 WebSocket 연결 집합
active_connections: Dict[int, Set[WebSocket]] = {}


async def connect(websocket: WebSocket, user_id: int):
    """WebSocket 연결 수락 및 등록"""
    await websocket.accept()
    if user_id not in active_connections:
        active_connections[user_id] = set()
    active_connections[user_id].add(websocket)
    logger.info(f"WebSocket 연결: user_id={user_id}")


def disconnect(websocket: WebSocket, user_id: int):
    """WebSocket 연결 해제"""
    if user_id in active_connections:
        active_connections[user_id].discard(websocket)
        if not active_connections[user_id]:
            del active_connections[user_id]
    logger.info(f"WebSocket 해제: user_id={user_id}")


async def send_status_update(user_id: int, data: dict):
    """특정 사용자에게 상태 업데이트 전송

    다른 서비스에서 호출하여 실시간 알림 전송 가능:
        from app.routers.websocket import send_status_update
        await send_status_update(user_id, {"generation_id": 1, "status": "image_done"})
    """
    if user_id in active_connections:
        disconnected = set()
        for ws in active_connections[user_id]:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.add(ws)

        # 끊어진 연결 정리
        for ws in disconnected:
            active_connections[user_id].discard(ws)


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket 엔드포인트 - 작업 상태 실시간 수신

    프론트엔드에서의 사용법:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws/1');
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('상태 업데이트:', data);
        // { "generation_id": 1, "status": "image_done", "image_url": "..." }
    };
    ```
    """
    await connect(websocket, user_id)
    try:
        while True:
            # 클라이언트로부터의 메시지 대기 (연결 유지)
            data = await websocket.receive_text()
            # 클라이언트가 ping을 보낼 경우 pong 응답
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        disconnect(websocket, user_id)
