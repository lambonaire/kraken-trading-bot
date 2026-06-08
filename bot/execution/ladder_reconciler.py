from bot.exchange.kraken_futures import get_tick_size, round_to_tick


class LadderReconciler:
    """
    Single source of truth for:
    - TP orders
    - Reentry orders
    - Ladder progression
    - Order cleanup
    """

    def __init__(self, exchange, state_store, strategy):
        if strategy is None:
            raise ValueError("strategy is required for LadderReconciler")

        self.exchange = exchange
        self.state_store = state_store
        self.strategy = strategy

    def reconcile(self, symbol, entry_price=None, position_size=None, level=None):

        state = self.state_store.get(symbol)

        if not hasattr(self.strategy, "reentry_levels"):
            raise ValueError("Invalid strategy object: missing reentry_levels")

        live_entry_price = entry_price or state.get("entry_price")
        live_position_size = position_size or state.get("position_size")

        if live_entry_price is None or live_position_size is None:
            print("[RECONCILE] waiting for confirmed fill")
            return state

        try:
            live_entry_price = float(live_entry_price)
            live_position_size = float(live_position_size)
        except Exception:
            print("[RECONCILE] invalid entry data")
            return state

        if live_position_size <= 0:
            print("[RECONCILE] waiting for confirmed fill")
            return state

        direction = self._normalize_direction(
            getattr(self.strategy, "direction", "long")
        )

        max_level = int(getattr(self.strategy, "max_level", 1))
        level = int(level or state.get("level") or 1)
        level = max(1, min(level, max_level))

        level_cfg = self.strategy.reentry_levels[level - 1]

        print(f"[RECONCILE] entry={live_entry_price} size={live_position_size} level={level}")

        # =========================
        # CANCEL EXISTING ORDERS
        # =========================
        self._cancel_if_exists(state.get("tp_order_id"))
        self._cancel_if_exists(state.get("reentry_order_id"))

        # =========================
        # TICK SIZE
        # =========================
        tick = get_tick_size(symbol)
        if not tick:
            raise ValueError(f"[CRITICAL] No tick size found for {symbol}")

        # =========================
        # TAKE PROFIT
        # =========================
        tp_pct = float(level_cfg.get("take_profit_pct", 0.003))

        if direction == "long":
            tp_price_raw = live_entry_price * (1 + tp_pct)
            tp_side = "sell"
        else:
            tp_price_raw = live_entry_price * (1 - tp_pct)
            tp_side = "buy"

        tp_price = round_to_tick(tp_price_raw, tick)

        tp_order = (
            self.exchange.sell_limit
            if tp_side == "sell"
            else self.exchange.buy_limit
        )(
            symbol=symbol,
            size=live_position_size,
            price=tp_price,
            reduce_only=True,
        )

        if self._ok(tp_order):
            state["tp_order_id"] = self._extract_order_id(tp_order)
            state["tp_price"] = tp_price
            state["tp_size"] = live_position_size
            print(f"[TP OK] {tp_price}")
        else:
            state["tp_order_id"] = None
            state["tp_price"] = None
            state["tp_size"] = None
            print("[TP FAIL]", tp_order)

        # =========================
        # MAX LEVEL
        # =========================
        if level >= max_level:
            state.update({
                "reentry_order_id": None,
                "reentry_price": None,
                "reentry_size": None,
                "level": level,
                "needs_new_ladder": False,
                "ladder_active": True,
                "last_reconciled_level": level,
                "last_reconciled_position_size": live_position_size,
            })
            return state

        # =========================
        # REENTRY (FRACTIONAL SAFE)
        # =========================
        drop_pct = float(level_cfg.get("drop_pct", 0.01))
        size_mult = float(level_cfg.get("size_multiplier", 1.0))

        if direction == "long":
            reentry_price_raw = live_entry_price * (1 - drop_pct)
            reentry_side = "buy"
        else:
            reentry_price_raw = live_entry_price * (1 + drop_pct)
            reentry_side = "sell"

        reentry_price = round_to_tick(reentry_price_raw, tick)

        # 🔴 FIX: NO INT, NO FORCE TO 1
        reentry_size = round(live_position_size * size_mult, 8)

        min_reentry_size = float(level_cfg.get("min_size", 0.001))

        print(
            f"[DEBUG REENTRY] raw={reentry_price_raw} "
            f"price={reentry_price} "
            f"size={reentry_size}"
        )

        # safety gate instead of forcing 1
        if reentry_size <= 0:
            print("[REENTRY] size <= 0 -> skip")
            state["reentry_order_id"] = None
            state["reentry_price"] = None
            state["reentry_size"] = None
            return state

        if reentry_size < min_reentry_size:
            print("[REENTRY] below min_size -> skip")
            state["reentry_order_id"] = None
            state["reentry_price"] = None
            state["reentry_size"] = None
            return state

        reentry_order = (
            self.exchange.buy_limit
            if reentry_side == "buy"
            else self.exchange.sell_limit
        )(
            symbol=symbol,
            size=reentry_size,
            price=reentry_price,
            reduce_only=False,
        )

        if self._ok(reentry_order):
            state["reentry_order_id"] = self._extract_order_id(reentry_order)
            state["reentry_price"] = reentry_price
            state["reentry_size"] = reentry_size
            print("[REENTRY OK]")
        else:
            state["reentry_order_id"] = None
            state["reentry_price"] = None
            state["reentry_size"] = None
            print("[REENTRY FAIL]", reentry_order)

        # =========================
        # STATE UPDATE
        # =========================
        state.update({
            "position_size": live_position_size,
            "entry_price": live_entry_price,
            "level": level,
            "needs_new_ladder": False,
            "ladder_active": True,
            "reentry_pending": False,
            "last_reconciled_level": level,
            "last_reconciled_position_size": live_position_size,
        })

        return state

    # =========================
    # HELPERS
    # =========================
    def _normalize_direction(self, d):
        return "short" if str(d).lower() in ("short", "sell") else "long"

    def _cancel_if_exists(self, order_id):
        if not order_id:
            return
        try:
            self.exchange.cancel_order(order_id)
        except Exception as e:
            print("[CANCEL ERROR]", e)

    def _ok(self, r):
        return r and r.get("sendStatus", {}).get("status") == "placed"

    def _extract_order_id(self, r):
        if not r:
            return None
        return r.get("sendStatus", {}).get("order_id")
