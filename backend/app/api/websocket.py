"""
TRIDENT Step 10: WebSocket Streaming Manager
================================================
Provides bidirectional real-time event streaming to the React/Three.js frontend.
Broadcasts live CLUSTER_MATCHED, METRICS_UPDATE, and STREAM_TICK payloads.

START_STREAM → asyncio.create_task consuming stream_synthetic_events()
            → normalize → match → broadcast CLUSTER_MATCHED events
STOP_STREAM  → cancel active background task cleanly
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("trident.websocket")


class ConnectionManager:
    """
    Asynchronous Connection Manager tracking active WebSocket connections
    and broadcasting telemetry payloads to all connected clients.
    """

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts an incoming WebSocket connection and registers it."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket client connected. Total active: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes a disconnected WebSocket client."""
        self.active_connections.discard(websocket)
        logger.info("WebSocket client disconnected. Total active: %d", len(self.active_connections))

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket) -> None:
        """Sends a JSON message to a single connected client."""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as exc:
            logger.warning("Error sending message to client: %s", exc)
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcasts a JSON payload to all active WebSocket clients."""
        if not self.active_connections:
            return

        payload_str = json.dumps(message, default=str)
        disconnected: List[WebSocket] = []

        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload_str)
            except Exception as exc:
                logger.warning("Error broadcasting to client: %s", exc)
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


# Global singleton connection manager
manager = ConnectionManager()

# Active streaming task registry (per WebSocket connection)
_active_stream_tasks: Dict[int, asyncio.Task] = {}


# ---------------------------------------------------------------------------
# Streaming background task
# ---------------------------------------------------------------------------

async def _stream_pipeline_task(
    rate_hz: float,
    count: int,
    seed: int,
    websocket: WebSocket,
) -> None:
    """
    Background coroutine: consumes stream_synthetic_events(), normalizes each event,
    runs it through the matcher pipeline, and broadcasts CLUSTER_MATCHED payloads.
    """
    from backend.app.benchmark.generator import stream_synthetic_events
    from backend.app.core.matcher.engine_factory import get_matcher_engine
    from backend.app.core.normalizer import normalize_event
    from backend.app.core.models import SourceType, MatchStatus

    matcher = get_matcher_engine()

    # Accumulate stream buffers for mini-batch matching every N events
    rzp_buf: list = []
    bank_buf: list = []
    erp_buf: list = []
    streamed = 0
    matched_clusters = 0

    source_map = {
        "RAZORPAY": SourceType.RAZORPAY,
        "BANK": SourceType.BANK,
        "ERP": SourceType.ERP,
    }

    try:
        async for event_item in stream_synthetic_events(rate_hz=rate_hz, count=count, seed=seed):
            src_str = event_item.get("source_type", "RAZORPAY")
            src_type = source_map.get(src_str, SourceType.RAZORPAY)
            canonical = normalize_event(event_item["payload"], src_type)

            if src_type == SourceType.RAZORPAY:
                rzp_buf.append(canonical)
            elif src_type == SourceType.BANK:
                bank_buf.append(canonical)
            elif src_type == SourceType.ERP:
                erp_buf.append(canonical)

            streamed += 1

            # Broadcast raw STREAM_TICK for UI progress indication
            await manager.broadcast({
                "event": "STREAM_TICK",
                "source": src_str,
                "txn_id": canonical.original_id,
                "amount_paise": canonical.amount_gross_paise,
                "timestamp": event_item.get("timestamp"),
                "streamed_count": streamed,
            })

            # Mini-batch matching as events stream in
            if len(bank_buf) >= 2 and len(rzp_buf) >= 2:
                try:
                    clusters, orphan_rzp, orphan_bank = matcher.prune(
                        list(rzp_buf), list(bank_buf), list(erp_buf)
                    )
                    matched_clusters += len(clusters)

                    for cl in clusters:
                        cl_dict = cl.model_dump() if hasattr(cl, "model_dump") else cl.dict()
                        await manager.broadcast({
                            "event": "CLUSTER_MATCHED",
                            "cluster": cl_dict,
                            "matched_clusters_total": matched_clusters,
                        })

                    # Broadcast aggregated metrics update
                    variance_paise = sum(abs(c.discrepancy_paise) for c in clusters)
                    await manager.broadcast({
                        "event": "METRICS_UPDATE",
                        "resolved_clusters": matched_clusters,
                        "orphan_rzp": len(orphan_rzp),
                        "orphan_bank": len(orphan_bank),
                        "discrepancy_variance_paise": variance_paise,
                        "latency_ms": round(time.perf_counter() * 1000 % 1000, 1),
                    })

                    # Clear matched entries from buffers
                    used_rzp = {t.id for cl in clusters for t in cl.razorpay_txns}
                    used_bank = {t.id for cl in clusters for t in cl.bank_txns}
                    rzp_buf = [r for r in rzp_buf if r.id not in used_rzp]
                    bank_buf = [b for b in bank_buf if b.id not in used_bank]

                except Exception as exc:
                    logger.warning("Mini-batch match error: %s", exc)

        # Final flush of remaining buffer through Pass 1, Pass 2, and Pass 3
        if bank_buf or rzp_buf:
            try:
                from backend.app.core.matcher.dp_solver import BoundedDPSolver
                from backend.app.api.routes import _run_pass3_agent
                from backend.app.guardrails.merkle_audit import MerkleAuditLedger

                stream_ledger = MerkleAuditLedger()
                p1_clusters, orphan_rzp, orphan_bank = matcher.prune(rzp_buf, bank_buf, erp_buf)
                matched_clusters += len(p1_clusters)
                for cl in p1_clusters:
                    cl_dict = cl.model_dump() if hasattr(cl, "model_dump") else cl.dict()
                    await manager.broadcast({"event": "CLUSTER_MATCHED", "cluster": cl_dict})

                if orphan_bank:
                    dp_solver = BoundedDPSolver()
                    p2_clusters, f_orphan_rzp, f_orphan_bank = dp_solver.match_residual_orphans(
                        orphan_rzp, orphan_bank, erp_buf
                    )
                    matched_clusters += len(p2_clusters)
                    for cl in p2_clusters:
                        cl_dict = cl.model_dump() if hasattr(cl, "model_dump") else cl.dict()
                        await manager.broadcast({"event": "CLUSTER_MATCHED", "cluster": cl_dict})

                    if f_orphan_bank:
                        p3_clusters = await _run_pass3_agent(f_orphan_rzp, f_orphan_bank, p1_clusters + p2_clusters, stream_ledger)
                        matched_clusters += len(p3_clusters)
                        for cl in p3_clusters:
                            cl_dict = cl.model_dump() if hasattr(cl, "model_dump") else cl.dict()
                            await manager.broadcast({"event": "CLUSTER_MATCHED", "cluster": cl_dict})
            except Exception as exc:
                logger.warning("Stream final flush match error: %s", exc)

        await manager.broadcast({
            "event": "STREAM_COMPLETE",
            "total_streamed": streamed,
            "total_matched_clusters": matched_clusters,
        })

    except asyncio.CancelledError:
        logger.info("Stream task cancelled cleanly.")
        await manager.broadcast({"event": "STREAM_STATUS", "active": False, "reason": "cancelled"})
    except Exception as exc:
        logger.error("Stream pipeline error: %s", exc)
        await manager.broadcast({"event": "STREAM_ERROR", "message": str(exc)})


# ---------------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------------

async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint handler on /ws/recon-stream.
    Handles PING, START_STREAM, STOP_STREAM, and generic ACK.
    """
    await manager.connect(websocket)
    ws_id = id(websocket)

    try:
        # Handshake
        await manager.send_personal_message(
            {
                "event": "HANDSHAKE",
                "status": "CONNECTED",
                "engine": "TRIDENT Autonomous FinOps v2.1",
                "features": [
                    "HeuristicPruner",
                    "DPSolver",
                    "Pass3AIAgent",
                    "EpisodicMemoryStore",
                    "MerkleAudit",
                    "LiveStreaming",
                ],
            },
            websocket,
        )

        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
                action = data.get("action", "").upper()

                if action == "PING":
                    await manager.send_personal_message(
                        {"event": "PONG", "timestamp": data.get("timestamp")},
                        websocket,
                    )

                elif action == "START_STREAM":
                    # Cancel any existing stream task for this connection
                    if ws_id in _active_stream_tasks:
                        _active_stream_tasks[ws_id].cancel()

                    rate_hz = float(data.get("frequency_hz", 5))
                    count = int(data.get("count", 100))
                    seed = int(data.get("seed", 42))

                    task = asyncio.create_task(
                        _stream_pipeline_task(rate_hz, count, seed, websocket),
                        name=f"stream_{ws_id}",
                    )
                    _active_stream_tasks[ws_id] = task

                    await manager.send_personal_message(
                        {
                            "event": "STREAM_STATUS",
                            "active": True,
                            "frequency_hz": rate_hz,
                            "count": count,
                        },
                        websocket,
                    )
                    logger.info("Stream task started for ws=%d at %.1f Hz, count=%d", ws_id, rate_hz, count)

                elif action == "STOP_STREAM":
                    task = _active_stream_tasks.pop(ws_id, None)
                    if task and not task.done():
                        task.cancel()
                        logger.info("Stream task cancelled for ws=%d", ws_id)
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
        # Clean up streaming task on disconnect
        task = _active_stream_tasks.pop(ws_id, None)
        if task and not task.done():
            task.cancel()
        manager.disconnect(websocket)
    except Exception as exc:
        logger.error("Unexpected WebSocket error: %s", exc)
        task = _active_stream_tasks.pop(ws_id, None)
        if task and not task.done():
            task.cancel()
        manager.disconnect(websocket)
