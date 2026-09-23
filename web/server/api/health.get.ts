import { defineEventHandler } from 'h3'

/**
 * GET /api/health — JSON liveness for external monitors (O1 fix).
 *
 * Previously this path fell through to the SPA HTML shell, so monitors that
 * probe /api/health by path convention saw HTML and misread the platform as
 * down. The aggregate dashboard remains at /api/health/stats.
 */
export default defineEventHandler(async () => {
  return {
    status: 'ok',
    service: 'rag-knowledge-web',
    time: new Date().toISOString(),
    stats: '/api/health/stats',
  }
})
