# 拓扑联系的请求
from typing import Optional

from fastapi import APIRouter, Query, Depends, HTTPException

from core.security import verity_token
from services.topology_service import TopologyService

router = APIRouter(prefix='/api/topology', tags=['Topology'])
svc = TopologyService()


@router.get('')
def get_topology(namespace: Optional[str] = Query(None), user: dict = Depends(verity_token), ):
    try:
        return svc.get_topology(namespace)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'拓扑推到失败:{e}')
