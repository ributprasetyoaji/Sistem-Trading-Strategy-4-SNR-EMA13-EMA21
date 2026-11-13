"""IPC: atomic signal/status files for MT5 + optional localhost TCP broadcast.

Preferred default is the atomic-file protocol (tmp file + os.replace) because
it survives VPS restarts, does not require a listening daemon, and MT5 reads
it with shared access. TCP mode is available for lower latency.
"""
from __future__ import annotations

import asyncio
import json
import os

from signal_protocol import atomic_write_json


class IPC:
    def __init__(self, cfg, logger=None):
        self.cfg = cfg
        self.log = logger
        self.mode = (cfg.ipc_mode or "file").lower()
        self.dir = cfg.resolve_ipc_dir()
        os.makedirs(self.dir, exist_ok=True)
        self._clients: set = set()
        self._server: asyncio.AbstractServer | None = None
        self.signals_sent = 0

    # ---- TCP ------------------------------------------------------------
    async def start_tcp(self) -> None:
        if self.mode not in ("tcp", "both"):
            return
        self._server = await asyncio.start_server(
            self._on_client, self.cfg.ipc_tcp_host, self.cfg.ipc_tcp_port)
        if self.log:
            self.log.log("DATA", "IPC_TCP_LISTENING",
                         host=self.cfg.ipc_tcp_host, port=self.cfg.ipc_tcp_port)

    async def _on_client(self, reader: asyncio.StreamReader,
                         writer: asyncio.StreamWriter) -> None:
        self._clients.add(writer)
        try:
            while True:
                await reader.read(4096)   # keep alive; MT5/python consumers just listen
        except (ConnectionError, asyncio.IncompleteReadError, OSError):
            pass
        finally:
            self._clients.discard(writer)
            try:
                writer.close()
            except Exception:
                pass

    def _broadcast(self, payload: dict) -> None:
        if not self._clients:
            return
        try:
            data = (json.dumps(payload, separators=(",", ":")) + "\n").encode()
        except (TypeError, ValueError):
            return
        for w in list(self._clients):
            try:
                w.write(data)
            except (ConnectionError, OSError):
                self._clients.discard(w)

    # ---- publish --------------------------------------------------------
    def publish_signal(self, payload: dict) -> None:
        if self.mode in ("file", "both"):
            atomic_write_json(self.cfg.signal_path(), payload)
        if self.mode in ("tcp", "both"):
            self._broadcast({"channel": "signal", **payload})
        self.signals_sent += 1
        if self.log:
            self.log.log("SIGNAL", "IPC_SIGNAL_PUBLISHED",
                         signal_id=payload.get("signal_id"),
                         direction=payload.get("direction"),
                         score=payload.get("score"))

    def publish_status(self, payload: dict) -> None:
        if self.mode in ("file", "both"):
            atomic_write_json(self.cfg.status_path(), payload)
        if self.mode in ("tcp", "both"):
            self._broadcast({"channel": "status", **payload})

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        for w in list(self._clients):
            try:
                w.close()
            except Exception:
                pass
