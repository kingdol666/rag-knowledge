import { defineEventHandler, getQuery } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

export default defineEventHandler(async (event): Promise<unknown> => {
  const q = getQuery(event)
  const backendUrl = getDynamicBackendUrl()
  return await $fetch(`${backendUrl}/api/v1/graph/neighbors`, { query: q })
})
