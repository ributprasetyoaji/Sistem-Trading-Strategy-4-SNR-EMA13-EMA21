"""Binance websocket: combined aggTrade + diff-depth + kline_5m streams.

- automatic reconnect with capped exponential backoff
- host rotation: if one endpoint is blocked/timing out, the next is tried,
  and a known-good host is preferred on later reconnects
- order-book snapshot + diff synchronization with update-id validation
- snapshot SUPERVISOR: keeps retrying the REST snapshot every ~2s until the
  book is synced, so a single failed snapshot can never wedge the book
- automatic resync after gaps, stale detection, malformed message handling
"""
from __future__ import annotations

import asyncio
import json
import urllib.request

try:
    import websockets
except ImportError:      # replay/tests do not need the network stack
    websockets = None

from binance_orderbook import LocalOrderBook


class BinanceWS:
    def __init__(self, cfg, health, on_trade=None, on_kline=None, logger=None):
        self.cfg = cfg
        self.health = health
        self.on_trade = on_trade          # cb(ts_ms, price, qty, is_sell)
        self.on_kline = on_kline          # cb(kline_dict)
        self.log = logger
        self.book = LocalOrderBook(levels=cfg.depth_levels)
        self._snap_task: asyncio.Task | None = None
        self.rest_host = cfg.binance_rest_hosts[0]
        self.ws_host = cfg.binance_ws_hosts[0]
        self.good_host = ""               # last host that connected OK

    # ---- REST snapshot (fail-fast, known-good host first) ----------------
    def _fetch_snapshot(self) -> dict:
        hosts = list(self.cfg.binance_rest_hosts)
        if self.rest_host in hosts:          # try the last host that worked first
            hosts.remove(self.rest_host)
            hosts.insert(0, self.rest_host)
        last_err: Exception | None = None
        for host in hosts:
            url = (f"{host}/api/v3/depth"
                   f"?symbol={self.cfg.binance_symbol.upper()}"
                   f"&limit={self.cfg.snapshot_depth_limit}")
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "btc-hvn-ea/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                if host != self.rest_host:
                    self.rest_host = host
                    if self.log:
                        self.log.log("DATA", "REST_HOST_SWITCHED", host=host)
                return data
            except Exception as exc:      # noqa: BLE001 - try next host
                last_err = exc
        raise last_err if last_err else RuntimeError("no REST host configured")

    # ---- message routing --------------------------------------------------
    def handle_message(self, data: dict) -> None:
        etype = data.get("e")
        now_ms = int(data.get("E") or data.get("T") or 0)
        if etype == "aggTrade":
            try:
                ts = int(data["T"])
                price = float(data["p"])
                qty = float(data["q"])
                is_sell = bool(data["m"])       # buyer is maker => aggressor sells
            except (KeyError, TypeError, ValueError):
                self.health.mark_malformed()
                return
            self.health.mark_trade(ts)
            if self.on_trade:
                self.on_trade(ts, price, qty, is_sell)

        elif etype == "depthUpdate":
            try:
                U = int(data["U"]); u = int(data["u"]); pu = int(data.get("pu") or 0)
                b = data["b"]; a = data["a"]
            except (KeyError, TypeError, ValueError):
                self.health.mark_malformed()
                return
            self.health.mark_depth(now_ms or int(asyncio.get_event_loop().time() * 1000))
            status = self.book.apply_diff(U, u, pu, b, a)
            if status == "gap":
                self.health.mark_resync()
                if self.log:
                    self.log.log("DATA", "ORDERBOOK_GAP_RESYNC", last_u=self.book.last_update_id)
                self.book.start_resync()

        elif etype == "kline":
            k = data.get("k")
            if k:
                self.health.mark_kline(int(k.get("T") or now_ms))
                if self.on_kline:
                    self.on_kline(k)
        # other streams are ignored

    async def _resync(self) -> None:
        try:
            snap = await asyncio.to_thread(self._fetch_snapshot)
            ok = self.book.apply_snapshot(
                snap["lastUpdateId"], snap.get("bids", []), snap.get("asks", []))
            if not ok:
                self.health.mark_resync()
                if self.log:
                    self.log.log("DATA", "ORDERBOOK_RESYNC_FAILED")
            else:
                self.health.book_synced = True
                if self.log:
                    self.log.log("DATA", "ORDERBOOK_SYNCED", last_update_id=snap["lastUpdateId"])
        except Exception as exc:      # noqa: BLE001 - supervisor will retry
            self.health.last_error = f"snapshot: {exc}"
            if self.log:
                self.log.log("DATA", "ORDERBOOK_SNAPSHOT_RETRY", err=str(exc)[:120])

    async def _supervise(self) -> None:
        """Keeps the order book alive: as long as we are connected and the
        book is not synced, (re)fetch a snapshot every couple of seconds."""
        loop = asyncio.get_running_loop()
        while True:
            if self.health.connected and self.book.needs_snapshot():
                if self._snap_task is None or self._snap_task.done():
                    self._snap_task = loop.create_task(self._resync())
            await asyncio.sleep(2.0)

    # ---- main loop ---------------------------------------------------------
    async def run(self, stop_event: asyncio.Event) -> None:
        if websockets is None:
            raise RuntimeError("package 'websockets' is required for live mode")
        sym = self.cfg.binance_symbol.lower()
        backoff = self.cfg.reconnect_delay_ms / 1000.0
        max_backoff = self.cfg.reconnect_delay_max_ms / 1000.0
        host_idx = 0
        supervisor = asyncio.get_running_loop().create_task(self._supervise())

        try:
            while not stop_event.is_set():
                # try the last known-good host first, then rotate through the rest
                hosts = list(self.cfg.binance_ws_hosts)
                if self.good_host and self.good_host in hosts:
                    hosts.remove(self.good_host)
                    hosts.insert(0, self.good_host)
                self.ws_host = hosts[host_idx % len(hosts)]
                host_idx += 1
                # defensif: config lama/override JSON tanpa field ini tidak boleh crash
                ctx_stream = getattr(self.cfg, "context_stream", "kline_15m")
                url = (f"{self.ws_host}?streams="
                       f"{sym}@aggTrade/{sym}@depth@{self.cfg.depth_speed}/"
                       f"{sym}@{ctx_stream}")
                try:
                    async with websockets.connect(url, ping_interval=20, ping_timeout=20,
                                                  max_queue=4096,
                                                  open_timeout=8) as ws:
                        self.good_host = self.ws_host
                        backoff = self.cfg.reconnect_delay_ms / 1000.0
                        self.health.mark_connected(int(asyncio.get_event_loop().time() * 1000))
                        if self.log:
                            self.log.log("DATA", "BINANCE_CONNECTED", host=self.ws_host)
                        self.book.start_resync()
                        async for raw in ws:
                            if stop_event.is_set():
                                break
                            try:
                                msg = json.loads(raw)
                            except json.JSONDecodeError:
                                self.health.mark_malformed()
                                continue
                            data = msg.get("data", msg)
                            self.handle_message(data)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:      # noqa: BLE001 - reconnect on any failure
                    self.health.mark_disconnected(str(exc)[:160])
                    self.book.start_resync()
                    if self.log:
                        self.log.log("DATA", "BINANCE_RECONNECT",
                                     host=self.ws_host,
                                     backoff_ms=int(backoff * 1000),
                                     err=str(exc)[:120])
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 1.7, max_backoff)
                finally:
                    self.health.connected = False
        finally:
            supervisor.cancel()
            try:
                await supervisor
            except (asyncio.CancelledError, Exception):
                pass
