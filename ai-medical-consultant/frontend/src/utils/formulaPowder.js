/** 从方剂组成文本解析散剂单方总量（g） */
export function parseCompositionTotal(composition) {
  if (!composition) return 0
  const cleaned = String(composition)
    .replace(/\[\[[^\]]+\]\]/g, '')
    .replace(/[半斤两钱]/g, '')
    .trim()
  const normalized = cleaned.replace(/(\D)(\d)/g, '$1 $2')
  const parts = normalized.split(/[+＋、，,\s]+/).filter(Boolean)
  let total = 0
  for (const part of parts) {
    const m = part.match(/(\d+(?:\.\d+)?)\s*(?:g|克|枚)?$/)
    if (m) total += parseFloat(m[1])
  }
  return total
}

export function extractPathologyLabels(pathology) {
  if (!Array.isArray(pathology)) return []
  return [...new Set(pathology.map((p) => (typeof p === 'string' ? p : p?.label)).filter(Boolean))]
}

/** 去掉方剂卡片中的 [[**重点**]] 标记，用于列表展示 */
export function stripFormulaMarkup(text) {
  return String(text || '')
    .replace(/\[\[\*\*([^*]+)\*\*\]\]/g, '$1')
    .replace(/\[\[([^\]]+)\]\]/g, '$1')
    .trim()
}

/** 主要症状：优先 mainSymptoms，否则取临床症状前几条 */
export function formatMainSymptomsText(mainSymptoms, clinicalSymptoms, maxItems = 6) {
  const source =
    Array.isArray(mainSymptoms) && mainSymptoms.length
      ? mainSymptoms
      : Array.isArray(clinicalSymptoms)
        ? clinicalSymptoms
        : []
  if (!source.length) return ''
  return source
    .slice(0, maxItems)
    .map(stripFormulaMarkup)
    .filter(Boolean)
    .join('、')
}

export function normalizeFormulaName(name) {
  return (name || '').trim().replace(/\s+/g, '')
}

export function buildFormulaPowderIndex(formulas = []) {
  const index = new Map()
  for (const f of formulas) {
    const name = normalizeFormulaName(f.name)
    if (!name) continue
    index.set(name, {
      name: f.name,
      total: parseCompositionTotal(f.composition),
      pathology: extractPathologyLabels(f.pathology),
      herbs: f.composition || '',
      mainSymptoms: Array.isArray(f.mainSymptoms) ? f.mainSymptoms : [],
      clinicalSymptoms: Array.isArray(f.clinicalSymptoms) ? f.clinicalSymptoms : []
    })
  }
  return index
}

export function lookupFormulaPowder(index, name) {
  const normalized = normalizeFormulaName(name)
  if (!normalized || !index?.size) return null
  if (index.has(normalized)) return index.get(normalized)
  for (const [key, value] of index.entries()) {
    const base = key.replace(/(汤|散|丸|方)$/u, '')
    if (
      normalized === key ||
      normalized.includes(key) ||
      key.includes(normalized) ||
      normalized === base ||
      normalized.startsWith(base)
    ) {
      return value
    }
  }
  return null
}

export function formatDoseNumber(value) {
  if (!Number.isFinite(value)) return '—'
  const rounded = Math.round(value * 10) / 10
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1)
}

/** 多份合方散剂换算 */
export function runDoseCalc(rows, targetDose) {
  const target = Number(targetDose)
  const parsed = (rows || [])
    .map((row) => ({
      ...row,
      unitTotal: Number(row.unitTotal) || 0,
      portions: Number(row.portions) || 0
    }))
    .filter((row) => row.name?.trim())

  const valid = parsed.filter((r) => r.unitTotal > 0 && r.portions > 0)
  if (!target || !valid.length) {
    return { coefficient: null, total: '—', rows: parsed.map((r) => ({ ...r, finalDose: '—' })) }
  }

  const combinedWeighted = valid.reduce((sum, r) => sum + r.unitTotal * r.portions, 0)
  const coefficient = target / combinedWeighted

  let sumFinal = 0
  const resultMap = new Map()
  valid.forEach((r) => {
    const finalDose = coefficient * r.unitTotal * r.portions
    sumFinal += finalDose
    resultMap.set(r.id, formatDoseNumber(finalDose))
  })

  return {
    coefficient,
    total: formatDoseNumber(sumFinal),
    rows: parsed.map((r) => ({
      ...r,
      finalDose: resultMap.get(r.id) || '—',
      missing: !(r.unitTotal > 0 && r.portions > 0)
    }))
  }
}
