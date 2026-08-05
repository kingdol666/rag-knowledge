import { defineEventHandler, readMultipartFormData } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/distill-files — 补天蒸馏(批量文件上传, FormData)。
 * 字段: name, personality_req?, kb_scope?, domain_labels?, supported_task_types?,
 * harness? + files[](任意数量, 支持 md/txt/json/eml/mbox/xlsx/docx/pdf/图片/pptx)。
 * 异步: 返回 {task_id} → 轮询 GET /api/soul/tasks/:taskId 看解析/蒸馏进度。
 */
export default defineEventHandler(async (event) => {
  const backendUrl = getDynamicBackendUrl()
  const form = await readMultipartFormData(event)
  if (!form) {
    return { success: false, error: 'no form data' }
  }
  const fd = new FormData()
  for (const part of form) {
    if (part.filename) {
      // 文件字段
      fd.append('files', new Blob([new Uint8Array(part.data)], { type: part.type || 'application/octet-stream' }), part.filename)
    } else {
      fd.append(part.name || '', String(part.data))
    }
  }
  return await $fetch(`${backendUrl}/api/v1/soul/distill-files`, {
    method: 'POST',
    body: fd,
    timeout: 60000,
  })
})
