"""SOUL 训练 WebSocket 连接管理器。

按 soul_kb_id 分组管理 WebSocket 连接, 训练事件实时推送到订阅了对应 SOUL 的所有客户端。

设计:
- 单例 SoulTrainingWSManager (模块级全局)
- subscribe(soul_kb_id, ws) → 客户端订阅某 SOUL 的训练事件
- broadcast(soul_kb_id, event) → 向该 SOUL 的所有订阅者推送事件
- broadcast_task_event(task_id, event) → 从 task_runner 的事件广播到对应 SOUL

集成点:
- soul_task_runner.append_event / update_progress → ws_manager.broadcast
- FastAPI WebSocket 端点 → ws_manager.subscribe
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class SoulTrainingWSManager:
    """WebSocket 连接管理器 — 按 soul_kb_id 分组广播训练事件。"""

    def __init__(self):
        # soul_kb_id → set of active WebSocket connections
        self._channels: dict[str, set[WebSocket]] = {}
        # task_id → soul_kb_id 映射 (训练任务提交时注册)
        self._task_soul_map: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def connect(self, soul_kb_id: str, websocket: WebSocket) -> None:
        """接受 WebSocket 连接并订阅到指定 SOUL 频道。"""
        await websocket.accept()
        async with self._lock:
            if soul_kb_id not in self._channels:
                self._channels[soul_kb_id] = set()
            self._channels[soul_kb_id].add(websocket)
        count = len(self._channels.get(soul_kb_id, set()))
        logger.info("WS connect: soul=%s, subscribers=%d", soul_kb_id, count)

    async def disconnect(self, soul_kb_id: str, websocket: WebSocket) -> None:
        """移除断开的 WebSocket 连接。"""
        async with self._lock:
            conns = self._channels.get(soul_kb_id)
            if conns:
                conns.discard(websocket)
                if not conns:
                    del self._channels[soul_kb_id]
        count = len(self._channels.get(soul_kb_id, set()))
        logger.info("WS disconnect: soul=%s, remaining=%d", soul_kb_id, count)

    def register_task(self, task_id: str, soul_kb_id: str) -> None:
        """注册 task_id → soul_kb_id 映射(训练提交时调用)。"""
        self._task_soul_map[task_id] = soul_kb_id

    def unregister_task(self, task_id: str) -> None:
        """任务结束后移除映射。"""
        self._task_soul_map.pop(task_id, None)

    async def broadcast(self, soul_kb_id: str, event: dict[str, Any]) -> None:
        """向订阅了指定 SOUL 的所有 WebSocket 客户端推送事件。

        事件结构: {type, ts, soul_kb_id, ...payload}
        type: progress | event | status | done | error
        """
        conns = self._channels.get(soul_kb_id)
        if not conns:
            return

        message = json.dumps(event, ensure_ascii=False, default=str)

        # 并行发送, 断开的连接自动清理
        stale: list[WebSocket] = []
        tasks = []
        for ws in list(conns):
            try:
                tasks.append(self._safe_send(ws, message, stale))
            except Exception:
                stale.append(ws)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # 清理断开的连接
        if stale:
            async with self._lock:
                for ws in stale:
                    conns.discard(ws)
                if not conns:
                    self._channels.pop(soul_kb_id, None)

    async def _safe_send(self, ws: WebSocket, message: str,
                         stale: list[WebSocket]) -> None:
        """安全发送消息, 失败时标记为 stale。"""
        try:
            await ws.send_text(message)
        except Exception:
            stale.append(ws)

    async def broadcast_task_event(self, task_id: str,
                                    event_type: str,
                                    data: dict[str, Any]) -> None:
        """从 task_runner 的事件广播到对应 SOUL 的所有订阅者。

        自动从 _task_soul_map 解析 soul_kb_id。
        event_type: progress | event | status | done | error
        """
        soul_kb_id = self._task_soul_map.get(task_id)
        if not soul_kb_id:
            return  # 无订阅者或未注册

        payload = {
            "type": event_type,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "soul_kb_id": soul_kb_id,
            "task_id": task_id,
            **data,
        }
        await self.broadcast(soul_kb_id, payload)

    def subscriber_count(self, soul_kb_id: str) -> int:
        """返回某 SOUL 的当前订阅者数量。"""
        return len(self._channels.get(soul_kb_id, set()))


# 模块级单例
ws_manager = SoulTrainingWSManager()
