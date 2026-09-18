import os
from openai import OpenAI


def ai_monitor(resource, current_value, threshold, context_data):
    api_key = os.getenv('API_KEY')
    base_url = os.getenv('API_URL', 'https://api.deepseek.com/v1')
    model_name = os.getenv('MODEL_NAME', 'deepseek-reasoner')

    if not api_key:
        return None

    prompt = f"""
    你是一个系统运维专家。当前监控告警如下：
    - 资源类型：{resource}
    - 当前使用率：{current_value}%
    - 告警阈值：{threshold}%

    以下是最近10条该资源的历史数据（时间戳, 使用率）：
    {context_data}

    请分析可能的原因，并给出具体的排查步骤和解决建议。
    输出格式：简要说明原因，然后列出步骤。
    """

    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            extra_body={"thinking": {"type": "enabled"}},
            timeout=240
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"LLM 分析失败: {e}")
        return None


def ai_aggregate(alerts: list) -> str:
    """
    告警聚合分析：把多条告警一起交给大模型，推断共同根因
    """
    api_key = os.getenv('API_KEY')
    base_url = os.getenv('API_URL', 'https://api.deepseek.com/v1')
    model_name = os.getenv('MODEL_NAME', 'deepseek-chat')

    if not api_key:
        return None

    if not alerts:
        return None

    # 格式化为文本
    alert_lines = []
    for a in alerts:
        alert_lines.append(
            f"- [{a['timestamp']}] {a['node']} {a['resource']} "
            f"当前 {a['value']}% (阈值 {a['threshold']}%)"
        )
    alert_text = "\n".join(alert_lines)

    prompt = f"""你是一个资深 SRE。以下是过去 {len(alerts)} 条告警记录：

{alert_text}

请分析这些告警：

1. **共同根因**：这些告警是否存在共同的根因？如果有，明确指出。
2. **关联分析**：不同节点/资源之间有什么关联？
3. **排查优先级**：建议先排查什么？
4. **操作建议**：给出 3-5 条可执行的排查命令。

输出格式：简洁的 Markdown，直接给结论。
如果无法确定共同根因，说明"可能是独立故障"，并分别给出建议。
"""

    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            timeout=120
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"AI 聚合分析失败: {e}")
        return None
