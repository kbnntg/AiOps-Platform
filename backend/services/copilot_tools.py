# AI Copilot
# 传统是用户手动输入，AI进行分析输出结果，AI Copilot算是Agent，AI可以调用各种工具来查看数据，返回给用户

"""
Agent（Function Calling）
text
用户：最近哪个 Pod 重启最多？
  ↓
AI："我需要调用 list_pods 工具"
  ↓
后端：执行 list_pods，拿到真实数据
  ↓
AI：（看到真实数据）"node-monitor-zq52h 重启 3 次最多"
  ↓
用户：✅ 准确的
核心：AI 不直接回答，而是先"请求调用工具"，后端执行后把结果给 AI，AI 再回答。
"""
from typing import Dict, Any

from services.k8s_service import K8sService
from services.prometheus_service import PrometheusService
from services.topology_service import TopologyService

"""
核心功能：
1. 定义工具清单（告诉 AI："你能调用这 10 个工具"）
2. 执行工具（AI 选了某个工具时，真正去调 K8s/Prometheus）
"""

# 用户发送工具菜单，AI根据工具菜单来调用相对应的工具来回答用户问题

############ 实例：
"""
用户问：最近的 Pod 重启最多的是哪个？

附带的工具菜单：
[
  {
    "name": "list_pods",
    "description": "列出指定命名空间的所有 Pod",
    "parameters": {
      "namespace": "命名空间名称（可选，默认 default）"
    }
  },
  {
    "name": "get_pod_logs",
    "description": "获取 Pod 的日志",
    "parameters": {
      "namespace": "命名空间",
      "name": "Pod 名称"
    }
  },
  ...
]

AI 看到菜单后，会判断："用户问的是 Pod 状态，我需要调用 list_pods 工具"。

然后 AI 不会直接回答，而是返回：

json
{
  "tool_calls": [
    {
      "name": "list_pods",
      "arguments": {"namespace": "privatization"}
    }
  ]
}
我们的代码就负责：

收到这个 tool_calls

执行 list_pods("privatization")

把结果返回给 AI

AI 看到结果后，输出最终答案


"""

# 1.工具定义（告诉 AI 有哪些工具）
# 格式遵循 OpenAI Function Calling 规范
# 每个工具包含：name（名字）、description（描述）、parameters（参数）
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_pods",
            "description": "列出指定命名空间的所有 Pod，返回 Pod 名称、状态、节点、重启次数等信息。用于回答'有哪些 Pod'、'哪个 Pod 重启最多'这类问题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "命名空间名称，默认为 privatization",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pod_logs",
            "description": "获取指定 Pod 的日志，用于排查问题。返回最后 N 行的日志文本。",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "命名空间"},
                    "name": {"type": "string", "description": "Pod 名称"},
                    "tail_lines": {"type": "integer", "description": "返回最后多少行，默认 100"},
                },
                "required": ["namespace", "name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pod_events",
            "description": "获取指定 Pod 的 Kubernetes 事件，用于查看 Pod 是否出现 OOMKilled、FailedScheduling、BackOff 等异常。",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "命名空间"},
                    "name": {"type": "string", "description": "Pod 名称"},
                },
                "required": ["namespace", "name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_deployments",
            "description": "列出指定命名空间的所有 Deployment，返回副本数、就绪副本数、镜像等信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "命名空间"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_metrics",
            "description": "查询 Prometheus 指标趋势。可用于查看 CPU、内存、磁盘使用率的历史曲线。",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": "指标名，可选 CPU_use_percent / Free_use_percent / Disk_use_percent",
                        "enum": ["CPU_use_percent", "Free_use_percent", "Disk_use_percent"],
                    },
                    "hours": {"type": "integer", "description": "查询最近多少小时，默认 1"},
                },
                "required": ["metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_alerts",
            "description": "查询告警历史记录，返回最近 N 条告警，包含资源类型、当前值、阈值、AI 建议等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "返回多少条，默认 10"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_topology",
            "description": "获取 K8s 服务拓扑图，返回节点（Deployment/Pod/Service）和它们之间的关系边。用于分析服务依赖关系。",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "命名空间（可选，不传则返回全部）"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_namespaces",
            "description": "列出集群中所有命名空间。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_nodes",
            "description": "列出集群中所有节点及其状态（Ready/NotReady）。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose_pod",
            "description": "对指定 Pod 进行多信号融合诊断（指标+日志+事件+告警），调用大模型分析根因。耗时长（10~30秒）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "命名空间"},
                    "name": {"type": "string", "description": "Pod 名称"},
                },
                "required": ["namespace", "name"],
            },
        },
    },
]


# 2. 工具执行器（AI 调工具时真正执行）
class ToolExecutor:
    # 执行AI请求的工具调用
    def __init__(self):
        self.k8s = K8sService()
        self.prom = PrometheusService()
        self.topology = TopologyService()

    # 执行工具，返回结果
    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        # 根据工具名发到不同方法，输入list_pod就是_tool_list_pod
        handler = getattr(self, f'_tool_{tool_name}', None)
        if not handler:
            # 找不到就未知
            return {'error': f"未知工具：{tool_name}"}
        try:
            # 找到就返回**arguments 是字典展开
            return handler(**arguments)
        except Exception as e:
            return {'error': f"工具执行失败{e}"}

    # 找到工具对应的_tool_xxx方法，这些方法去掉前缀_tool_其他必须要和工具中定义的名字一致
    def _tool_list_pods(self, namespace: str = 'privatization'):
        pods = self.k8s.list_pods(namespace=namespace)
        # 返回AI需要的字段
        return [{
            'name': p['name'],
            'status': p['status'],
            'node': p.get('node'),
            'restarts': p.get('restarts', 0),
        } for p in pods]

    # 找日志
    def _tool_get_pod_logs(self, namespace: str, name: str, tail_lines: int = 100):
        logs = self.k8s.get_pod_log(namespace=namespace, name=name, tail_lines=tail_lines)
        # 最多要5000行
        if len(logs) >= 5000:
            logs = logs[-5000:]
        return {'logs': logs}

    # 事件
    def _tool_get_pod_events(self, namespace: str, name: str):
        events = self.k8s.get_pod_event(namespace=namespace, name=name)
        return events

    # deployment列表
    def _tool_list_deployments(self, namespace: str = 'privatization'):
        deployments = self.k8s.get_deployment(namespace)
        return deployments

    # 资源值
    def _tool_get_metrics(self, metric: str, hours: int = 1):
        # 限制时间
        hour = max(1, min(hours, 24))
        data = self.prom.query_range(metric, hout=hour)

        # 只返回每条时序摘要
        summaries = []
        for r in data:
            # 获取资源值
            values = r.get('values', [])
            if not values:
                continue
            nums = [float(v[1]) for v in values]
            summaries.append({
                "instance": r.get("metric", {}).get("instance", "unknown"),
                "current": round(nums[-1], 1),
                "max": round(max(nums), 1),
                "avg": round(sum(nums) / len(nums), 1),
            })
        return summaries

    # 告警记录
    def _tool_get_alerts(self, limit: int = 10):
        from services.alert_service import AlertService
        svc = AlertService()
        # 默认传输十个
        alerts = svc.get_alert(limit=limit)
        return alerts

    # 拓扑关系
    def _tool_get_topology(self, namespace: str = None):
        result = self.topology.get_topology(namespace)
        # 只给名字和类型
        nodes = [{"name": n["name"], "type": n["type"], "health": n["health"]} for n in result["nodes"]]
        edges = [{"source": e["source"], "target": e["target"], "type": e["type"]} for e in result["edges"]]
        return {"nodes": nodes, "edges": edges}

    # 获取命名空间和节点
    def _tool_list_namespaces(self):
        return self.k8s.list_namespace()

    def _tool_list_nodes(self):
        return self.k8s.list_nodes()

    # 多混合
    def _tool_diagnose_pod(self, namespace: str, name: str):
        return {
            "message": "多信号诊断需要调用 /api/pods/{name}/diagnose 接口，暂不支持在 Copilot 中调用。请提示用户手动使用诊断功能。"}
