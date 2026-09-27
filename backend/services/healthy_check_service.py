# 集群巡检
"""
步骤：
1. 导入模块
2. 创建实例并定义注册表
3. 循环遍历注册表并进行加减分
4. 检测配置方法
5. 定义资源列表

"""
from typing import Dict, List, Optional

from services.k8s_service import K8sService


class HealthCheckService:
    def __init__(self):
        self.k8s = K8sService()
        self.core_v1 = self.k8s.core_v1
        self.apps_v1 = self.k8s.apps_v1

        # 注册表，新规则加到这里
        self.rules = [
            {'id': 'pod-no-requests', 'name': 'Pod 未配置 requests', 'func': self._check_pod_no_requests},
            {'id': 'pod-no-limits', 'name': 'Pod 未配置 limits', 'func': self._check_pod_no_limits},
            {'id': 'pod-no-liveness', 'name': 'Pod 未配置 livenessProbe', 'func': self._check_pod_no_liveness},
            {'id': 'pod-no-readiness', 'name': 'Pod 未配置 readinessProbe', 'func': self._check_pod_no_readiness},
            {'id': 'pod-latest-image', 'name': '镜像 tag 是 latest', 'func': self._check_pod_latest_image},
            {'id': 'pod-pending', 'name': 'Pod 长期 Pending', 'func': self._check_pod_pending},
            {'id': 'pod-high-restarts', 'name': 'Pod 重启次数偏高', 'func': self._check_pod_high_restarts},
            {'id': 'deploy-single-replica', 'name': 'Deployment 单副本', 'func': self._check_deploy_single_replica},
            {'id': 'svc-no-endpoints', 'name': 'Service 无 endpoints', 'func': self._check_svc_no_endpoints},
            {'id': 'node-pressure', 'name': '节点有压力污点', 'func': self._check_node_pressure},
            {'id': 'node-not-ready', 'name': '节点 NotReady', 'func': self._check_node_not_ready},
        ]

    # 执行巡检，返回健康分和问题
    def run_check(self, namespace: Optional[str] = None) -> Dict:
        # 1.定义资源
        pods = self._list_pods(namespace)
        deployment = self._list_deployments(namespace)
        services = self._list_services(namespace)
        endpoints = self._list_endpoints(namespace)
        nodes = self._list_nodes()  # 节点是全集群的，不受namespace影响

        # 定义这个字典，后续传入参数不需要一个一个变零名输入了，直接(resource)就能传过去
        resource = {
            'pods': pods,
            'deployments': deployment,
            'services': services,
            'endpoints': endpoints,
            'nodes': nodes
        }

        # 2. 逐条规则执行，用一个变量获取rules'func'值获取到的值（用resource）资源进行调度
        issues = []
        for rule in self.rules:
            try:
                rule_issues = rule['func'](resource)
                for issue in rule_issues:
                    issue['rule'] = rule['id']
                    issue['rule_name'] = rule['name']
                issues.extend(rule_issues)
            except Exception as e:
                print(f"规则 {rule['id']} 执行失败：{e}")

        """
        上面那个执行步骤：1.定义一个空列表
        2. 使用rule变量循环遍历注册表，之后使用rule_issues获取rule将资源值传入'func'函数中的结果，大概是：
        rule_issues = [
    {
        'severity': 'warning',
        'resource': 'Pod/privatization/nginx-5dc74f67cc-b5tdm',
        'message': '容器 nginx 未配置 resources.requests',
        'suggestion': '添加 requests.cpu 和 requests.memory...'
    },
    {
        'severity': 'warning',
        'resource': 'Pod/privatization/aiops-backend-59b9c4bc75',
        'message': '容器 backend 未配置 resources.requests',
        'suggestion': '添加 requests.cpu 和 requests.memory...'
    },
    {
        'severity': 'warning',
        'resource': 'Pod/privatization/aiops-frontend-6b49fcc9ff',
        'message': '容器 frontend 未配置 resources.requests',
        'suggestion': '添加 requests.cpu 和 requests.memory...'
    },
]
        3. 之后使用issue循环遍历获取到的上序列表，定义两个字段'rule'获取rule的id，最外层循环，就是注册表对应的id值，rule_name获取注册表的name
        4. 最后让issues把上序的列表追加进来
        """

        # 统计严重值
        summary = {'critical': 0, 'warning': 0, 'info': 0}
        for issue in issues:
            summary[issue['severity']] = summary.get(issue['severity'], 0) + 1
        """
        使用issue遍历issues列表，找到对应字段的告警等级，有一个就加1
        """

        # 4.计算健康值, 最高等级-10分
        score = 100
        score -= summary['critical'] * 10
        score -= summary['warning'] * 3
        score -= summary['info'] * 1
        score = max(0, score)

        # 返回
        return {
            'score': score,
            'total': len(issues),
            'summary': summary,
            'issues': issues,
            'scanned': {
                'pods': len(pods),
                'deployments': len(deployment),
                'services': len(services),
                'nodes': len(nodes),
            },
        }

    # 开始配置规则检查
    def _check_pod_no_requests(self, resource: Dict) -> List[Dict]:
        # 检查未配置requests的pod
        issues = []
        for p in resource['pods']:
            for c in p.spec.containers or []:
                if not c.resources or not c.resources.requests:
                    issues.append({
                        'severity': 'warning',
                        'resource': f"Pod/{p.metadata.namespace}/{p.metadata.name}",
                        'message': f"容器 {c.name} 未配置 resources.requests",
                        'suggestion': "添加 requests.cpu 和 requests.memory，让调度器能正确分配资源",
                    })
        return issues

    # 判断是否配置limit
    def _check_pod_no_limits(self, resource: Dict) -> List[Dict]:
        issues = []
        for p in resource['pods']:
            for c in p.spec.containers or []:
                if not c.resources or not c.resources.limits:
                    issues.append({
                        'severity': 'warning',
                        'resource': f"Pod/{p.metadata.namespace}/{p.metadata.name}",
                        'message': f"容器 {c.name} 未配置 resources.limits",
                        'suggestion': "添加 limits.cpu 和 limits.memory，防止容器吃光节点资源",
                    })
        return issues

    # 判断是否配置livenessProbe
    def _check_pod_no_liveness(self, resource: Dict) -> List[Dict]:
        issues = []
        for p in resource['pods']:
            for c in p.spec.containers or []:
                if not c.liveness_probe:
                    issues.append({
                        'severity': 'info',
                        'resource': f"Pod/{p.metadata.namespace}/{p.metadata.name}",
                        'message': f"容器 {c.name} 未配置 livenessProbe",
                        'suggestion': "添加 livenessProbe，容器假死时能自动重启",
                    })
        return issues

    # 判断是否配置了readiness
    def _check_pod_no_readiness(self, resource: Dict) -> List[Dict]:
        issues = []
        for p in resource['pods']:
            for c in p.spec.containers or []:
                if not c.readiness_probe:
                    issues.append({
                        'severity': 'info',
                        'resource': f"Pod/{p.metadata.namespace}/{p.metadata.name}",
                        'message': f"容器 {c.name} 未配置 Readiness",
                        'suggestion': "添加 readinessProbe，避免流量打到未就绪的 Pod",
                    })
        return issues

    # 判断image标签是不是latest
    def _check_pod_latest_image(self, resource: Dict) -> List[Dict]:
        issues = []
        for p in resource['pods']:
            for c in p.spec.containers or []:
                # 获取image标签
                image = c.image or ''
                # 从最后剪切：后的字段，是不是latest或空白
                if image.endswith(':latest') or (':' not in image.split('/')[-1]):
                    issues.append({
                        'severity': 'warning',
                        'resource': f"Pod/{p.metadata.namespace}/{p.metadata.name}",
                        'message': f"容器 {c.name} 镜像 tag 是 latest 或未指定: {image}",
                        'suggestion': "使用明确的版本 tag，如 nginx:1.25.3，避免不可控的版本变化",
                    })
        return issues

    # 判断pod状态是否是pending
    def _check_pod_pending(self, resource: Dict) -> List[Dict]:
        issues = []
        for p in resource['pods']:
            if p.status.phase == 'Pending':
                issues.append({
                    'severity': 'critical',
                    'resource': f"Pod/{p.metadata.namespace}/{p.metadata.name}",
                    'message': "Pod 处于 Pending 状态，可能无法调度",
                    'suggestion': "检查节点资源是否充足、PVC 是否绑定、是否有污点未容忍",
                })
        return issues

    # 判断重启次数搞得Pod
    def _check_pod_high_restarts(self, resource: Dict) -> List[Dict]:
        issues = []
        for p in resource['pods']:
            statuses = p.status.container_statuses or []
            restarts = sum(s.restart_count for s in statuses)
            if restarts >= 5:
                issues.append({
                    'severity': 'warning',
                    'resource': f"Pod/{p.metadata.namespace}/{p.metadata.name}",
                    'message': f"Pod 累计重启 {restarts} 次",
                    'suggestion': "查看 Pod 事件和日志，排查崩溃原因（如 OOMKilled、配置错误）",
                })
        return issues

    # 判断Deployment副本数
    def _check_deploy_single_replica(self, resource: Dict) -> List[Dict]:
        issues = []
        for d in resource['deployments']:
            replicas = d.spec.replicas or 0
            if replicas == 1:
                issues.append({
                    'severity': 'info',
                    'resource': f"Deployment/{d.metadata.namespace}/{d.metadata.name}",
                    'message': "Deployment 只有 1 个副本，没有高可用",
                    'suggestion': "生产环境建议至少 2 个副本，避免单点故障",
                })
        return issues

    # 判断service是否有匹配的endpoint
    def _check_svc_no_endpoints(self, resource: Dict) -> List[Dict]:
        issues = []
        # 遍历endpoint，取它的namespace、name和subsets(这里面有address）
        ep_map = {}
        for ep in resource['endpoints']:
            key = f'{ep.metadata.namespace}/{ep.metadata.name}'
            # 存入subsets
            ep_map[key] = ep.subsets or []

        # 遍历service，得看看有没有匹配的endpoint
        for s in resource['services']:
            # 跳过系统Service
            if s.metadata.namespace == 'default' or s.metadata.namespace == 'kubernetes':
                continue
            # 获取service命名空间及name
            key = f'{s.metadata.namespace}/{s.metadata.name}'
            # 把ep_map的subsets取出来
            subset = ep_map.get(key, [])

            # 没有subsets就死
            endpoints = False
            # 遍历subset，有address就代表有对应的，为True
            for sb in subset:
                if sb.addresses:
                    endpoints = True
                    break
            if not endpoints:
                issues.append({
                    'severity': 'warning',
                    'resource': f"Service/{s.metadata.namespace}/{s.metadata.name}",
                    'message': "Service 没有可用的 endpoints",
                    'suggestion': "检查 selector 是否匹配到 Pod，或后端 Pod 是否就绪",
                })
        return issues

    # 判断节点是否有污点
    def _check_node_pressure(self, resource: dict) -> List[Dict]:
        # 先定义污点
        issues = []
        taints_w = ['disk-pressure', 'memory-pressure', 'pid-pressure']
        # 遍历节点
        for n in resource['nodes']:
            # 判断是否存在五点
            for t in n.spec.taints or []:
                if any(p in t.key for p in taints_w):
                    issues.append({
                        'severity': 'critical',
                        'resource': f"Node/{n.metadata.name}",
                        'message': f"节点有压力污点: {t.key}",
                        'suggestion': "清理节点磁盘/内存，或扩容节点资源",
                    })
        return issues

    # 判断节点准备状态
    def _check_node_not_ready(self, resource: Dict) -> List[Dict]:
        issues = []
        for n in resource['nodes']:
            # 判断状态
            ready_cond = next((c for c in n.status.conditions if c.type == 'Ready'), None)
            if ready_cond and ready_cond.status != 'True':
                issues.append({
                    'severity': 'critical',
                    'resource': f"Node/{n.metadata.name}",
                    'message': f"节点状态异常: {ready_cond.reason or 'NotReady'}",
                    'suggestion': "检查节点 kubelet 状态、网络连通性、系统资源",
                })
        return issues


    # 给resource的资源列表
    def _list_pods(self, namespace: Optional[str]):
        if namespace:
            return self.core_v1.list_namespaced_pod(namespace).items
        return self.core_v1.list_pod_for_all_namespaces().items

    def _list_deployments(self, namespace: Optional[str]):
        if namespace:
            return self.apps_v1.list_namespaced_deployment(namespace).items
        return self.apps_v1.list_deployment_for_all_namespaces().items

    def _list_services(self, namespace: Optional[str]):
        if namespace:
            return self.core_v1.list_namespaced_service(namespace).items
        return self.core_v1.list_service_for_all_namespaces().items

    def _list_endpoints(self, namespace: Optional[str]):
        if namespace:
            return self.core_v1.list_namespaced_endpoints(namespace).items
        return self.core_v1.list_endpoints_for_all_namespaces().items

    def _list_nodes(self):
        return self.core_v1.list_node().items
