# 接收前端发来的pod操作请求，对pod进行一系列的管理
# 列出pod、列出指定pod的logs、获取指定pod的事件、删除指定pod
from fastapi import APIRouter, Query, Depends, HTTPException

from core.security import verity_token, verity_role
from models.database import get_db
from services.audit_service import record_audit
from services.k8s_service import K8sService
from services.prometheus_service import PrometheusService

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

# AI混合分析
@router.post('/{name}/diagnose')
def diagnose_pod_api(
        namespace: str,
        name: str,
        user: dict = Depends(verity_token),
):

    # 导入ai_diagnose_service
    from services.ai_diagnose_service import (
        diagnose_pod,
        format_alert_for_ai,
        format_events_for_ai,
        format_metrics_for_ai,
    )

    # 采集Prometheus指标
    try:
        metrics_text = '无指标数据'
        # 创建实例，用来接收组件参数到指定方法处理
        try:
            prom = PrometheusService()
            cpu_data = prom.query_range('CPU_use_percent', hout=1)
            mem_data = prom.query_range('Free_use_percent', hout=1)
            disk_data = prom.query_range('Disk_use_percent', hout=1)
            # 将各组件获取得到的值传递到ai+diagnose_service中
            metrics_text = format_metrics_for_ai(cpu_data=cpu_data, mem_data=mem_data, disk_data=disk_data, node_name=name)

        except Exception as e:
            metrics_text = f"指标获取失败{e}"

        # 获取日志
        logs = ""
        try:
            logs = k8s.get_pod_log(namespace=namespace, name=name, tail_lines=200)
            # 如果超过5000行取最新
            if len(logs) > 5000:
                logs = logs[-5000:]
        except Exception as e:
            logs = f"日志获取失败:{e}"

        # 获取事件
        events = ""
        try:
            events = k8s.get_pod_event(namespace=namespace, name=name)
        except Exception as e:
            pass
        event_text = format_events_for_ai(events=events)

        # 获取历史告警
        alerts = []
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT resource, value, threshold, node, triggered_at "
                    "FROM alert_history ORDER BY triggered_at DESC LIMIT 10"
                )
                alerts = cursor.fetchall()
        except Exception:
            pass
        finally:
            conn.close()
        alert_text = format_alert_for_ai(alerts)

        # ===== 调用 AI 诊断 =====
        signals = {
            "metrics_text": metrics_text,
            "logs": logs,
            "events_text": event_text,
            "alerts_text": alert_text,
        }
        result = diagnose_pod(signals)

        # ===== 记录审计 =====
        record_audit(user['username'], 'AI_DIAGNOSE', 'Pod', name, namespace=namespace)

        # ===== 返回结果 + 信号统计 =====
        return {
            "analysis": result,
            "signals": {
                "metrics": "✓" if metrics_text != "无指标数据" else "✗",
                "logs": "✓" if logs and "失败" not in logs[:20] else "✗",
                "events": len(events),
                "alerts": len(alerts),
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
