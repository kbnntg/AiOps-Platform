# 1. 把数据库的已解决告警传到chroma中
# 2. 获取知识库状态
# 3. 手动监所（前端调用）
# 4. 清空知识库
from fastapi import APIRouter, Depends

from core.security import verity_role, verity_token
from models.database import get_db

router = APIRouter(prefix='/api/rag', tags=['RAG'])


# 数据库传入chroma中
@router.post('/index')
def index_rag(user: dict = Depends(verity_role)):
    from services.rag_service import RagService
    conn = get_db()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, resource, value, threshold, node, ai_advice,
                        triggered_at, resolved_at
                FROM alert_history
                WHERE resolved_at IS NOT NULL
                ORDER BY triggered_at DESC
                LIMIT 1000
            """)
            # 只截取有解决的告警
            alerts = cursor.fetchall()
    finally:
        conn.close()

    if not alerts:
        return {'message': '没有已解决的警告', 'indexed': 0}
    rag = RagService()
    # 把解决的案例传到info_chroma中
    result = rag.info_chroma(alerts)
    return {
        "message": f"索引完成",
        "indexed": result["indexed"],
        "skipped": result["skipped"],
        "total_in_rag": rag.count_RAG(),
    }


# 检查知识库窗台
@router.get('/status')
def rag_status(user: dict = Depends(verity_token)):
    from services.rag_service import RagService
    rag = RagService()
    return {
        "count": rag.count_RAG(),
        "ready": rag.count_RAG() > 0,
    }


# 检索知识库
@router.post('/search')
def rag_search(query: str, top_k: int = 5, resource: str = None, user: dict = Depends(verity_token)):
    # 手动监所
    from services.rag_service import RagService
    rag = RagService()

    hits = rag.search(query=query, top_k=top_k, resource_filter=resource, th=0.4)
    return {"quert": query, "hits": hits}


# 清空数据库
@router.post('/clear')
def clear_rag(user: dict = Depends(verity_token)):
    from services.rag_service import RagService
    rag = RagService()
    rag.clear()
    return {'message': '知识库已清空'}
