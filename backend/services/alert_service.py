# 该模块是后端数据库处理，路由接收到前端请求后，到该模块对数据进行处理
"""
1. 将数据列表返回给前端
2. 将数据中的告警进行处理更新
"""

"""
架构图
1. 获取告警历史记录
前端 → GET /api/alerts?limit=100&status=OPEN
         ↓
    routers/alerts.py
         ↓
    alert_service.get_alerts(100, "OPEN")
         ↓
    查数据库 alert_history 表
         ↓
    返回列表给前端
    
2. 解决告警
前端 → POST /api/alerts/resolve {"alert_id": 5}
        ↓
    routers/alerts.py
        ↓
    alert_service.resolve_alert(5, "admin")
        ↓
    更新数据库 alert_history 表
         ↓
    返回成功信息
    
"""
from typing import List, Dict

from models.database import get_db


class AlertService:
    def get_alert(self, limit: int = 100, status: str = None) -> List[Dict]:
        # 创建游标简历链接（连接database）
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                if status:
                    # 查询alter_history表的告警数据（历史数据），这个可以指定状态
                    cursor.execute(
                        "SELECT * FROM alert_history WHERE status=%s ORDER BY triggered_at DESC LIMIT %s",
                        (status, limit))
                else:
                    cursor.execute(
                        "SELECT * FROM alert_history ORDER BY triggered_at DESC LIMIT %s",
                        (limit,))
                # 输出数据
                rows = cursor.fetchall()
                # 通过r遍历上面的rows，然后转换格式，因为有些字段无法直接呈现给前端，转换为str类型
                return [{
                    "id": r["id"], "resource": r["resource"], "value": r["value"],
                    "threshold": r["threshold"], "node": r["node"],
                    "ai_advice": r["ai_advice"], "status": r["status"],
                    "raw_count": r.get("raw_count", 1),
                    "is_false_positive": r.get("is_false_positive", 0),
                    "triggered_at": str(r["triggered_at"]),
                    "resolved_at": str(r["resolved_at"]) if r["resolved_at"] else None,
                    "resolved_by": r["resolved_by"],
                } for r in rows]
        finally:
            conn.close()

    # 更新告警参数方法
    def resolve_alert(self, alert_id: int, resolved_by: str) -> Dict:
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                # 更新解决记录
                cursor.execute(
                    "UPDATE alert_history SET status='RESOLVED', resolved_at=NOW(), resolved_by=%s WHERE id=%s",
                    (resolved_by, alert_id))

                if cursor.rowcount == 0:
                    return {'message': '告警不存在'}
                return {'message': f'告警#{alert_id}已标记为解决'}
        finally:
            conn.close()
