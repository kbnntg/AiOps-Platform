# 接收前端发送查询告警记录与更新告警记录
from typing import Optional

from fastapi import APIRouter, Query, Depends

from core.security import verity_token
from models.schemas import AlertResolveRequest
from services.alert_service import AlertService

# 创建路由
router = APIRouter(prefix='/api/alerts', tags=['Alerts'])
# 创建实例
svc = AlertService()


# 创建接收前端发送查询告警记录
@router.get('')
def list_alerts(limit: int = Query(100, ge=1, le=500), status: Optional[str] = None,
                user: dict = Depends(verity_token)):
    # 将前端发送的查询条目、状态返回给get_alert中处理
    return svc.get_alert(limit=limit, status=status)


# 创建前端更新告警记录操作
@router.post('/resolve')
def resolve(req: AlertResolveRequest, user: dict = Depends(verity_token)):
    return svc.resolve_alert(req.alter_id, user['username'])


"""
过程：
前端打开"告警历史"页面
        ↓
GET /api/alerts?limit=200
        ↓
get_current_user 验证 token
        ↓
svc.get_alerts(200, None)
        ↓
查数据库 alert_history 表
        ↓
返回告警列表

用户点击"标记已解决"
        ↓
POST /api/alerts/resolve
Body: {"alert_id": 5}
        ↓
require_admin 验证 token + 检查 role
        ↓ admin ✅
svc.resolve_alert(5, "admin")
        ↓
UPDATE alert_history SET status='RESOLVED', resolved_by='admin' WHERE id=5
        ↓
返回 {"message": "告警 #5 已标记为已解决"}
"""
