import requests


def _send(url: str, message: str):
    """统一的发送函数（内部用）"""
    header = {"Content-Type": "application/json"}
    data = {
        "msgtype": "text",
        "text": {"content": message}
    }
    try:
        response = requests.post(url=url, headers=header, json=data, timeout=10)
        if response.status_code == 200:
            print('发送成功')
        else:
            print(f'发送失败，状态码: {response.status_code}')
    except Exception as e:
        print(f'没发送过去: {e}')


def log_alter(url, system_time, resource, use, advice=None):
    """单条告警发送"""
    if not url:
        print("未配置 Webhook，跳过告警发送")
        return

    message = f'当前系统时间{system_time},设备[{resource}]使用率超过{use}%'
    if advice:
        message += f"\n\n🤖 AI 分析建议：\n{advice}"

    _send(url, message)


def log_alter_aggregated(url, alerts: list, advice: str = None):
    """聚合告警发送"""
    if not url:
        print("未配置 Webhook，跳过告警发送")
        return

    # 汇总告警信息
    lines = [f"⚠️ 告警聚合：{len(alerts)} 条告警"]
    lines.append("")
    for a in alerts[:10]:    # 最多展示前 10 条
        lines.append(f"• {a['node']} {a['resource']} {a['value']}% (阈值 {a['threshold']}%)")
    if len(alerts) > 10:
        lines.append(f"• ... 还有 {len(alerts) - 10} 条")

    message = "\n".join(lines)

    if advice:
        message += f"\n\n🤖 AI 根因分析：\n{advice}"
    else:
        message += "\n\n（AI 分析未启用或失败）"

    _send(url, message)
