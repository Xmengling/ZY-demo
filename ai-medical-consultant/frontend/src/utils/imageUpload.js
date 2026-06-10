const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
const MAX_FILE_SIZE = 5 * 1024 * 1024
const MAX_IMAGES = 4

export function validateImageFile(file) {
  if (!ALLOWED_TYPES.includes(file.type)) {
    return '仅支持 jpg / png / webp / gif 图片'
  }
  if (file.size > MAX_FILE_SIZE) {
    return '单张图片不能超过 5MB'
  }
  return ''
}

export function readImageAsDataUrl(file, maxDim = 1600, quality = 0.86) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      let { width, height } = img
      const scale = Math.min(1, maxDim / Math.max(width, height))
      width = Math.max(1, Math.round(width * scale))
      height = Math.max(1, Math.round(height * scale))
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        reject(new Error('无法处理图片'))
        return
      }
      ctx.drawImage(img, 0, 0, width, height)
      const mime = file.type === 'image/png' ? 'image/png' : 'image/jpeg'
      resolve(canvas.toDataURL(mime, quality))
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('图片读取失败'))
    }
    img.src = url
  })
}

export { MAX_IMAGES }
