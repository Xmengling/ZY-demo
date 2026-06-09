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
