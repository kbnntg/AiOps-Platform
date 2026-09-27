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
    return svc.resolve_alert(req.alert_id, user['username'])


@router.get("/metrics")
def alert_metrics(user: dict = Depends(verity_token)):
    """告警治理量化指标"""
    from models.database import get_db
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 1. 原始告警总数（聚合告警的 raw_count 之和 + 单条告警的数量）
            cursor.execute("""
                SELECT 
                    COUNT(*) AS total_alerts,
                    SUM(raw_count) AS total_raw,
                    SUM(CASE WHEN is_false_positive = 1 THEN 1 ELSE 0 END) AS false_positives
                FROM alert_history
            """)
            row = cursor.fetchone()
            total_alerts = row['total_alerts'] or 0
            total_raw = row['total_raw'] or 0
            false_positives = row['false_positives'] or 0

            # 2. MTTR（已解决告警的平均恢复时间，单位秒）
            cursor.execute("""
                SELECT AVG(TIMESTAMPDIFF(SECOND, triggered_at, resolved_at)) AS mttr
                FROM alert_history
                WHERE resolved_at IS NOT NULL
            """)
            mttr_row = cursor.fetchone()
            mttr = int(mttr_row['mttr']) if mttr_row['mttr'] else 0

            # 3. 最近 7 天告警趋势
            cursor.execute("""
                SELECT DATE(triggered_at) AS day, COUNT(*) AS count
                FROM alert_history
                WHERE triggered_at > NOW() - INTERVAL 7 DAY
                GROUP BY DATE(triggered_at)
                ORDER BY day
            """)
            trend = cursor.fetchall()
            for t in trend:
                t['day'] = str(t['day'])

            # 计算压缩率
            compression_rate = round(total_raw / total_alerts, 2) if total_alerts > 0 else 0
            false_positive_rate = round(false_positives / total_alerts * 100, 1) if total_alerts > 0 else 0

            return {
                "total_alerts": total_alerts,  # 聚合后告警数
                "total_raw": total_raw,  # 原始告警数
                "compression_rate": compression_rate,  # 压缩率
                "false_positive_rate": false_positive_rate,  # 误报率 %
                "false_positives": false_positives,
                "mttr_seconds": mttr,  # MTTR（秒）
                "trend": trend,  # 最近 7 天趋势
            }
    finally:
        conn.close()


# 标记告警为误报
@router.post('/{alert_id}/false-positive')
def mark_false_positive(alert_id: int, user: dict = Depends(verity_token)):
    from models.database import get_db
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE alert_history SET is_false_positive=1 WHERE id=%s",
                (alert_id,)
            )
            if cursor.rowcount == 0:
                return {"message": "告警不存在"}
            return {"message": f"告警 #{alert_id} 已标记为误报"}
    finally:
        conn.close()


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
