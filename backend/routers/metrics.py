# 接收前端请求发送监控指标、列出namespace、node节点
from fastapi import APIRouter, Depends, Query

from core.security import verity_token
from services.k8s_service import K8sService
from services.prometheus_service import PrometheusService

# 创建路由
router = APIRouter(prefix='/api/metrics', tags=['Metrics'])
# 创建实例
k8s = K8sService()
prom = PrometheusService()


# 创建列出namespace函数
@router.get('/namespaces')
def list_namespaces(user: dict = Depends(verity_token)):
    return k8s.list_namespace()


# 列出node
@router.get('/nodes')
def nodes(user: dict = Depends(verity_token)):
    return prom.get_current_node()


# 获取cpu指标
@router.get('/cpu')
def cpu(hour: int = Query(1, ge=1, le=168), user: dict = Depends(verity_token)):
    return prom.query_range("CPU_use_percent", hour)

# 获取memory指标
@router.get('/memory')
def memory(hour: int = Query(1, ge=1, le=168), user: dict = Depends(verity_token)):
    return prom.query_range("Free_use_percent", hour)

# 获取cpu指标
@router.get('/disk')
def disk(hour: int = Query(1, ge=1, le=168), user: dict = Depends(verity_token)):
    return prom.query_range("Disk_use_percent", hour)

"""
前端打开 Dashboard 页面
        ↓
并发发三个请求：
  1. GET /api/metrics/current      → 拿当前状态卡片数据
  2. GET /api/metrics/cpu?hours=1  → 拿 CPU 趋势
  3. GET /api/metrics/memory?hours=1 → 拿内存趋势
        ↓
每个请求都经过：
  get_current_user 验证 token → 调用对应的服务 → 返回数据
        ↓
前端拿到数据后：
  - 当前状态：渲染节点卡片
  - CPU 趋势：用 ECharts 画折线图
  - 内存趋势：用 ECharts 画折线图
"""
