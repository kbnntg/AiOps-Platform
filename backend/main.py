# 一切路由的入口
import asyncio
from concurrent.futures import ThreadPoolExecutor

import fastapi
import jwt
from fastapi import Query, WebSocket
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect

from core.config import settings
from routers import auth, pods, deployments, metrics, alerts, audit, topology, copilot

_executor = ThreadPoolExecutor(max_workers=4)

# 创建应用
app = fastapi.FastAPI(
    title='Aiops运管平台',
    version='1.0.0'
)

# 创建跨域，不然前端发起的请求都会拦截
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产allow_origins=["https://aiops.example.com"]   # ← 只允许这一个来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 把所有路由拿过来
app.include_router(auth.router)
app.include_router(pods.router)
app.include_router(deployments.router)
app.include_router(metrics.router)
app.include_router(alerts.router)
app.include_router(audit.Router)
app.include_router(topology.router)
app.include_router(copilot.router)


# 全部拿到app上


# 创建健康检查
@app.get("/api/health")
def health():
    return {"status": "healthy"}


# 这个是实时日志流——WebSocket
@app.websocket('/api/ws/pods/{namespace}/{name}/logs')
async def ws_pod_logs(
        websocket: WebSocket,
        namespace: str,
        name: str,
        token: str = Query(...),
        tail_lines: int = Query(100),
):
    # 1. 验证 token
    try:
        jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception as e:
        await websocket.close(code=1008, reason=f"认证失败：{e}")
        return

    await websocket.accept()

    from services.k8s_service import K8sService, get_pod_logs_stream

    k8s = K8sService()
    loop = asyncio.get_event_loop()
    last_log = ""

    try:
        while True:
            # 2. 在线程池里执行同步阻塞调用（不阻塞事件循环）
            try:
                current_log = await asyncio.wait_for(
                    loop.run_in_executor(
                        _executor, get_pod_logs_stream,
                        k8s.core_v1, namespace, name, tail_lines
                    ),
                    timeout=10,
                )
            except asyncio.TimeoutError:
                await websocket.send_text("[WARN] 读取日志超时，重试中...\n")
                await asyncio.sleep(3)
                continue

            # 3. 只推送新增部分
            if current_log != last_log:
                if last_log and current_log.startswith(last_log):
                    # 追加模式：只发新增部分
                    new_part = current_log[len(last_log):]
                else:
                    # 日志被轮转或过长，直接发全部
                    new_part = current_log

                if new_part:
                    await websocket.send_text(new_part)

                last_log = current_log

            # 4. 每 2 秒轮询一次
            await asyncio.sleep(2)

    except WebSocketDisconnect:
        print(f'[WebSocket] 客户端断开: {namespace}/{name}')
    except Exception as e:
        try:
            await websocket.send_text(f"[ERROR] {e}\n")
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
