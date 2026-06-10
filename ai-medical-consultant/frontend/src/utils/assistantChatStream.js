/**
 * AI 问答流式接口（SSE）
 * @param {object} data - { session_id, message, images, case_context }
 * @param {object} handlers - { onStart, onToken, onDone, onError }
 * @param {AbortSignal} [signal]
 */
export async function assistantChatStream(data, handlers = {}, signal) {
  const token = localStorage.getItem('token')
  const res = await fetch('/api/v1/consult/assistant/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(data),
    signal
  })

  if (res.status === 401) {
    localStorage.removeItem('token')
    if (location.pathname !== '/login') location.href = '/login'
    throw Object.assign(new Error('未登录'), { response: { status: 401 } })
  }

  if (!res.ok) {
    let detail = 'AI 回复失败'
    try {
      const body = await res.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      /* ignore */
    }
    throw Object.assign(new Error(detail), { response: { status: res.status, data: { detail } } })
  }

  const reader = res.body?.getReader()
  if (!reader) throw new Error('流式响应不可用')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let boundary = buffer.indexOf('\n\n')
    while (boundary >= 0) {
      const chunk = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      boundary = buffer.indexOf('\n\n')

      for (const line of chunk.split('\n')) {
        if (!line.startsWith('data: ')) continue
        let payload
        try {
          payload = JSON.parse(line.slice(6))
        } catch {
          continue
        }
        if (payload.type === 'start') handlers.onStart?.(payload)
        else if (payload.type === 'token') handlers.onToken?.(payload.content || '')
        else if (payload.type === 'done') handlers.onDone?.(payload)
        else if (payload.type === 'error') {
          const err = new Error(payload.message || 'AI 回复失败')
          handlers.onError?.(err)
          throw err
        }
      }
    }
  }
}
