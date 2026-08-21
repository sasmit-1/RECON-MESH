"""
RECON-MESH Step 10: WebSocket Streaming Manager
================================================
Provides bidirectional real-time event streaming to the React/Three.js frontend.
Broadcasts live telemetry ticks, cluster status updates, and Merkle root syncs.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("recon_mesh.websocket")


class ConnectionManager:
    """
    Asynchronous Connection Manager tracking active WebSocket connections
    and broadcasting telemetry ticks to connected clients.
    """

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts an incoming WebSocket connection and registers it."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes a disconnected WebSocket client."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total active: {len(self.active_connections)}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket) -> None:
        """Sends a JSON message to a single connected client."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as exc:
            logger.warning(f"Error sending message to client: {exc}")
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcasts a JSON payload to all active WebSocket clients."""
        if not self.active_connections:
            return

        payload_str = json.dumps(message)
        disconnected: List[WebSocket] = []

        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload_str)
            except Exception as exc:
                logger.warning(f"Error broadcasting to client: {exc}")
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


# Global singleton connection manager
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint handler listening on /ws/recon-stream.
    """
    await manager.connect(websocket)
    try:
        # Send initial handshake message
        await manager.send_personal_message(
            {
                "event": "HANDSHAKE",
                "status": "CONNECTED",
                "engine": "RECON-MESH Autonomous FinOps v2.1",
                "features": ["HeuristicPruner", "DPSolver", "MerkleAudit", "EpisodicMemoryStore"],
            },
            websocket,
        )

        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
                action = data.get("action", "").upper()

                if action == "PING":
                    await manager.send_personal_message({"event": "PONG", "timestamp": data.get("timestamp")}, websocket)
                elif action == "START_STREAM":
                    await manager.send_personal_message(
                        {"event": "STREAM_STATUS", "active": True, "frequency_hz": data.get("frequency_hz", 5)},
                        websocket,
                    )
                elif action == "STOP_STREAM":
                    await manager.send_personal_message(
                        {"event": "STREAM_STATUS", "active": False},
                        websocket,
                    )
                else:
                    await manager.send_personal_message(
                        {"event": "ACK", "received": action, "data": data},
                        websocket,
                    )
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {"event": "ERROR", "message": "Invalid JSON format"},
                    websocket,
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.error(f"Unexpected WebSocket error: {exc}")
        manager.disconnect(websocket)
