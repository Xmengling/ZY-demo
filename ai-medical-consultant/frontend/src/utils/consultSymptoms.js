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
  const num = Number(scores?.[label])
  return !Number.isNaN(num) && num > 0 ? num : null
}

/** 病例摘要：按病理标签汇总描述（水实、水虚分别列出） */
export function buildPathologySummaryLines(sections, notes, selected, scores = {}) {
  const lines = []

  for (const section of sections || []) {
    for (const block of section.blocks || []) {
      const text = buildPathologyBlockText(block, notes, selected)
      if (text) {
        lines.push({
          label: block.label,
          text,
          score: pathologyScoreValue(scores, block.label)
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
  let label = String(item?.label || '').trim()
  if (item?.score != null) label += ` ${item.score}`
  return `${label}：${String(item?.text || '').trim()}`
}

/** 病例摘要全文（用于复制） */
export function formatConsultSummaryText(lines) {
  return (lines || [])
    .filter((item) => String(item?.text || '').trim())
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

  const changes = Array.isArray(visit?.changes) ? visit.changes.filter(Boolean) : []
  if (changes.length) lines.push({ label: '服药后变化', text: changes.join('、'), kind: 'meta' })

  const chief = String(visit?.chief_complaint || '').trim()
  if (chief) lines.push({ label: '当前主诉', text: chief, kind: 'meta' })

  const symptomText = buildFollowupSymptomText(visit, sections)
  if (symptomText) lines.push({ label: '当前症状', text: symptomText, kind: 'meta' })

  const tonguePulseAbdominal = buildTonguePulseAbdominalText({
    tongue_image: visit?.tongue_image,
    pulse: visit?.pulse,
    abdominal: visit?.abdominal
  })
  if (tonguePulseAbdominal) {
    lines.push({ label: '舌脉腹变化', text: tonguePulseAbdominal, kind: 'meta' })
  }

  const previousFormula = String(visit?.previous_formula || '').trim()
  if (previousFormula) lines.push({ label: '上次方剂', text: previousFormula, kind: 'meta' })

  const prescriptionText = buildPrescriptionSummaryText(visit?.prescription)
  if (prescriptionText) {
    lines.push({ label: '本次调整方剂', text: prescriptionText, kind: 'meta' })
  }

  return lines
}

export function formatConsultSummaryGroups(groups) {
  return (groups || [])
    .filter((group) => Array.isArray(group?.lines) && group.lines.some((item) => String(item?.text || '').trim()))
    .map((group) => {
      const body = formatConsultSummaryText(group.lines)
      return body ? `【${group.label}】\n${body}` : ''
    })
    .filter(Boolean)
    .join('\n\n')
}
