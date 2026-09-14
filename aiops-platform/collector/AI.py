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
