/** 去掉 AI 回复中的 Markdown 符号，便于阅读 */

const EMPTY_SECTION_BODIES = new Set([
  '（本节略）',
  '本节略',
  '暂无需追问',
  '暂无需追问。',
  '暂无对比条目',
  '知识库中暂无对比条目',
  '知识库中暂无对比条目。',
  '当前知识库未检索到胡希恕讲稿相关内容',
  '当前知识库未检索到胡希恕讲稿相关内容。',
  '当前知识库未检索到李冠杰讲稿相关内容',
  '当前知识库未检索到李冠杰讲稿相关内容。'
])

const OPTIONAL_SECTION_KEYWORDS = ['类方鉴别', '建议追问', '胡希恕讲稿摘要', '李冠杰讲稿摘要']
const CN_NUMS = '一二三四五六七八九十'
const SECTION_SPLIT_RE =
  /(?=^[一二三四五六七八九十]+[、．.]\s*.+?[：:]|^(?:类方鉴别|建议追问|胡希恕讲稿摘要|李冠杰讲稿摘要)[：:])/m
const SECTION_MATCH_RE =
  /^([一二三四五六七八九十]+[、．.]\s*.+?[：:]|(?:类方鉴别|建议追问|胡希恕讲稿摘要|李冠杰讲稿摘要)[：:])([\s\S]*)/

function normalizeSectionBody(body) {
  return String(body || '').trim().replace(/\s+/g, '').replace(/[。.]+$/g, '')
}

function isEmptySectionBody(body) {
  const text = String(body || '').trim()
  if (!text) return true
  const compact = normalizeSectionBody(text)
  if (EMPTY_SECTION_BODIES.has(compact)) return true
  for (const marker of ['（本节略）', '暂无需追问', '暂无对比条目', '未检索到胡希恕', '未检索到李冠杰']) {
    if (text.includes(marker) && compact.length <= marker.replace(/\s+/g, '').length + 12) {
      return true
    }
  }
  if (text.includes('未检索到') && (text.includes('胡希恕') || text.includes('李冠杰')) && compact.length < 60) {
    return true
  }
  return false
}

function isOptionalSection(title) {
  return OPTIONAL_SECTION_KEYWORDS.some((keyword) => title.includes(keyword))
}

function renumberReplySections(text) {
  if (!text) return ''
  const parts = text.split(SECTION_SPLIT_RE)
  const blocks = []

  for (const part of parts) {
    const chunk = part.trim()
    if (!chunk) continue
    const match = chunk.match(SECTION_MATCH_RE)
    if (!match) {
      blocks.push({ title: '', body: chunk })
      continue
    }
    const header = match[1]
    const body = (match[2] || '').trim()
    const title = header.split('：')[0].split(':')[0].replace(/^[一二三四五六七八九十]+[、．.]\s*/, '')
    blocks.push({ title, body })
  }

  const renumbered = []
  let idx = 0
  for (const block of blocks) {
    if (!block.title) {
      renumbered.push(block.body)
      continue
    }
    idx += 1
    const num = idx <= CN_NUMS.length ? CN_NUMS[idx - 1] : String(idx)
    renumbered.push(block.body ? `${num}、${block.title}：\n${block.body}` : `${num}、${block.title}：`)
  }

  return renumbered.join('\n\n').replace(/\n{3,}/g, '\n\n').trim()
}

/** 去掉无实质内容的可选段 */
export function stripEmptyReplySections(text) {
  if (!text) return ''
  const s = String(text).replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim()
  if (!s) return ''

  const parts = s.split(SECTION_SPLIT_RE)
  const kept = []

  for (const part of parts) {
    const chunk = part.trim()
    if (!chunk) continue
    const match = chunk.match(SECTION_MATCH_RE)
    if (!match) {
      kept.push(chunk)
      continue
    }
    const header = match[1]
    const body = (match[2] || '').trim()
    const title = header.split('：')[0].split(':')[0]
    if (isOptionalSection(title) && isEmptySectionBody(body)) continue
    kept.push(body ? `${header}\n${body}` : header)
  }

  return renumberReplySections(kept.join('\n\n').replace(/\n{3,}/g, '\n\n').trim())
}

function splitInlinePoints(block) {
  let s = block
  s = s.replace(/([；;。])\s*(?=(?:[一二三四五六七八九十百]+是))/g, '$1\n\n')
  s = s.replace(/([：:])\s*(?=(?:[一二三四五六七八九十百]+是))/g, '$1\n\n')
  s = s.replace(/([；;。])\s*(?=\d+[.、．])/g, '$1\n\n')
  s = s.replace(/(?<=\S)\s+(?=(?:[一二三四五六七八九十百]+是))/g, '\n\n')
  s = s.replace(/(?<=\S)\s+(?=\d+[.、．])/g, '\n\n')
  return s
}

/** 把挤在同段的「一是…二是…」拆成换行分条 */
export function normalizeListLineBreaks(text) {
  if (!text) return ''
  const parts = text.split(SECTION_SPLIT_RE)
  const normalized = []

  for (const part of parts) {
    const chunk = part.trim()
    if (!chunk) continue
    const match = chunk.match(SECTION_MATCH_RE)
    if (!match) {
      normalized.push(splitInlinePoints(chunk))
      continue
    }
    const header = match[1]
    const body = (match[2] || '').trim()
    normalized.push(body ? `${header}\n${splitInlinePoints(body)}` : header)
  }

  return normalized.join('\n\n').replace(/\n{3,}/g, '\n\n').trim()
}

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
  s = s
    .split('\n')
    .map((line) => line.trim())
    .join('\n')

  s = normalizeListLineBreaks(s)
  return stripEmptyReplySections(s.replace(/\n{3,}/g, '\n\n').trim())
}

const FOLLOWUP_SECTION_RE = /(?:[三四五六][、．.]\s*)?建议追问[：:]\s*(.*)/s
const FOLLOWUP_ITEM_RE = /^\d+[.、．)\]]\s*|^[一二三四五六七八九十]+[是、．.]\s*/

/** 从 AI 回复中解析「建议追问」（应在 formatAiReply 之前对原文调用） */
export function extractFollowupQuestions(text, limit = 3) {
  if (!text) return []
  const s = String(text).replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim()
  const match = s.match(FOLLOWUP_SECTION_RE)
  if (!match) return []
  const body = (match[1] || '').trim()
  if (!body || body.includes('暂无需追问') || body === '（本节略）') return []

  const questions = []
  for (const rawLine of body.split('\n')) {
    let line = rawLine.trim().replace(FOLLOWUP_ITEM_RE, '').trim()
    if (!line || line === '（本节略）') continue
    if (line.endsWith('。') && !line.includes('？') && !line.includes('?')) {
      line = line.slice(0, -1)
    }
    if (line.length >= 4) questions.push(line)
  }

  const deduped = []
  const seen = new Set()
  for (const item of questions) {
    const key = item.replace(/\s+/g, '')
    if (seen.has(key)) continue
    seen.add(key)
    deduped.push(item)
    if (deduped.length >= limit) break
  }
  return deduped
}
