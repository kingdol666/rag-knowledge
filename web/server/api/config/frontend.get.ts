import { defineEventHandler } from 'h3'
import {
  getDynamicBackendUrl,
  getDynamicFrontendPort,
  getDynamicTreeStoragePath,
  getAppMode,
  getRawConfig,
  invalidateConfigCache,
} from '~/server/utils/dynamic-config'

/**
 * GET /api/config/frontend
 *
 * Returns the frontend-relevant config (read dynamically from config.yml + .env).
 * Called by the client after saving config to refresh runtimeConfig values
 * that were baked into the HTML at page load.
 */
export default defineEventHandler(async () => {
  // Force fresh read (invalidate cache before reading)
  invalidateConfigCache()

  const cfg = getRawConfig()
  const vector = cfg.vector || {}
  const graph = cfg.graph || {}
  const mineru = cfg.mineru || {}

  return {
    success: true,
    config: {
      backend_url: getDynamicBackendUrl(),
      frontend_port: getDynamicFrontendPort(),
      tree_storage_path: getDynamicTreeStoragePath(),
      app_mode: getAppMode(),
      vector_enabled: vector.enabled !== false,
      graph_enabled: graph.enabled !== false,
      mineru_enabled: mineru.enabled !== false,
    },
  }
})
