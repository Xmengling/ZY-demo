/** 首页欢迎区建议问题：按类型轮换，已问过的不重复 */

export const HOME_SUGGESTION_SLOTS = [
  {
    type: 'fangzheng',
    pool: [
      '桂枝汤的方证抓手是什么？',
      '小柴胡汤的方证抓手是什么？',
      '麻黄汤的方证抓手是什么？',
      '五苓散的方证抓手是什么？',
      '附子泻心汤的方证抓手是什么？',
      '半夏泻心汤的方证抓手是什么？'
    ]
  },
  {
    type: 'definition',
    pool: [
      '太阳病提纲如何理解？',
      '少阳病提纲如何理解？',
      '阳明病提纲如何理解？',
      '伤寒论第96条如何理解？',
      '半表半里证如何理解？'
    ]
  },
  {
    type: 'compare',
    pool: [
      '五苓散与猪苓汤如何鉴别？',
      '桂枝汤与麻黄汤如何鉴别？',
      '大柴胡汤与小柴胡汤如何鉴别？',
      '苓桂术甘汤与真武汤如何鉴别？',
      '半夏泻心汤与生姜泻心汤如何鉴别？',
      '猪苓汤与泽泻汤如何鉴别？'
    ]
  }
]

const FALLBACK_POOL = HOME_SUGGESTION_SLOTS.flatMap((slot) => slot.pool)

export function normalizeQuestionText(text) {
  return String(text || '')
    .trim()
    .replace(/[？?。．]+$/g, '')
    .replace(/\s+/g, '')
}

export function isQuestionAsked(question, askedList) {
  const q = normalizeQuestionText(question)
  if (!q) return false
  return (askedList || []).some((item) => {
    const a = normalizeQuestionText(item)
    if (!a) return false
    if (a === q) return true
    const minLen = Math.min(a.length, q.length, 8)
    if (minLen >= 6 && (a.includes(q.slice(0, minLen)) || q.includes(a.slice(0, minLen)))) {
      return true
    }
    return false
  })
}

/** @param {string[]} askedList 历史已问问题（会话标题等） */
export function buildHomeSuggestions(askedList = [], limit = 3) {
  const asked = [...new Set((askedList || []).map((item) => String(item || '').trim()).filter(Boolean))]
  const picked = []
  const used = new Set()

  for (const slot of HOME_SUGGESTION_SLOTS) {
    const candidate = slot.pool.find(
      (item) => !isQuestionAsked(item, asked) && !used.has(normalizeQuestionText(item))
    )
    if (candidate) {
      picked.push(candidate)
      used.add(normalizeQuestionText(candidate))
    }
    if (picked.length >= limit) break
  }

  if (picked.length < limit) {
    for (const item of FALLBACK_POOL) {
      const key = normalizeQuestionText(item)
      if (used.has(key) || isQuestionAsked(item, asked)) continue
      picked.push(item)
      used.add(key)
      if (picked.length >= limit) break
    }
  }

  return picked.slice(0, limit)
}
