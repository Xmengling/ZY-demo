import { ElMessageBox } from 'element-plus'

/**
 * 删除类操作的二次确认：先说明影响，再要求再次确认。
 * @returns {Promise<boolean>} 用户两次均确认返回 true，否则 false
 */
export async function confirmDeleteTwice(message, secondMessage) {
  const step2 =
    secondMessage || '此操作不可恢复，删除后无法撤销。请再次确认是否继续。'
  try {
    await ElMessageBox.confirm(message, '删除确认', {
      type: 'warning',
      confirmButtonText: '继续',
      cancelButtonText: '取消',
      distinguishCancelAndClose: true
    })
    await ElMessageBox.confirm(step2, '二次确认', {
      type: 'error',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      distinguishCancelAndClose: true
    })
    return true
  } catch {
    return false
  }
}
