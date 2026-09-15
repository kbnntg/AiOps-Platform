# AI分析模块
import os

from openai import OpenAI


# 定义分析模块
def analyze_logs(logs: str, pod_name: str) -> str:
    """调用大模型分析日志，返回 Markdown 格式的分析结果"""
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("API_URL", "https://api.deepseek.com/v1")
    # 日志分析不需要深度推理，用便宜的 chat 模型
    model_name = os.getenv("LOG_MODEL_NAME", "deepseek-chat")

    if not api_key:
        return "未配置 API_KEY，无法进行 AI 分析"

    if not logs or not logs.strip():
        return "没有日志可供分析"

    # 日志太长时截断（保留最新的部分）
    if len(logs) > 8000:
        logs = logs[-8000:]

    prompt = f"""你是一个资深 SRE（站点可靠性工程师）。以下是 Kubernetes Pod `{pod_name}` 的日志片段：{logs} 请分析这段日志，输出以下三部分（Markdown 格式）：

## 问题摘要
列出日志中的关键错误、异常、警告（如果没有异常，说明运行正常）

## 可能原因
推断最可能导致这些问题的根因（如果日志正常，说明无需处理）

## 排查建议
给出 3-5 条具体的排查步骤（可执行的命令或操作）

要求：
- 只基于日志内容分析，不确定的地方明确说"日志中未体现"
- 命令要具体，例如给出 kubectl、top、jstat 等实际可执行的操作
- 不要寒暄，直接给结论
"""

    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=1024,
            timeout=60
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f'AI分析失败：{e}'
