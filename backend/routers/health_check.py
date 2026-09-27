from typing import Optional

from fastapi import APIRouter, Query, Depends, HTTPException

from core.security import verity_token
from services.healthy_check_service import HealthCheckService

router = APIRouter(prefix='/api/health-check', tags=['HealthCheck'])
svc = HealthCheckService()


# 创建接口
@router.get('')
def get_health(namespace: Optional[str] = Query(None), user: dict = Depends(verity_token), ):
    try:
        return svc.run_check(namespace)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'巡检失败: {e}')
