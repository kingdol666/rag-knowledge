import { defineEventHandler, readBody } from 'h3'
import { getDynamicBackendUrl } from '~/server/utils/dynamic-config'

/** POST /api/soul/train-rl — RL 强化训练(好奇心×评价Agent×策略更新)。
 * 每轮: learn(探索) → evaluate(reward 四维评分) → cognition drafts(策略更新)。
 * 异步: 立即返回 {task_id}; 轮询 GET /api/soul/tasks/:taskId 看
 * progress {phase: learn|reward, round, rounds, reward, drafts_created}。
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const backendUrl = getDynamicBackendUrl()
  const kbId = encodeURIComponent(String(body.soul_kb_id || ''))
  return await $fetch(`${backendUrl}/api/v1/soul/${kbId}/train-rl`, {
    method: 'POST',
    body: { rounds: body.rounds || 1, async_mode: body.async_mode !== false },
    timeout: 30000,
  })
})
