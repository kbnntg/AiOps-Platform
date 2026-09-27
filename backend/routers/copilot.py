# 用户在对话框中的请求
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from core.security import verity_token
from models.schemas import ChatRequest, ExecuteConfirmRequest
from services.audit_service import record_audit
from services.copilot_service import CopilotService
from services.copilot_tools import TOOL_SCAL, ToolExecutor

router = APIRouter(prefix='/api/copilot', tags=['Copilot'])
svc = CopilotService()


# 创建请求路由,AI读操作路由
@router.post('/chat')
# 因为是SSE返回,需要用中继函数
async def chat(req: ChatRequest, user: dict = Depends(verity_token)):
    # AI Copilot对话接口
    # 把history从pydantic模型转换为普通字典类型
    history = None
    if req.history:
        history = [{"role": m.role, "content": m.content} for m in req.history]

    # 定义异步生成器,把service的输出逐条yield出去
    async def event_stream():
        try:
            async for chunk in svc.chat(req.message, history):
                yield chunk
        except Exception as e:
            yield f'data: {{"type": "error", "content": "{str(e)}"}}\n\n'

    # 返回SSE相应
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


# 用户点击确认框，同意AI执行操作路由
@router.post('/execute')
def execute_confirmed(
        req: ExecuteConfirmRequest,
        user: dict = Depends(verity_token),
):
    # 用户确认，先判断req.tool是否在工具集中
    if req.tool not in TOOL_SCAL:
        raise HTTPException(status_code=400, detail=f'{req.tool}没有这个')

    # 执行操作
    executor = ToolExecutor()
    result = executor.execute_write(req.tool, req.arguments)

    # 获取特定服务【不要用硬编码】
    arguments = req.arguments or {}
    resource_name = arguments.get('name', 'unknown')
    namespace = arguments.get('namespace', 'default')

    # 写审计日志
    record_audit(
        username=user["username"],  # "admin"
        action=f"COPILOT_{req.tool.upper()}",  # 特殊前缀
        resource_type="Copilot",
        resource_name=resource_name,
        namespace=namespace,
        details={
            "source": "ai_copilot",
            "tool": req.tool,
            "arguments": arguments
        },
    )

    # 返回结果
    return {'result': result}


# 给前端看的
@router.get('/tools')
def list_tools(user: dict = Depends(verity_token)):
    # 返回当前 Copilot 支持的所有工具（用于前端展示）
    from services.copilot_tools import TOOL_SCHEMAS
    return [
        {
            "name": t["function"]["name"],
            "description": t["function"]["description"],
        }
        for t in TOOL_SCHEMAS
    ]
