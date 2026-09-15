# 这个就是前端管理员发起获取审计的请求
from fastapi import APIRouter, Query, Depends

from core.security import verity_token
from models.database import get_db

# 创建路由
Router = APIRouter(prefix='/api/audit', tags=['Audit'])


# 获取前端管理员发起的审计访问请求
@Router.get('')
def list_audit(limit: int = Query(100, ge=0, le=500), user: dict = Depends(verity_token)):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM operation_audit ORDER BY created_at DESC LIMIT %s", (limit,))
            # 输出查询记录
            rows = cursor.fetchall()
            for r in rows:
                if r.get("created_at"):
                    r["created_at"] = str(r["created_at"])
            return rows
    finally:
        conn.close()


"""
前端打开"审计日志"页面
        ↓
GET /api/audit?limit=200
请求头：Authorization: Bearer eyJ...
        ↓
require_admin 验证 token
        ↓ 是 admin
直接查数据库 operation_audit 表
        ↓
转换时间格式
        ↓
返回记录列表
        ↓
前端渲染表格
"""
