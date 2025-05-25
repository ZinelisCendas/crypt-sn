from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Sequence, cast

import aiohttp
import base58
import websockets
from prometheus_client import Gauge, Histogram, start_http_server
from solana.keypair import Keypair
from solana.rpc.api import Client
from solana.transaction import Transaction

from config import (
    GLOBAL_DD_PCT,
    PRUNE_INTERVAL_H,
    PRIV_KEY,
    RPC_URL,
    JITO_RPC,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
    SOL_MINT,
)
from exec import JupiterExec, add_priority_fee
from mev import send_bundle
from safety import SafetyChecker, SolscanAPI
from sizing import kelly_size, pyth_atr, pyth_price
from wallet import GmgnAPI


@dataclass(slots=True)
class Position:
    token: str
    qty: float
    entry: float
    value: float
    sl: float
    tp: float
    src: str
    limit_id: str | None = None


class PositionBook:
    def __init__(self, init_nav: float = 100):
        self.init = init_nav
        self.pos: Dict[str, Position] = {}
        self.mark: Dict[str, float] = {}
        self.peak = init_nav

    def update(self, token: str, qty: float, price: float, side: str = "buy"):
        """Record executed trade and update mark price."""
        self.mark[token] = price
        pos = self.pos.get(token)
        if side == "buy":
            if pos:
                new_qty = pos.qty + qty
                pos.entry = (pos.entry * pos.qty + price * qty) / new_qty
                pos.qty = new_qty
                pos.value += qty * price
            else:
                self.pos[token] = Position(
                    token,
                    qty,
                    price,
                    qty * price,
                    price * (1 - STOP_LOSS_PCT / 100),
                    price * (1 + TAKE_PROFIT_PCT / 100),
                    "copy",
                )
        else:
            if pos:
                pos.qty -= qty
                pos.value -= qty * price
                if pos.qty <= 0:
                    del self.pos[token]

    def nav(self) -> float:
        free = self.init - sum(p.value for p in self.pos.values())
        pos_val = sum(self.mark.get(t, p.entry) * p.qty for t, p in self.pos.items())
        return free + pos_val

    def update_peak(self, nav: float):
        self.peak = max(self.peak, nav)

    def global_dd(self, nav: float) -> float:
        return 100 * (1 - nav / self.peak)


class Notifier:
    def __init__(self):
        from config import TELE_CHAT, TELE_TOKEN  # local import to avoid cycle

        self.tg_enabled = bool(TELE_TOKEN and TELE_CHAT)
        if self.tg_enabled:
            self.api = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
            self.chat = TELE_CHAT

    async def send(self, msg: str):
        if not self.tg_enabled:
            return
        try:
            await aiohttp.ClientSession().post(
                self.api,
                json={"chat_id": self.chat, "text": msg},
                timeout=aiohttp.ClientTimeout(total=10),
            )
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).warning("Notifier error: %s", exc)


NAV_G = Gauge("bot_nav_sol", "Current NAV in SOL")
PNL_G = Gauge("bot_pnl_pct", "PnL % from start")
SLIPPAGE_G = Histogram("slippage_bps", "Slippage per trade")
INCLUSION_G = Histogram("inclusion_ms", "ms from send to confirm")


class CopyEngine:
    def __init__(self, seed_addrs: Sequence[str]):
        self.addrs = set(seed_addrs)
        self.notif = Notifier()
        self.gmgn = GmgnAPI(self.notif)
        self.sol = SolscanAPI(self.notif)
        self.exec = JupiterExec(self.notif)
        self.pb = PositionBook(100)
        self.safe = SafetyChecker(self.sol, self.notif)
        self.closed: Dict[str, float] = {}
        self.start_nav = self.pb.init

    async def _size(self, token: str, sharpe: float, nav: float) -> float:
        vol = await pyth_atr(token, notif=self.notif) or 0.05
        stake = kelly_size(nav, sharpe, vol, 30)
        nav_vol_target = 0.10
        portfolio_est_vol = vol or 0.05
        stake = stake * (nav_vol_target / portfolio_est_vol)
        return stake

    async def _execute_buy(self, ev: dict):
        token = ev["token"]
        price = float(ev["price"])
        nav = self.pb.nav()
        pos = self.pb.pos.get(token)
        if pos and self.pb.mark.get(token, pos.entry) * pos.qty >= 0.3 * nav:
            return
        stake = await self._size(token, 1.5, nav)  # assume sharpe proxy
        amt = int(stake / price)
        quote = await self.exec.quote(token, token, amt)  # placeholder self swap
        tx_b64 = await self.exec.swap_tx(quote["data"][0])

        tx_bytes = base64.b64decode(tx_b64)
        tx_bytes = await add_priority_fee(tx_bytes)
        kp = Keypair.from_secret_key(base58.b58decode(PRIV_KEY))
        tx = Transaction.deserialize(tx_bytes)
        tx.sign(kp)
        client = Client(RPC_URL)
        try:
            start_t = time.time()
            if JITO_RPC:
                ok = await send_bundle(base64.b64encode(tx.serialize()).decode())
                if ok:
                    sig = "bundle"
                else:
                    resp = cast(
                        dict[str, Any], client.send_raw_transaction(tx.serialize())
                    )
                    sig = resp.get("result", "raw")
            else:
                resp = cast(dict[str, Any], client.send_raw_transaction(tx.serialize()))
                sig = resp["result"]
            INCLUSION_G.observe((time.time() - start_t) * 1000)
            logging.getLogger(__name__).info("tx %s sent", sig)
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).warning("tx failure: %s", exc)

        SLIPPAGE_G.observe(0.0)
        await self.notif.send(f"BUY {amt} {token[:4]}… @ {price:.6f} SOL")
        self.pb.update(token, amt, price, "buy")
        pos = self.pb.pos.get(token)
        if pos:
            limit_price = pos.entry * (1 + TAKE_PROFIT_PCT / 100)
            res = await self.exec.create_limit(token, SOL_MINT, amt, limit_price)
            pos.limit_id = res.get("limitOrderId")
        nav = self.pb.nav()
        NAV_G.set(nav)
        PNL_G.set((nav - self.pb.init) / self.pb.init * 100)
        self.pb.update_peak(nav)
        dd = self.pb.global_dd(nav)
        if dd >= GLOBAL_DD_PCT:
            await self.notif.send(
                f"GLOBAL DD {dd:.1f}% exceeds {GLOBAL_DD_PCT}% – shutting down"
            )
            Path("flag_down").write_text(f"{nav:.4f}")
            await asyncio.sleep(86400)
            raise SystemExit("drawdown limit hit")

    async def _wallet_stream(self):
        backoff = 1
        while True:
            try:
                async with websockets.connect("wss://ws.gmgn.ai/v1") as ws:
                    backoff = 1
                    async for msg in ws:
                        ev = json.loads(msg)
                        if ev.get("address") in self.addrs and ev.get("side") == "buy":
                            token = ev.get("token")
                            if not token:
                                continue
                            if await self.safe.is_safe(token):
                                await self._execute_buy(ev)
            except Exception as exc:  # noqa: BLE001
                logging.getLogger(__name__).warning(
                    "WS reconnect in %s sec due to %s", backoff, exc
                )
                try:
                    await self.notif.send(f"WS disconnect: {exc}")
                except Exception:  # noqa: BLE001
                    pass
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def _mark_positions(self):
        while True:
            now = time.time()
            for token, pos in list(self.pb.pos.items()):
                price = await pyth_price(token, notif=self.notif)
                if not price:
                    continue
                self.pb.mark[token] = price
                if price <= pos.sl:
                    pnl = price * pos.qty - pos.value
                    self.pb.init += pnl
                    self.pb.pos.pop(token, None)
                    self.pb.mark.pop(token, None)
                    self.closed[token] = now
                    await self.notif.send(
                        f"SELL {int(pos.qty)} {token[:4]}… @ {price:.6f} PnL {pnl:+.4f}"
                    )

            nav = self.pb.nav()
            self.pb.update_peak(nav)
            NAV_G.set(nav)
            if self.start_nav:
                PNL_G.set(100 * (nav - self.start_nav) / self.start_nav)

            for token, ts in list(self.closed.items()):
                if now - ts >= PRUNE_INTERVAL_H * 3600:
                    self.closed.pop(token, None)

            await asyncio.sleep(60)

    async def run(self):
        start_http_server(9100)
        await asyncio.gather(self._wallet_stream(), self._mark_positions())
