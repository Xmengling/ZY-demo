/**
 * 病理配色：先按后缀归族（热/寒/虚/实…），同族内再按具体标签分色阶
 * 例：里热/半热 → 两种红；水实/表实/里实/气实 → 四种黄
 */

const EXACT_CLASS = {
  阴性: 'path-tone-yin',
  虚寒: 'path-tone-yin',
  半表: 'path-tone-half-1',
  里热: 'path-tone-heat-1',
  半热: 'path-tone-heat-2',
  里寒: 'path-tone-cold-1',
  表虚: 'path-tone-deficiency-1',
  里虚: 'path-tone-deficiency-2',
  半虚: 'path-tone-deficiency-3',
  水虚: 'path-tone-deficiency-4',
  气虚: 'path-tone-deficiency-5',
  血虚: 'path-tone-deficiency-6',
  表实: 'path-tone-excess-1',
  里实: 'path-tone-excess-2',
  水实: 'path-tone-excess-3',
  气实: 'path-tone-excess-4',
  血实: 'path-tone-excess-5'
}

const SUFFIX_FAMILY = [
  ['热', 'heat'],
  ['寒', 'cold'],
  ['虚', 'deficiency'],
  ['实', 'excess']
]

const PREFIX_VARIANT = {
  表: 1,
  半: 2,
  里: 3,
  水: 4,
  气: 5,
  血: 6
}

/** @returns {'heat'|'cold'|'deficiency'|'excess'|'half'|'yin'|'neutral'} */
export function getPathologyToneKey(label) {
  const text = String(label || '').trim()
  if (!text) return 'neutral'
  if (text === '阴性' || text === '虚寒') return 'yin'
  if (text === '半表') return 'half'
  for (const [suffix, family] of SUFFIX_FAMILY) {
    if (text.endsWith(suffix)) return family
  }
  return 'neutral'
}

function inferVariantIndex(label, family) {
  const prefix = String(label || '').charAt(0)
  const idx = PREFIX_VARIANT[prefix]
  if (idx) return idx
  if (family === 'half') return 1
  return 1
}

export function getPathologyToneClass(label) {
  const text = String(label || '').trim()
  if (!text) return 'path-tone-neutral'
  if (EXACT_CLASS[text]) return EXACT_CLASS[text]

  const family = getPathologyToneKey(text)
  if (family === 'yin') return 'path-tone-yin'
  if (family === 'neutral') return 'path-tone-neutral'

  const variant = inferVariantIndex(text, family)
  const maxVariants = { heat: 2, cold: 1, deficiency: 6, excess: 5, half: 1 }
  const cap = maxVariants[family] || 1
  const v = Math.min(variant, cap)
  return `path-tone-${family}-${v}`
}

export function isSamePathologyTone(a, b) {
  return getPathologyToneKey(a) === getPathologyToneKey(b)
}
