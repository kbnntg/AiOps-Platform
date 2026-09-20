# AI调用工具流进行处理
import json
import os
from typing import AsyncGenerator

from openai import OpenAI

from services.copilot_tools import ToolExecutor, TOOL_SCHEMAS

# 系统提示词：定义 AI 的角色和行为约束
SYSTEM_PROMPT = """你是 AIOps 智能运维助手，可以调用工具查询 Kubernetes 集群的真实数据。

回答规则：
1. 优先调用工具获取真实数据，不要凭记忆猜测
2. 引用数据时标注来源，格式如 [来源: list_pods]
3. 工具没有返回数据时，说明"未获取到数据"，不要编造
4. 使用简洁的中文回答，必要时用 Markdown 列表
5. 涉及删除、扩容等高危操作时，提示用户手动确认
"""


class CopilotService:
    # 从环境变量读取配置，初始化定义执行器的属性
    def __init__(self):
        self.api_key = os.getenv('API_KEY')
        self.base_url = os.getenv('API_URL', "https://api.deepseek.com/v1")
        self.model = os.getenv("COPILOT_MODEL_NAME", "deepseek-chat")
        self.executor = ToolExecutor()

    # 消息历史，系统提示词→用户输入→AI回复，有历史记录就加进来
    # 必须要用异步函数，SSE需要一步一步的将结果呈现给用户，可以看作是个进度条
    async def chat(self, user_message: str, history: list = None) -> AsyncGenerator[str, None]:
        if not self.api_key:
            yield self._sse({'type': 'error', 'content': '未配置API_KEY'})
            return

        # 1. 组装消息历史
        # 这个是接受系统提示词
        messages = [{"role": 'system', 'content': SYSTEM_PROMPT}]
        if history:
            # 有历史记录就加进来
            messages.extend(history)
        # 用户输入的
        messages.append({'role': 'user', 'content': user_message})

        # 2.初始化OpenAI客户端,AI的载体
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        # 3.Function Calling循环（最多5次，防止死循环）
        max_iterations = 5
        for iteration in range(max_iterations):
            try:
                response = client.chat.completions.create(
                    # 告诉AI啥模型、消息、调用哪个工具、是否自动调用工具、最多用多少Token、超时时间
                    model=self.model,
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                    tool_choice='auto',
                    max_tokens=20480,
                    timeout=600,
                )
            except Exception as e:
                yield self._sse({"type": 'error', 'content': f'AI调用失败: {e}'})
                return
            choice = response.choices[0]  # 只取最优解（第一个回答）
            assistant_message = choice.message  # AI回复消息对象，默认role是assistant
            """
            content：AI 的文本回答（可能为 None，如果 AI 选择调用工具）
            tool_calls：如果 AI 决定调用工具，这里会有工具调用信息（可能为 None）
            
            不调用工具：
                assistant_message = {
                    "role": "assistant",
                    "content": "重启最多的是 node-monitor-zq52h，重启了 3 次",
                    "tool_calls": None,
                }
                
            调用工具：
                assistant_message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                {
                        "id": "call_abc123",
                        "type": "function",
                        "function": {
                        "name": "list_pods",
                        "arguments": '{"namespace": "privatization"}',
            },
        }
    ],
}
            """
            # 检查AI是否调用工具，就是判断tool_calls有没有这个值
            tool_calls = assistant_message.tool_calls

            # 如果没有这就是最终答案
            if not tool_calls:
                content = assistant_message.content or ""
                yield self._sse({"type": "text", "content": content})
                yield self._sse({"type": "done"})
                return

            # 5. 有工具调用 → 把 AI 的请求加入历史
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            })

            # 有工具了就便利获取参数
            for tc in tool_calls:
                tool_name = tc.function.name    # 取出工具名，比如"name": "list_pods",
                # 那么tool_name就是list_pods然后传递到copilot_tool中的执行器中，再由执行器的handle获取传来的名称，在调用对应的方法

                # 解析参数（AI返回的是JSON字符串，需要转换）
                try:
                    arguments = json.loads(tc.function.arguments)
                except Exception:
                    arguments = {}

                # 推送进度：正在调用：xxx
                yield self._sse({
                    "type": "tool_start",
                    "tool": tool_name,
                    "arguments": arguments
                })

                # 执行工具，tool_name就传进copilot_tools的execute去，再在这个方法中根据传入的tool_name调用其他方法
                result = self.executor.execute(tool_name, arguments)

                # 推送工具结果
                yield self._sse({
                    "type": "tool_result",
                    "tool": tool_name,
                    "result": self._truncate_result(result),
                })

                # 吧工具结果加入消息历史（role必须是"tool"）
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })
        # 超过最大循环次数
        yield self._sse({
            'type': 'text',
            'content': "已到达最大工具调用次数，请换个方式提问。",
        })
        yield self._sse({'type': 'done'})

    def _sse(self, param: dict) -> str:
        # 把字典换为SSE格式的字符串
        return f'data: {json.dumps(param, ensure_ascii=False)}\n\n'

    def _truncate_result(self, result, max_len: int = 500):
        # 截断工具结果，避免推送太长
        s = json.dumps(result, ensure_ascii=False, default=str)
        if len(s) > max_len:
            return s[:max_len] + '...'
        return result


"""
假设用户要问有哪些Pod：
1. 组床message = [system, user]
2. 调用Deepseek（带者工具）
3. Deepseek返回 tool_cails=[list_pods]
4. SSE推送 type为tool_start tool为list_pods
5. 执行list_pods
6. SSE推送 type为tool_result result为..
7. 把AI请求 工具加入messages
8. 再掉用Deepseep(带完整历史)
9. Deepseek返回纯文本(没有tool_cails)
10. SSE 推送 type为text content为一些值
11. SSE推送done
完成
"""
