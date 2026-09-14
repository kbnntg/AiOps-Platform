# 接收前端发来的pod操作请求，对pod进行一系列的管理
# 列出pod、列出指定pod的logs、获取指定pod的事件、删除指定pod
from fastapi import APIRouter, Query, Depends, HTTPException

from core.security import verity_token, verity_role
from services.audit_service import record_audit
from services.k8s_service import K8sService

# 创建路由
router = APIRouter(prefix='/api/pods', tags=['Pods'])
# 调用K8s的服务类模块，创建一个实例
k8s = K8sService()


# 创建列出Pod的方法,直接/api/pods就能获取
@router.get('')
def list_pods(namespace: str = Query('default'), user: dict = Depends(verity_token)):
    return k8s.list_pods(namespace=namespace)


# 创建出获取指定pod日志的方法
@router.get('/{name}/logs')
def get_logs(namespace: str, name: str, tail_lines: int = Query(200, ge=10, le=10000),
             user: dict = Depends(verity_token)):
    try:
        logs = k8s.get_pod_log(namespace=namespace, name=name, tail_lines=tail_lines)
        # 下列这一行是记录用户操作日志→audit_service
        record_audit(user['username'], 'GET_LOGS', 'Pod', name, namespace=namespace)
        return {'logs': logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 创建获取指定pod的事件方法
@router.get('/{name}/event')
def get_events(namespace: str, name: str, user: dict = Depends(verity_token)):
    return k8s.get_pod_event(namespace, name=name)


# 创建删除pod的方法
@router.delete('/{name}')
def delete_pod(namespace: str, name: str, user: dict = Depends(verity_role)):
    result = k8s.delete_pod(namespace=namespace, name=name)
    # 记录操作
    record_audit(user['username'], "DELETE_POD", "Pod", name, namespace=namespace)
    return result


# AI分析请求
@router.post('/{name}/analyze')
def ai_search(
        namespace: str,
        name: str,
        tail_lines: int = Query(600, ge=10, le=2000),
        user: dict = Depends(verity_token),
):
    # 调用AI服务
    from services.ai_log_service import analyze_logs
    try:
        logs = k8s.get_pod_log(namespace=namespace, name=name, tail_lines=tail_lines)
        if not logs:
            return {"analysis": "该 Pod 没有日志输出"}
        result = analyze_logs(logs=logs, pod_name=name)
        record_audit(user['username'], 'AI_ANALYZE_LOG', 'Pod', name, namespace=namespace)
        return {"analysis": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
