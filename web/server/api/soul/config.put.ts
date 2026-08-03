import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** PUT /api/soul/config — 人格配置更新 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(body.soul_kb_id || ''))
  return await $fetch(`${backendUrl}/api/v1/soul/${kbId}/config`, {
    method: 'PUT',
    body: {
      kb_scope: body.kb_scope,
      domain_labels: body.domain_labels,
      supported_task_types: body.supported_task_types,
      route_weight: body.route_weight,
    },
  })
})
