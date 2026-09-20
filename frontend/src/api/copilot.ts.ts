// Copilot API：因为用 SSE，不能用 axios（不支持流式读取），改用 fetch
export async function* streamChat(
  message: string,
  history: Array<{ role: string; content: string }> = []
): AsyncGenerator<any, void, unknown> {
  const token = localStorage.getItem('token')

  const resp = await fetch('/api/copilot/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message, history }),
  })

  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}: ${resp.statusText}`)
  }

  const reader = resp.body!.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // SSE 格式：每条消息以 \n\n 分隔
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''    // 最后一段可能不完整，留到下次

    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data:')) continue

      const jsonStr = line.slice(5).trim()   // 去掉 "data:" 前缀
      if (!jsonStr) continue

      try {
        yield JSON.parse(jsonStr)
      } catch (e) {
        console.error('解析 SSE 消息失败:', jsonStr, e)
      }
    }
  }
}

export const getCopilotTools = () => {
  const token = localStorage.getItem('token')
  return fetch('/api/copilot/tools', {
    headers: { Authorization: `Bearer ${token}` },
  }).then((r) => r.json())
}