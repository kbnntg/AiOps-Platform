# 该模块用来对k8s资源进行管理
"""
1. 通过创建一个类使用__new__来创建类属性，为什么要用new因为k8s每次都要重新创建实例的话会消耗大量资源，使用new每次到类属性时判断实例是否存在，不存在才实例化，存在就直接返回之前创建的
2. 创建列出pod的函数，接收self（就是类属性的）和namespace（用来列出指定命名空间pod），self.core_v1.list_namespace_pod(namespace=namespace)，遍历接收其值的变量返回到封装的format_pod函数里
3. 创建获取指定pod的函数，将值返给封装的format_pod里
4. 创建获取日志的函数，指定namespace、pod、活人获取行数，直接返回字符串
5. 创建删除指定pod的函数，指定namespace、name，返回为字典
6. 创建获取事件的函数，指定namespace、name返回List[Dict]
7. 创建格式化 Pod（私有方法）_format_pod(self, pod) -> Dict，statuses = pod.status.container_statuses or []获取当前pod的状态，or []代表pod可能不是running，这个方法意思就是只获取指定的字段，并转化为字典呈现给前端
8. 创建列出deployment的方法，注意使用apps_v1了，接受namspace值返回List[DIct]
9. 创建扩容pod副本数的方法
10. 创建列出namespace的方法
11. 创建列出node的方法
"""
import os
from typing import List, Dict

from kubernetes import config, client


# 导入模块

# 这个是流日志方法，实时更新日志
def get_pod_logs_stream(core_v1, namespace: str, name: str, tail_lines: int = 100):
    """
    返回生成器，逐行产出日志
    """
    return core_v1.read_namespaced_pod_log(
        name=name,
        namespace=namespace,
        tail_lines=tail_lines,
        timestamps=True,
    )


# 创建类、类属性使用__new__省的每一次都要重新创建实例的
class K8sService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            # 如果cls的实例为None，就执行创建
            cls._instance = super().__new__(cls)
            # 判断是集群内还是本地开发
            if os.getenv('KUBERNETES_SERVICE_HOST'):
                config.load_incluster_config()
            else:
                config.load_kube_config()
                # 创建两个客户端
                """
                core_v1	Pod、Service、Namespace、Node、Event
                apps_v1	Deployment、StatefulSet、DaemonSet
                """
            cls.core_v1 = client.CoreV1Api()
            cls.apps_v1 = client.AppsV1Api()
        return cls._instance

    # Pod的相关操作==============================
    # 创建列出所有pod的方法
    def list_pods(self, namespace: str = "default") -> List[Dict]:
        pods = self.core_v1.list_namespaced_pod(namespace=namespace)
        return [self._format_pod(p) for p in pods.items]

    # 创建出获取指定pod的方法
    def get_pod(self, namespace: str, name: str) -> Dict:
        pod = self.core_v1.read_namespaced_pod(namespace=namespace, name=name)
        return self._format_pod(pod)

    # 创建出获取指定pod日志的方法
    def get_pod_log(self, namespace: str, name: str, tail_lines: int = 100) -> str:
        # 直接返回字符串
        return self.core_v1.read_namespaced_pod_log(name=name, namespace=namespace, tail_lines=tail_lines,
                                                    timestamps=True)

    # 创建删除pod的方法
    def delete_pod(self, namespace: str, name: str) -> Dict:
        self.core_v1.delete_namespaced_pod(namespace=namespace, name=name)
        return {"message": f'pod{name}已删除'}

    # 创建获取pod事件的方法
    def get_pod_event(self, namespace: str, name: str) -> List[Dict]:
        events = self.core_v1.list_namespaced_event(
            namespace=namespace,
            field_selector=f"involvedObject.name={name}"
        )
        return [{
            # 返回指定的键值对
            "type": e.type,
            "reason": e.reason,
            "message": e.message,
            "time": str(e.metadata.creation_timestamp),
        } for e in events.items]

    # 创建接受pod固定字段的私有方法
    def _format_pod(self, pod) -> Dict:
        # 这个是获取各pod的运行状态，or []代表如果pod状态不为running的就返回空的
        statuses = pod.status.container_statuses or []
        return {
            # 只接受固定字段，这些都返回给前端
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": pod.status.phase,
            "node": pod.spec.node_name,
            "ip": pod.status.pod_ip,
            # 重启次数
            "restarts": sum(c.restart_count for c in statuses),
            "containers": [
                {"name": c.name, "image": c.image,
                 # 查看该状态的pod名是否与定义的pod名相同
                 # statuses 是 container_statuses，它的 s.name 就是容器名。
                 # c 是 pod.spec.containers 里的容器定义，c.name 也是容器名。

                 "ready": next((s.ready for s in statuses if s.name == c.name), False)}
                for c in (pod.spec.containers or [])
            ],
            "created_at": str(pod.metadata.creation_timestamp),
        }

    # Deployment===============
    # 创建列出deployment的方法
    def get_deployment(self, namespace: str) -> List[Dict]:
        dep = self.apps_v1.list_namespaced_deployment(namespace)
        return [{
            "name": d.metadata.name,
            "namespace": d.metadata.namespace,
            "replicas": d.spec.replicas or 0,
            "ready_replicas": d.status.ready_replicas or 0,
            "images": [c.image for c in (d.spec.template.spec.containers or [])],
        } for d in dep.items]

    # 创建扩/缩容副本方法
    def scale_deployment(self, namespace: str, name: str, replicas: int) -> Dict:
        body = {"spec": {"replicas": replicas}}
        self.apps_v1.patch_namespaced_deployment_scale(name=name, namespace=namespace, body=body)
        return {"message": f'{name}副本以调整为{replicas}个'}

    # 通用=============
    def list_namespace(self) -> List[str]:
        ns = self.core_v1.list_namespace()
        return [n.metadata.name for n in ns.items]

    # 获取node节点
    def list_nodes(self) -> List[Dict]:
        nodes = self.core_v1.list_node()
        return [{
            'name': n.metadata.name,
            "status": n.status.conditions[-1].type if n.status.conditions else "Unknown",
        } for n in nodes.items]
