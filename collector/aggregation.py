# 告警聚合器：收集窗口内的多条告警，统一分析根因，生成一条聚合告警
import time


class AlertAggregator:
    # window_size：窗口大小（秒）
    # max_alerts：缓冲区最多存多少条告警
    def __init__(self, window_size: int = 300, max_alerts: int = 50):
        self.window_size = window_size
        self.max_alerts = max_alerts
        # 窗口中的告警
        self.alerts = []
        self.window_start = None

    # monitor需要将触发告警的参数发送到下方方法
    def add_alert(self, node, resource, value, threshold, timestamp):
        # 第一条告警进来，启动窗口倒计时
        if not self.alerts:
            self.window_start = time.time()

        self.alerts.append({
            "node": node,
            "resource": resource,
            "value": value,
            "threshold": threshold,
            "timestamp": timestamp,
        })

        # 缓冲区满了，强制触发聚合
        if len(self.alerts) >= self.max_alerts:
            return True  # 该剧合理了

        return False

    # 检测窗口到期时间
    def should_flush(self):
        if not self.alerts:
            return False
        if self.window_start is None:
            return False
        return (time.time() - self.window_start) >= self.window_size

    # 取出所有告警并清空缓冲区
    def flush(self):
        if not self.alerts:
            return False
        # 把告警参数拷贝过来
        snap = self.alerts.copy()
        # 清空原告警参数
        self.alerts.clear()
        self.window_start = None
        return snap

    # 统计当前告警数
    def count(self) -> int:
        return len(self.alerts)
