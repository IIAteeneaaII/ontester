class Thresholds:
    def __init__(
        self,
        min_tx=1.0,
        max_tx=5.0,
        min_rx=-19.0,
        max_rx=-13.0,
        min_wifi24=60,
        min_wifi5=60,
    ):
        self.min_tx = min_tx
        self.max_tx = max_tx
        self.min_rx = min_rx
        self.max_rx = max_rx
        self.min_wifi24 = min_wifi24
        self.min_wifi5 = min_wifi5