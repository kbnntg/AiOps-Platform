# 该模块用于处理后端Prometheus请求
"""
创建类，接收传来的URL
1. 定义当前时间截取的Prometheus语句的方法，返回.json()["data"]["result"]
2. 定义一段时间截取的Promenade语句的方法，返回.json()["data"]["result"]
3. 定义一个当前节点状态的方法，需要与上面两个方法返回的请求体一起用（较复杂）
"""
from datetime import datetime, timedelta
from typing import List

import requests

from core.config import settings


# 创建类，获取URL（从setting实例中获取类方法）
class PrometheusService:
    # 定义__init__法
    def __init__(self):
        self.base_url = settings.PROMETHEUS_URL

    # 定义获取当前时段的Prometheus语句的方法
    def query(self, query: str) -> List:
        try:
            respose = requests.get(
                f"{self.base_url}/api/v1/query",
                params={"query": query}, timeout=15     # query就是查询的语句
            )
            data = respose.json()

            """
                    返回的这个：
                    {
                    "metric": {"__name__": "up", "instance": "localhost:9090", "job": "prometheus"},
                    "value": [1726000000, "1"]
                  }
            """

            return data['data']['result']
        except Exception:
            print(f'Prometheus query失败')
            return []

    # 定义获取一段时间范围的Prometheus语句方法
    def query_range(self, query: str, hout: int = 1) -> List:
        end = datetime.now()
        start = end - timedelta(hours=hout)
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/query_range",
                params={
                    "query": query,
                    "start": start.timestamp(),
                    "end": end.timestamp(),
                    "step": "30s"
                },
                timeout=15
            )
            data = response.json()
            return data['data']['result']
        except Exception:
            print(f'Prometheus query_range失败')
            return []

    # 获取当前节点状态方法，将查询语句调用上面的函数获取详情
    def get_current_node(self) -> List:
        # 定义空的字典
        nodes = {}
        # 将查询语句为遍历对象给metric_name，metric_name传入到query方法中，用来返回
        for metric_name, key in [("CPU_use_percent", "cpu"),
                                 ("Free_use_percent", "memory"),
                                 ("Disk_use_percent", "disk")]:
            for r in self.query(metric_name):
                """
                        metric": {"__name__": "up", "instance": "localhost:9090", "job": "prometheus"},
                                "value": [1726000000, "1"]
                """
                # r就获取上面的值，inst就等于metric值从中get到instance实例地址
                inst = r["metric"].get("instance", "unknown")
                # 第一次肯定没在里面，就放入到字典
                if inst not in nodes:
                    nodes[inst] = {'name': inst}
                    # key值就等于value的下表为1的值，比如是1
                nodes[inst][key] = round(float(r['value'][1]), 2)
        return list(nodes.values())

