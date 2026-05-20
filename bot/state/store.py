class StateStore:
    def __init__(self):
        self.state = {
            "position_size": 0,
            "entry_price": None,
            "level": 1,
            "entry_order_id": None,
            "tp_order_id": None,
            "reentry_order_id": None,
            "symbol": None
        }

    # -------------------------
    # READ
    # -------------------------
    def get(self):
        return self.state

    def reset(self):
        self.state = {
            "position_size": 0,
            "entry_price": None,
            "level": 1,
            "entry_order_id": None,
            "tp_order_id": None,
            "reentry_order_id": None,
            "symbol": None
        }

    # -------------------------
    # UPDATE ENTRY
    # -------------------------
    def set_entry(self, price, size, order_id=None, symbol=None):
        self.state["entry_price"] = price
        self.state["position_size"] = size
        self.state["entry_order_id"] = order_id
        self.state["symbol"] = symbol
        self.state["level"] = 1

    # -------------------------
    # LEVEL UP (ladder groeit)
    # -------------------------
    def increase_level(self):
        self.state["level"] += 1

    # -------------------------
    # UPDATE POSITION SIZE
    # -------------------------
    def update_position_size(self, new_size):
        self.state["position_size"] = new_size

    # -------------------------
    # CLEAR AFTER EXIT
    # -------------------------
    def clear_position(self):
        self.reset()

state = {
    "symbol": None,
    "position_size": 0,
    "entry_price": None,
}
