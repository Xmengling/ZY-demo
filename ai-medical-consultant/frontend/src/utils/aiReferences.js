/** AI 问答引用来源：归一化与跳转 */

export function normalizeReferences(refs) {
  if (!Array.isArray(refs)) return []
  const seen = new Set()
  return refs
    .map((item) => ({
      title: String(item?.title || '').trim(),
      category: String(item?.category || '').trim(),
      department: String(item?.department || '').trim(),
      source: String(item?.source || '').trim(),
      score: item?.score
    }))
    .filter((item) => {
      if (!item.title) return false
      const key = `${item.category}::${item.title}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
}

/** @returns {{ name: string } | null} */
export function referenceRoute(ref) {
  const category = ref?.category || ''
  const source = ref?.source || ''
  if (category === '方剂梳理' || source === 'jingfang') {
    return { name: 'formulas' }
  }
  if (category === '伤寒论条文解读' || source === 'shanghan') {
    return { name: 'shanghan' }
  }
  if (category === '知识库上传' || source === 'upload') {
    return { name: 'knowledge' }
  }
  return null
}

export function referenceDisplayTitle(ref) {
  const title = String(ref?.title || '').trim()
  const category = String(ref?.category || '').trim()
  if (category === '知识库上传' && ref?.department) {
    return ref.department
  }
  return title
}

export function referenceCategoryLabel(ref) {
  const category = String(ref?.category || '').trim()
  if (!category) return '资料'
  if (category === '知识库上传') return '上传资料'
  return category
}
