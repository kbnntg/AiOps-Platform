"""
新建拓扑服务 → 新建路由 → 注册路由 → 测试接口
"""
from typing import Optional, Dict, List

from kubernetes import client

from services.k8s_service import K8sService

# 这个模块是从 Kubernetes 资源关系自动推导服务拓扑（Topology），输出节点（nodes）和边（edges）给前端画图用
# 层级：Ingress → Service → Pod ← ReplicaSet ← Deployment
"""
Ingress 通过 backend 指向 Service

Service 通过 selector 选中 Pod

Pod 的 owner 是 ReplicaSet

ReplicaSet 的 owner 是 Deployment
"""


# 一、K8s 服务拓扑推导：从 K8s 资源关系中构建节点和边
class TopologyService:
    """从K8s的Api中获取服务拓扑关系"""

    def __init__(self):
        self.k8s = K8sService()
        # pod
        self.core_v1 = self.k8s.core_v1
        # deployment控制器啥的
        self.app_v1 = self.k8s.apps_v1
        # ingress
        self.network_v1 = client.NetworkingV1Api()

    # 主入口
    def get_topology(self, namespace: Optional[str] = None) -> Dict:
        # 推导指定命名空间（或全部）的服务拓扑
        nodes: List[Dict] = []
        edges: List[Dict] = []

        # 拉取所有资源
        deployments = self._list_deployments(namespace)
        replicasets = self._list_replicasets(namespace)
        pods = self._list_pods(namespace)
        services = self._list_services(namespace)
        ingresses = self._list_ingresses(namespace)

        # 建立REplicasSet -》 Deployment映射
        """
        因为pod的owner是Replicaset，REplicasSet的owner才是Deployment，得先映射一下
        """

        # 先定义空字典
        rs_to_deploy = {}
        # 用rs遍历获取到的replicasets资源
        for rs in replicasets:
            # 取 ReplicaSet 的 ownerReferences
            owner_refs = rs.metadata.owner_references or []
            # 用ref遍历owner_refs采集到的信息
            for ref in owner_refs:
                # 如果类型是Deployment就将Deployment的名字赋值给rs.metadata,uid中
                if ref.kind == 'Deployment':
                    rs_to_deploy[rs.metadata.uid] = ref.name

                    """
                    ReplicaSet "nginx-5dc74f67cc" 的 ownerReferences 里写着：
                    kind: Deployment
                    name: nginx
                    uid: <deployment的UID>

                    但我们存的是 ReplicaSet 自己的 UID → Deployment 名字
                    """
        # 构建Deployment节点
        # d用来遍历获取到的deployment列表
        for d in deployments:
            nodes.append({
                # 在node字段中追加以下字段
                'id': self._id('deploy', d.metadata.namespace, d.metadata.name),
                'name': d.metadata.name,
                'type': 'Deployment',
                'namespace': d.metadata.namespace,
                'health': self._deployment_health(d),
                'detail': {
                    'replicas': d.spec.replicas or 0,
                    'ready_replicas': d.status.ready_replicas or 0,
                    'images': [c.image for c in (d.spec.template.spec.containers or [])],
                },
            })

        # 构建pod节点与Deployment映射→pod的边
        for p in pods:
            pod_id = self._id('pod', p.metadata.namespace, p.metadata.name)
            nodes.append({
                'id': pod_id,
                'name': p.metadata.name,
                'type': 'Pod',
                'namespace': p.metadata.namespace,
                'health': self._pod_health(p),
                'detail': {
                    'node': p.spec.node_name,
                    'ip': p.status.pod_ip,
                    'phase': p.status.phase,
                    'restarts': sum(c.restart_count for c in (p.status.container_statuses or [])),
                },
            })
            # 通过owner_references找到Deployment
            owner_refs = p.metadata.owner_references or []
            for ref in owner_refs:
                if ref.kind == 'ReplicaSet':
                    dep_name = rs_to_deploy.get(ref.uid)
                    if dep_name:
                        edges.append({
                            'source': self._id('deploy', p.metadata.namespace, dep_name),
                            'target': pod_id,
                            'type': 'owns',
                        })
        # 构建Service节点建立Service与pod的映射
        for s in services:
            svc_id = self._id('svc', s.metadata.namespace, s.metadata.name)
            selector = s.spec.selector or {}

            # 找到与selector标签匹配的pod
            matched_pods = []
            for p in pods:
                # 如果pod与service不是一个命名空间就跳过本次循环
                if p.metadata.namespace != s.metadata.namespace:
                    continue
                # pod的标签
                labels = p.metadata.labels or {}

                if selector and all(labels.get(k) == v for k, v in selector.items()):
                    matched_pods.append(p)

            nodes.append({
                'id': svc_id,
                'name': s.metadata.name,
                'type': 'Service',
                'namespace': s.metadata.namespace,
                'health': self._service_health(matched_pods),
                'detail': {
                    'type': s.spec.type,
                    'cluster_ip': s.spec.cluster_ip,
                    'ports': [
                        {'port': port.port, 'target_port': str(port.target_port)}
                        for port in (s.spec.ports or [])
                    ],
                },
            })

            # 建立Service→pod
            for p in matched_pods:
                edges.append({
                    'source': svc_id,
                    'target': self._id('pod', p.metadata.namespace, p.metadata.name),
                    'type': 'selects',
                })

        # 构建Ingress节点建立Ingress到Service
        for ing in ingresses:
            ing_id = self._id('ing', ing.metadata.namespace, ing.metadata.name)
            nodes.append({
                'id': ing_id,
                'name': ing.metadata.name,
                'type': 'Ingress',
                'namespace': ing.metadata.namespace,
                'health': 'healthy',
                'detail': {
                    # 取出域名
                    'rules': [r.host for r in (ing.spec.rules or []) if r.host],
                },
            })

            # 解析Ingress的backend到service
            for rule in (ing.spec.rules or []):
                # http为rule中http参数
                http = rule.http
                if not http:
                    continue
                    # 用path去遍历rule中http的paths参数
                for path in (http.paths or []):
                    # 存储backend值
                    backend = path.backend
                    # 如果有backemd、name、service值才会追加到edges
                    if backend and backend.service and backend.service.name:
                        edges.append({
                            'source': ing_id,
                            'target': self._id('svc', ing.metadata.namespace, backend.service.name),
                            'type': 'routes',
                        })

        return {'nodes': nodes, 'edges': edges}

    def _deployment_health(self, dep):
        """判断 Deployment 健康度"""
        replicas = dep.spec.replicas or 0
        ready = dep.status.ready_replicas or 0
        if replicas == 0:
            return 'warning'
        if ready == replicas:
            return 'healthy'
        if ready == 0:
            return 'error'
        return 'warning'

    # 返回的ID格式
    def _id(self, param: str, namespace: str, name: str) -> str:
        return f'{param}-{namespace}-{name}'

    def _list_deployments(self, namespace: Optional[str]):
        if namespace:
            return self.app_v1.list_namespaced_deployment(namespace=namespace).items
        return self.app_v1.list_deployment_for_all_namespaces().items

    def _list_replicasets(self, namespace):
        if namespace:
            return self.app_v1.list_namespaced_replica_set(namespace=namespace).items
        return self.app_v1.list_replica_set_for_all_namespaces().items

    def _list_pods(self, namespace):
        if namespace:
            return self.core_v1.list_namespaced_pod(namespace).items
        return self.core_v1.list_pod_for_all_namespaces().items

    def _list_services(self, namespace):
        if namespace:
            return self.core_v1.list_namespaced_service(namespace).items
        return self.core_v1.list_service_for_all_namespaces().items

    def _list_ingresses(self, namespace):
        try:
            if namespace:
                return self.network_v1.list_namespaced_ingress(namespace).items
            return self.network_v1.list_ingress_for_all_namespaces().items
        except Exception:
            # 集群可能没有 Ingress 资源，或当前 SA 无权限
            return []

    def _pod_health(self, p) -> str:
        # 判断健康度
        phase = p.status.phase
        if phase in ('Failed', 'Unknown'):
            return 'error'
        if phase == 'Pending':
            return 'warning'
        status = p.status.container_statuses or []
        if not status:
            return 'warning'
        if all(s.ready for s in status):
            return 'healthy'
        return 'warning'

    def _service_health(self, matched_pods) -> str:
        if not matched_pods:
            return 'warning'
        if any(self._pod_health(p) == 'healthy' for p in matched_pods):
            return 'healthy'
        return 'warning'
