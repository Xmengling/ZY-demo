export function splitSymptomText(value) {
  return String(value || '')
    .split(/[、，,；;]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

export function joinSymptomText(parts) {
  return (parts || []).filter(Boolean).join('、')
}

export function toggleSymptomInNote(note, symptom, active) {
  const parts = splitSymptomText(note)
  const index = parts.indexOf(symptom)
  if (active) {
    if (index < 0) parts.push(symptom)
  } else if (index >= 0) {
    parts.splice(index, 1)
  }
  return joinSymptomText(parts)
}

export function renameSymptomInNote(note, oldText, newText) {
  if (!oldText || !newText || oldText === newText) return note
  const parts = splitSymptomText(note)
  const index = parts.indexOf(oldText)
  if (index >= 0) parts[index] = newText
  return joinSymptomText(parts)
}

export function removeSymptomFromNote(note, symptom) {
  return joinSymptomText(splitSymptomText(note).filter((item) => item !== symptom))
}

/** 单个病理块的描述：本例所见 + 已勾选且未写入备注的症状 */
export function buildPathologyBlockText(block, notes, selected) {
  const label = block.label
  const note = String(notes?.[label] || '').trim()
  const chipSelected = (block.symptoms || []).filter((s) => selected?.[s])
  const chunks = []
  if (note) chunks.push(note)
  const extra = chipSelected.filter((s) => !note.includes(s))
  if (extra.length) chunks.push(extra.join('，'))
  return chunks.join('，')
}

function pathologyScoreValue(scores, label) {
  const text = String(scores?.[label] ?? '').trim()
  return text || null
}

/** 病例摘要：按病理标签汇总描述（水实、水虚分别列出） */
export function buildPathologySummaryLines(sections, notes, selected, scores = {}) {
  const lines = []

  for (const section of sections || []) {
    for (const block of section.blocks || []) {
      const text = buildPathologyBlockText(block, notes, selected)
      const score = pathologyScoreValue(scores, block.label)
      if (text || score != null) {
        lines.push({
          label: block.label,
          text,
          score
        })
      }
    }
  }
  return lines
}

export function formatVisitDate(visitTime) {
  if (!visitTime) return ''
  const m = String(visitTime).match(/^(\d{4})-(\d{1,2})-(\d{1,2})/)
  if (m) return `${m[1]}年${Number(m[2])}月${Number(m[3])}日`
  return String(visitTime).trim()
}

export function buildPatientInfoLine(form) {
  return [form?.patient_name, form?.gender, form?.age, formatVisitDate(form?.visit_time)]
    .filter(Boolean)
    .join(' ')
}

export function buildTonguePulseAbdominalText(form) {
  const parts = []
  const tongue = String(form?.tongue_image || '').trim()
  if (tongue) {
    parts.push(tongue)
  } else {
    const legacyBody = String(form?.tongue_body || '').trim()
    const legacyCoat = String(form?.tongue_coat || '').trim()
    if (legacyBody || legacyCoat) {
      parts.push([legacyBody, legacyCoat].filter(Boolean).join('，'))
    }
  }
  const pulse = String(form?.pulse || '').trim()
  if (pulse) parts.push(pulse.startsWith('脉') ? pulse : `脉${pulse}`)
  const abdominal = String(form?.abdominal || '').trim()
  if (abdominal) parts.push(abdominal.startsWith('腹诊') ? abdominal : `腹诊${abdominal}`)
  return parts.join('，')
}

/** 处方摘要：方名 + 份数 */
export function buildPrescriptionSummaryText(prescription) {
  const rows = (prescription?.rows || []).filter((row) => String(row?.name || '').trim())
  if (!rows.length) return ''
  return rows
    .map((row) => {
      const name = String(row.name).trim()
      const portions = Number(row.portions) || 1
      return `${name}${portions}份`
    })
    .join('，')
}

export function stripFormulaBasisText(value) {
  return String(value || '')
    .replace(/（依据：[^）]*）/g, '')
    .replace(/\(依据：[^)]*\)/g, '')
    .trim()
}

export function buildFollowupSymptomText(visit, sections) {
  const symptomText = String(visit?.symptoms_text || '').trim()
  if (symptomText) return symptomText

  const selected = visit?.selected || {}
  const notes = visit?.notes || {}
  const parts = []
  for (const section of sections || []) {
    const sectionLabel = String(section?.title || '').replace(/采集$/, '').trim()
    const sectionText = String(notes?.[sectionLabel] || '').trim()
    if (sectionLabel && sectionText) {
      parts.push(`${sectionLabel}：${sectionText}`)
      continue
    }
    for (const block of section.blocks || []) {
      const text = buildPathologyBlockText(block, notes, selected)
      if (text) parts.push(`${block.label}：${text}`)
    }
  }
  return parts.join('；')
}

/** 病例摘要单行格式 */
export function formatConsultSummaryLine(item) {
  if (item?.kind === 'changeGroups') {
    return (item.groups || [])
      .filter((group) => String(group?.text || '').trim())
      .map((group) => `${group.label}：${String(group.text || '').trim()}`)
      .join('\n')
  }
  const label = String(item?.label || '').trim()
  const text = String(item?.text || '').trim()
  const score = item?.score != null ? String(item.score).trim() : ''
  const body = text && score ? `${text}（${score}）` : text || score
  return `${label}：${body}`
}

/** 病例摘要全文（用于复制） */
export function formatConsultSummaryText(lines) {
  return (lines || [])
    .filter((item) => item?.score != null || String(item?.text || '').trim() || (item?.groups || []).some((group) => String(group?.text || '').trim()))
    .map((item) => formatConsultSummaryLine(item))
    .join('\n')
}

/** 病例摘要：信息、主诉、病理描述、舌脉腹、方剂份数 */
export function buildConsultSummaryLines(form, sections) {
  const lines = []

  const info = buildPatientInfoLine(form)
  if (info) lines.push({ label: '信息', text: info, kind: 'meta' })

  const chief = String(form?.chief_complaint || '').trim()
  if (chief) lines.push({ label: '主诉', text: chief, kind: 'meta' })

  buildPathologySummaryLines(sections, form?.notes, form?.selected, form?.scores).forEach((item) => {
    lines.push({ ...item, kind: 'pathology' })
  })

  const tonguePulseAbdominal = buildTonguePulseAbdominalText(form)
  if (tonguePulseAbdominal) {
    lines.push({
      label: '舌脉腹',
      text: tonguePulseAbdominal,
      kind: 'meta'
    })
  }

  const prescriptionText = buildPrescriptionSummaryText(form?.prescription)
  if (prescriptionText) {
    lines.push({ label: '方剂', text: prescriptionText, kind: 'meta' })
  }

  return lines
}

export function buildFollowupSummaryLines(visit, sections) {
  const lines = []

  const changeGroups = buildFollowupChangeGroups(visit)
  if (changeGroups.some((group) => group.text)) {
    lines.push({
      label: '服药后变化',
      text: changeGroups.map((group) => group.text).filter(Boolean).join('；'),
      kind: 'changeGroups',
      groups: changeGroups
    })
  }

  const prescriptionText = buildPrescriptionSummaryText(visit?.prescription)
  if (prescriptionText) {
    lines.push({ label: '本次调整方剂', text: prescriptionText, kind: 'meta' })
  }

  return lines
}

export function buildFollowupChangeGroups(visit) {
  const changes = Array.isArray(visit?.changes) ? visit.changes.filter(Boolean) : []
  const improved = splitSymptomText(visit?.improved_symptoms)
  const worsened = splitSymptomText(visit?.worsened_symptoms)
  const remaining = splitSymptomText(visit?.remaining_symptoms)

  if (changes.includes('好转') && !improved.length) improved.push('好转')
  if (changes.includes('加重') && !worsened.length) worsened.push('加重')
  if (changes.includes('无变化') && !remaining.length) remaining.push('无变化')
  if (changes.includes('新增症状') && !worsened.includes('新增症状')) worsened.push('新增症状')

  return [
    { key: 'improved', label: '好转的症状', text: joinSymptomText(improved), tone: 'green' },
    { key: 'worsened', label: '加重的症状', text: joinSymptomText(worsened), tone: 'red' },
    { key: 'remaining', label: '仍存在的症状', text: joinSymptomText(remaining), tone: 'orange' }
  ]
}

export function formatConsultSummaryGroups(groups) {
  return (groups || [])
    .filter((group) => Array.isArray(group?.lines) && group.lines.some((item) => item?.score != null || String(item?.text || '').trim()))
    .map((group) => {
      const body = formatConsultSummaryText(group.lines)
      return body ? `【${group.label}】\n${body}` : ''
    })
    .filter(Boolean)
    .join('\n\n')
}
