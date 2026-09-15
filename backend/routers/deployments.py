# 和Pods相类似，前端发送的Deployment操作进行管理
from fastapi import APIRouter, Depends, HTTPException

from core.security import verity_token
from models.schemas import ScaleRequest
from services.audit_service import record_audit
from services.k8s_service import K8sService

# 定义路由前缀与实例
router = APIRouter(prefix='/api/deployments', tags=['Deployment'])
k8s = K8sService()


# 列出当前deployment
@router.get('')
def get_deployments(namespace: str = "default", user: dict = Depends(verity_token)):
    return k8s.get_deployment(namespace=namespace)


# 扩/缩容
@router.post('/scale')
def scale(req: ScaleRequest, user: dict = Depends(verity_token)):
    try:
        # 模型类，前端发送的调用到scale_deployment中，步骤：前端→ScaleRequest模型类获取username、deployment、replicas→传入到scale_deployment函数中
        result = k8s.scale_deployment(req.namespace, req.deployment, req.replicas)
        record_audit(user['username'], "SCALE", "Deployment", req.deployment, req.namespace, {"replicas": req.replicas})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""
前端点击"扩容 nginx 到 3 个副本"
        ↓
POST /api/deployments/scale
请求头：Authorization: Bearer eyJ...
请求体：{"namespace": "privatization", "deployment": "nginx", "replicas": 3}
        ↓
FastAPI 校验请求体（ScaleRequest）
        ↓ 校验通过
require_admin 验证 token + 检查 role
        ↓ admin ✅
k8s.scale_deployment("privatization", "nginx", 3)
        ↓
K8s API 修改 Deployment 副本数
        ↓
K8s 自动创建/删除 Pod 以达到目标副本数
        ↓
record_audit("admin", "SCALE", "Deployment", "nginx", "privatization", {"replicas": 3})
        ↓ 写入数据库
返回 {"message": "nginx 已调整为 3 个副本"}
        ↓
前端显示"扩容成功"，刷新 Deployment 列表
"""
