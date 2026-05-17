class BaseStrategy:
    def on_tick(self, market_data, state, config):
        raise NotImplementedError
