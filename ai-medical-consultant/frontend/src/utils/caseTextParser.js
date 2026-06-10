// 医案文本自动解析：从粘贴的医案/病历文字中提取问诊表单字段与症状勾选
// 仅做规则解析，不依赖后端。复诊内容不参与解析（避免把"已消失"的症状勾上）。

const NEGATION_WORDS = ['无', '不', '未', '没有', '否认', '非']

// 取首诊部分：遇到"复诊"或"二诊/三诊"后的内容不参与解析
function firstVisitText(text) {
  const m = text.search(/复诊|二诊|三诊|再诊/)
  return m === -1 ? text : text.slice(0, m)
}

function matchOne(text, regex) {
  const m = text.match(regex)
  return m ? (m[1] || '').trim() : ''
}

function cleanTail(s) {
  return s.replace(/[，,。;；、\s]+$/, '').trim()
}

// 姓名、性别、年龄："董某，男，54岁" / "患者王某某，女，32岁"
function parsePatientLine(text) {
  const re = /(?:患者)?([\u4e00-\u9fa5·]{1,6}?)[，,]\s*(男|女)[，,]\s*(\d{1,3})\s*岁/
  const m = text.match(re)
  if (!m) {
    // 兜底：只有性别年龄 "男，54岁"
    const m2 = text.match(/(男|女)[，,]\s*(\d{1,3})\s*岁/)
    if (m2) return { name: '', gender: m2[1], age: m2[2] }
    return { name: '', gender: '', age: '' }
  }
  let name = m[1].trim()
  // 排除误把前文词当姓名（如"医案一"）
  if (/[医案诊一二三四五六七八九十、.．\d]/.test(name)) name = ''
  return { name, gender: m[2], age: m[3] }
}

function parseTongueImage(text) {
  // "舌淡红有齿痕，苔薄黄" / "舌质淡红，舌苔黄腻" → 合并为舌像
  const body = matchOne(text, /舌(?:质|体)?([^，。;；,\n苔脉]{1,16})/)
  const coat = matchOne(text, /(?:舌)?苔([^，。;；,\n脉]{1,12})/)
  const parts = [cleanTail(body), cleanTail(coat)].filter(Boolean)
  return parts.join('，')
}

function parsePulse(text) {
  // 从"脉"起，截到"腹诊"或句号；"脉略弦，脉律不齐，约120次/分"
  const m = text.match(/[，。;；,\s]脉([^。;；\n]*?)(?=[，,]?\s*腹诊|[。;；\n]|$)/)
  if (!m) return ''
  return cleanTail(m[1])
}

function parseAbdominal(text) {
  return cleanTail(matchOne(text, /腹诊[：:]?\s*([^。;；\n]*)/))
}

function parseChiefComplaint(text) {
  return cleanTail(matchOne(text, /主诉[：:]\s*([^\n。]*)/))
}

// 就诊时间："2022年5月6日就诊" / "就诊日期：2022-05-06" → YYYY-MM-DD
function parseVisitTime(text) {
  let m = text.match(/(\d{4})年(\d{1,2})月(\d{1,2})日/)
  if (m) {
    return `${m[1]}-${String(m[2]).padStart(2, '0')}-${String(m[3]).padStart(2, '0')}`
  }
  m = text.match(/(?:就诊|初诊|日期)[：:]?\s*(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/)
  if (m) {
    return `${m[1]}-${String(m[2]).padStart(2, '0')}-${String(m[3]).padStart(2, '0')}`
  }
  return ''
}

// 主诊医生："主诊医生：张三" / "医师：李四"
function parseDoctor(text) {
  return cleanTail(matchOne(text, /(?:主诊医生|主诊医师|主治医生|主治医师|接诊医生|医师|医生)[：:]\s*([\u4e00-\u9fa5·]{2,8})/))
}

function parseModernDiagnosis(text) {
  const lines = text.split(/\n/)
  const hits = []
  const re = /辅助检查|心电图|检查示|检验|化验|CT|MRI|B超|彩超|超声|X线|血常规|尿常规|血压|血糖/
  for (const line of lines) {
    const t = line.trim()
    if (!t || !re.test(t)) continue
    hits.push(cleanTail(t.replace(/^辅助检查/, '').replace(/^[：:]/, '')))
  }
  return hits.join('；')
}

// 病程叙述：主诉行之后的第一段叙述，截到舌诊/腹诊描述之前
function parseHistory(text) {
  const lines = text.split(/\n/).map((l) => l.trim()).filter(Boolean)
  let start = lines.findIndex((l) => /^主诉[：:]/.test(l))
  const candidates = lines.slice(start === -1 ? 0 : start + 1)
  const narrative = candidates.find(
    (l) => l.length > 20 && !/^(辅助检查|心电图|主诉|处方|腹诊)/.test(l) && !/^[\u4e00-\u9fa5·]{1,6}[，,](男|女)/.test(l)
  )
  if (!narrative) return ''
  // 截掉舌脉腹之后的内容（这些已单独解析）
  const cutMatch = narrative.search(/[，。;；,]\s*(舌(?:质|体|淡|红|暗|胖)|腹诊|脉[象略弦沉浮滑数细弱紧缓])/)
  const result = cutMatch === -1 ? narrative : narrative.slice(0, cutMatch)
  return cleanTail(result)
}

// 在文本中匹配症状词，并检查前面是否有否定词（如"无胸痛"不算）
function symptomMentioned(text, symptom) {
  let idx = text.indexOf(symptom)
  while (idx !== -1) {
    const before = text.slice(Math.max(0, idx - 3), idx)
    const negated = NEGATION_WORDS.some((w) => before.endsWith(w))
    if (!negated) return true
    idx = text.indexOf(symptom, idx + symptom.length)
  }
  return false
}

/**
 * 解析医案文本
 * @param {string} rawText 粘贴的原始文本
 * @param {Array} sections 症状采集模块（含 blocks[].symptoms），用于自动勾选
 * @returns {{ fields: Object, symptoms: string[] }}
 */
export function parseCaseText(rawText, sections = []) {
  const text = firstVisitText(String(rawText || ''))
  const patient = parsePatientLine(text)
  const fields = {
    patient_name: patient.name,
    gender: patient.gender,
    age: patient.age,
    visit_time: parseVisitTime(text),
    doctor: parseDoctor(text),
    chief_complaint: parseChiefComplaint(text),
    history: parseHistory(text),
    tongue_image: parseTongueImage(text),
    pulse: parsePulse(text),
    abdominal: parseAbdominal(text),
    modern_diagnosis: parseModernDiagnosis(text)
  }

  const symptoms = []
  const seen = new Set()
  for (const section of sections) {
    for (const block of section.blocks || []) {
      for (const symptom of block.symptoms || []) {
        if (seen.has(symptom)) continue
        if (symptomMentioned(text, symptom)) {
          symptoms.push(symptom)
          seen.add(symptom)
        }
      }
    }
  }

  return { fields, symptoms }
}

export const FIELD_LABELS = {
  patient_name: '姓名',
  gender: '性别',
  age: '年龄',
  visit_time: '就诊时间',
  doctor: '主诊医生',
  chief_complaint: '主诉',
  history: '病程',
  tongue_image: '舌像',
  tongue_body: '舌质',
  tongue_coat: '舌苔',
  pulse: '脉象',
  abdominal: '腹诊',
  modern_diagnosis: '现代诊断'
}
