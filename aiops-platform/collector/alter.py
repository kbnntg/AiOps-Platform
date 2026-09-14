import requests


def log_alter(url, system_time, resource, use, advice=None):
    if not url:
        print("未配置 Webhook，跳过告警发送")
        return

    message = f'当前系统时间{system_time},设备[{resource}]使用率超过{use}%'
    if advice:
        message += f"\n\n🤖 AI 分析建议：\n{advice}"

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
