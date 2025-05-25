from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Sequence, cast
from collections import deque
import math
import random

import aiohttp
import base58
from prometheus_client import Gauge, Histogram, start_http_server
from solders.keypair import Keypair
from solana.rpc.api import Client
from solders.transaction import VersionedTransaction as Transaction

from config import (
    GLOBAL_DD_PCT,
    PRUNE_INTERVAL_H,
    PRIV_KEY,
    RPC_URL,
    JITO_RPC,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
    SOL_MINT,
    DRY_RUN,
    SIM_SLIPPAGE_BPS,
)
from exec import JupiterExec, add_priority_fee
from mev import send_bundle
from safety import SafetyChecker, SolscanAPI
from sizing import kelly_size, pyth_atr, pyth_price
from wallet import FlipsideAPI, WalletMetrics


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
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    self.api,
                    json={"chat_id": self.chat, "text": msg},
                    timeout=aiohttp.ClientTimeout(total=10),
                ):
                    pass
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).warning("Notifier error: %s", exc)


NAV_G = Gauge("bot_nav_sol", "Current NAV in SOL")
PNL_G = Gauge("bot_pnl_pct", "PnL % from start")
SLIPPAGE_G = Histogram("slippage_bps", "Slippage per trade")
INCLUSION_G = Histogram("inclusion_ms", "ms from send to confirm")


class CopyEngine:
    def __init__(
        self,
        seed_addrs: Sequence[str],
        *,
        dry: bool = DRY_RUN,
        ws_log: str | None = None,
        journal_path: str = "journal.csv",
    ):
        self.addrs = set(seed_addrs)
        self.notif = Notifier()
        self.flipside = FlipsideAPI(self.notif)
        self.sol = SolscanAPI(self.notif)
        self.exec = JupiterExec(self.notif)
        self.pb = PositionBook(100)
        self.safe = SafetyChecker(self.sol, self.notif)
        self.closed: Dict[str, float] = {}
        self.metrics: Dict[str, WalletMetrics] = {}
        self.start_nav = self.pb.init
        self.nav_hist: deque[float] = deque([self.pb.init], maxlen=1440)
        self.dry = dry
        self.ws_log = ws_log
        self.journal_path = journal_path

    def _log_trade(
        self,
        ts: float,
        address: str,
        token: str,
        side: str,
        qty: float,
        price: float,
        nav_after: float,
    ) -> None:
        """Append a trade line to the journal CSV."""
        line = f"{ts:.3f},{address},{token},{side},{qty},{price:.6f},{nav_after:.4f}\n"
        try:
            p = Path(self.journal_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).warning("journal write failed: %s", exc)

    def _nav_vol(self) -> float:
        if len(self.nav_hist) < 2:
            return 0.0
        returns = [
            (self.nav_hist[i] / self.nav_hist[i - 1]) - 1
            for i in range(1, len(self.nav_hist))
        ]
        alpha = 2 / 1441
        ewma = 0.0
        for r in reversed(returns):
            ewma = alpha * r * r + (1 - alpha) * ewma
        sigma = math.sqrt(ewma) * math.sqrt(525_600)
        return sigma

    async def _refresh_seed_wallets(self) -> None:
        """Placeholder for polling trending wallets and updating seeds."""
        await asyncio.sleep(0)

    async def _size(
        self, token: str, sharpe: float, nav: float, trades: int = 30
    ) -> float:
        vol = await pyth_atr(token, notif=self.notif) or 0.05
        stake = kelly_size(nav, sharpe, vol, trades)
        sigma = self._nav_vol()
        if sigma > 0:
            stake *= 0.10 / sigma
        return stake

    async def _execute_buy(self, ev: dict):
        token = ev["token"]
        price = float(ev["price"])
        nav = self.pb.nav()
        pos = self.pb.pos.get(token)
        if pos and self.pb.mark.get(token, pos.entry) * pos.qty >= 0.3 * nav:
            return
        wallet = ev.get("address")
        metrics = self.metrics.get(wallet) if wallet else None
        trades = metrics.trades if metrics else 30
        stake = await self._size(token, 1.5, nav, trades)  # assume sharpe proxy
        amt = int(stake / price)
        if amt <= 0:
            logging.getLogger(__name__).info("trade size <1, skipping")
            return None
        quote = await self.exec.quote(SOL_MINT, token, amt)
        route = quote["data"][0]
        if isinstance(route, dict):
            quote_price = float(route.get("outAmount", 0)) / max(amt, 1)
        else:
            quote_price = price
        tx_resp = await self.exec.swap_tx(route)
        if isinstance(tx_resp, dict):
            tx_b64 = cast(
                str, tx_resp.get("tx") or tx_resp.get("swapTransaction") or ""
            )
            exec_px = cast(float | None, tx_resp.get("exec_px"))
        else:
            tx_b64 = cast(str, tx_resp)
            exec_px = None

        if not self.dry:
            tx_bytes = base64.b64decode(tx_b64)
            tx_bytes = await add_priority_fee(tx_bytes)
            kp = Keypair.from_bytes(base58.b58decode(PRIV_KEY))
            tx = Transaction.from_bytes(tx_bytes)
            signature = kp.sign_message(bytes(tx.message))
            tx = Transaction.populate(tx.message, [signature, *tx.signatures[1:]])
            client = Client(RPC_URL)
            try:
                start_t = time.time()
                if JITO_RPC:
                    ok = await send_bundle(base64.b64encode(bytes(tx)).decode())
                    if ok:
                        sig = "bundle"
                    else:
                        resp = cast(
                            dict[str, Any], client.send_raw_transaction(bytes(tx))
                        )
                        sig = resp.get("result", "raw")
                else:
                    resp = cast(dict[str, Any], client.send_raw_transaction(bytes(tx)))
                    sig = resp["result"]
                INCLUSION_G.observe((time.time() - start_t) * 1000)
                logging.getLogger(__name__).info("tx %s sent", sig)
            except Exception as exc:  # noqa: BLE001
                logging.getLogger(__name__).warning("tx failure: %s", exc)
                sig = "err"
        else:
            exec_px = quote_price * (
                1 + (SIM_SLIPPAGE_BPS / 10_000) * (1 if random.random() < 0.5 else -1)
            )
            sig = f"SIM-{int(time.time()*1000)}"

        if exec_px is not None and quote_price:
            slippage = abs(exec_px / quote_price - 1) * 10_000
        else:
            slippage = 0.0
        SLIPPAGE_G.observe(slippage)
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
        self.nav_hist.append(nav)
        self._log_trade(time.time(), wallet or "", token, "buy", amt, price, nav)
        dd = self.pb.global_dd(nav)
        if dd >= GLOBAL_DD_PCT:
            await self.notif.send(
                f"GLOBAL DD {dd:.1f}% exceeds {GLOBAL_DD_PCT}% – shutting down"
            )
            Path("flag_down").write_text(f"{nav:.4f}")
            await asyncio.sleep(86400)
            raise SystemExit("drawdown limit hit")
        return sig

    async def _wallet_stream(self):
        if self.ws_log:
            prev = None
            with open(self.ws_log, "r", encoding="utf-8") as f:
                for line in f:
                    ev = json.loads(line)
                    ts = ev.get("timestamp", ev.get("ts", 0)) / 1000
                    if prev is not None:
                        await asyncio.sleep(max(0, ts - prev))
                    prev = ts
                    if ev.get("address") in self.addrs and ev.get("side") == "buy":
                        token = ev.get("token")
                        if token and await self.safe.is_safe(token):
                            await self._execute_buy(ev)
        else:
            # No real WS – fall back to a long-poll every 60 s
            while True:
                await self._refresh_seed_wallets()
                await asyncio.sleep(60)

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
                    self._log_trade(
                        now, "", token, "sell", pos.qty, price, self.pb.nav()
                    )

            nav = self.pb.nav()
            self.pb.update_peak(nav)
            NAV_G.set(nav)
            if self.start_nav:
                PNL_G.set(100 * (nav - self.start_nav) / self.start_nav)
            self.nav_hist.append(nav)

            for token, ts in list(self.closed.items()):
                if now - ts >= PRUNE_INTERVAL_H * 3600:
                    self.closed.pop(token, None)

            await asyncio.sleep(60)

    async def run(self):
        start_http_server(9100)
        tasks = [
            asyncio.create_task(self._wallet_stream()),
            asyncio.create_task(self._mark_positions()),
        ]
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for t in tasks:
                t.cancel()
            await self.exec.close()
            await self.sol.close()
