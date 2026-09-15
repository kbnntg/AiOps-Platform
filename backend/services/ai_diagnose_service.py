# AI对多混元数据数据进行分析
"""
1. 通过定义函数接受各查询语句返回结果，把 Prometheus 时序数据格式化为 AI 可读的文本摘要
2。 接受日志进行截取
3. 接受事件
4. 接受告警
5. AI进行分析

"""
import os

from openai import OpenAI


# 定义告警参数
def format_metrics_for_ai(cpu_data: list, mem_data: list, disk_data: list, node_name: str) -> str:
    # 接受时序，定义一个空列表
    lines = []

    # 各组件参数传到这里处理，截取节点的资源值
    def summarize(data: list, metric_label: str):
        for r in data:
            # 节点
            instance = r.get("metric", {}).get("instance", "unknown")
            values = r.get('values', [])  # 这个是资源值
            if not values:
                continue
            # 截取值，最大、当前、平均追加到列表中
            nums = [float(v[1]) for v in values]
            curr = nums[-1]
            max_v = max(nums)
            avg_v = sum(nums) / len(nums)
            lines.append(
                f"{metric_label} [{instance}]: 当前 {curr:.1f}%, "
                f"峰值 {max_v:.1f}%, 均值 {avg_v:.1f}%"
            )

    # 调用，这个值是从pods里传过来  路径pods→ai_diagnose_service→summarize
    summarize(cpu_data, "CPU")
    summarize(mem_data, "内存")
    summarize(disk_data, "磁盘")

    if not lines:
        return "无可用指标数据"
    return "\n".join(lines)

    # 获取事件


def format_events_for_ai(events: list) -> str:
    # 格式化k8s事件问问本
    if not events:
        return '无事件'
    return '\n'.join([
        f"[{e.get('type', '?')}] {e.get('reason', '?')}: {e.get('message', '')}"
        for e in events
    ])


# 获取告警记录
def format_alert_for_ai(alerts: list) -> str:
    # 获取
    if not alerts:
        return '没有告警记录'
    return "\n".join([
        f"[{a.get('triggered_at', '?')}] {a.get('node', '?')} "
        f"{a.get('resource', '?')} 使用率 {a.get('value', '?')}% "
        f"(阈值 {a.get('threshold', '?')}%)"
        for a in alerts
    ])


# AI告警
def diagnose_pod(signals: dict) -> str:
    """多信号融合根因诊断，返回 Markdown 格式的分析结果"""
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("API_URL", "https://api.deepseek.com/v1")
    model_name = os.getenv("DIAGNOSE_MODEL_NAME", "deepseek-chat")

    if not api_key:
        return "未配置 API_KEY，无法进行 AI 诊断"

    prompt = f"""你是一个资深 SRE 和 Kubernetes 专家。现在需要对一个 Pod 进行综合故障诊断。

请基于以下**四类信号**交叉验证，推断最可能的根因，并给出可执行的排查建议。

## 信号 1：Prometheus 指标（最近 1 小时，节点级）
{signals.get('metrics_text', '无指标数据')}

## 信号 2：Pod 日志（最后 200 行）
{signals.get('logs', '无日志')}


## 信号 3：Kubernetes 事件
{signals.get('events_text', '无事件')}

## 信号 4：历史告警记录（最近 10 条）
{signals.get('alerts_text', '无历史告警')}

---

请严格按以下 Markdown 格式输出：

## 综合诊断
用 2-3 句话概括当前 Pod 的状态和最主要的问题。

## 信号交叉分析
逐条分析四类信号分别说明了什么，以及它们之间是否存在因果关联。

## 根因推断
给出最可能的根因（如果信号不足以确定，明确说明）。

## 排查建议
给出 3-5 条可执行的排查步骤，命令要具体（kubectl、内存分析、网络检查等）。

## 风险评估
说明问题的严重程度（严重 / 警告 / 正常），以及是否需要立即介入。

要求：
- 不要寒暄，直接输出结论
- 信号不足时明确说"日志中未体现"，不要编造
- 如果四类信号都正常，说明"Pod 运行健康，无需处理"
- 命令要能直接复制执行
- 注意：指标是节点级的，不能直接等同于 Pod 级指标，分析时要说明这一点
"""

    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            timeout=120,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"AI 诊断失败: {e}"
