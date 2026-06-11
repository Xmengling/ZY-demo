import { ElMessageBox } from 'element-plus'

/**
 * 删除类操作确认（单次弹窗）。
 * @returns {Promise<boolean>} 用户确认返回 true，否则 false
 */
export async function confirmDelete(message) {
  try {
    await ElMessageBox.confirm(message, '删除确认', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      distinguishCancelAndClose: true
    })
    return true
  } catch {
    return false
  }
}

/** @deprecated 使用 confirmDelete；保留兼容，仅弹一次 */
export async function confirmDeleteTwice(message) {
  return confirmDelete(message)
}
