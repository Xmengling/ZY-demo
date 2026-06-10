/** 判断问诊会话是否归属医案（含采集数据或曾在问诊页带病例摘要问答） */
export function isLinkedCaseSession(detail) {
  if (!detail) return false
  if (detail.linked_case) return true

  if (detail.patient_name?.trim() || detail.case_text?.trim()) return true

  const intake = detail.intake_data || {}
  const textFields = [
    'patient_name',
    'chief_complaint',
    'history',
    'doctor',
    'phone',
    'address',
    'gender',
    'age',
    'modern_diagnosis',
    'pulse',
    'abdominal',
    'tongue_image',
    'visit_time'
  ]
  if (textFields.some((field) => String(intake[field] || '').trim())) return true

  const selected = intake.selected || {}
  if (Object.values(selected).some(Boolean)) return true

  const notes = intake.notes || {}
  if (Object.values(notes).some((value) => String(value).trim())) return true

  const rows = intake.prescription?.rows || []
  if (rows.some((row) => String(row?.name || '').trim())) return true

  const messages = detail.messages || []
  return messages.some((msg) => msg.meta?.case_linked)
}
