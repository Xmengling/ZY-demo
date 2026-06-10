/** 去掉 AI 回复中的 Markdown 符号，便于阅读 */
export function formatAiReply(text) {
  if (!text) return ''
  let s = String(text).replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim()

  s = s.replace(/^#{1,6}\s*/gm, '')
  s = s.replace(/\*\*(.+?)\*\*/g, '$1')
  s = s.replace(/__(.+?)__/g, '$1')
  s = s.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '$1')
  s = s.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
  s = s.replace(/^>\s?/gm, '')
  s = s.replace(/^[-*+]\s+/gm, '· ')
  s = s.replace(/^[-*_]{3,}\s*$/gm, '')
  s = s.replace(/`([^`]+)`/g, '$1')
  s = s.replace(/\n{3,}/g, '\n\n')
  s = s
    .split('\n')
    .map((line) => line.trim())
    .join('\n')

  return s.trim()
}
