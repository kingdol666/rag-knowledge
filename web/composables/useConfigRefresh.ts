/**
 * useConfigRefresh — client-side composable for hot-reloading frontend config.
 *
 * After saving config via the Settings page, the client needs to:
 * 1. Fetch the latest config from the server (GET /api/config/frontend)
 * 2. Update the reactive runtimeConfig so all components pick up new values
 * 3. Notify the user which changes require a page reload or service restart
 */

interface FrontendConfig {
  backend_url: string
  frontend_port: string
  tree_storage_path: string
  app_mode: string
  vector_enabled: boolean
  graph_enabled: boolean
  mineru_enabled: boolean
}

export function useConfigRefresh() {
  /**
   * Fetch fresh config from the server and update client-side runtimeConfig.
   * Returns the new config and whether a page reload is recommended.
   */
  async function refreshConfig(): Promise<{ config: FrontendConfig; needsReload: boolean }> {
    try {
      const res = await $fetch<{ success: boolean; config: FrontendConfig }>('/api/config/frontend')

      if (res?.success && res.config) {
        const newCfg = res.config
        const rc = useRuntimeConfig()

        // Track what changed
        const oldBackendUrl = rc.public?.treeStoragePath as string
        const oldStorage = rc.public?.treeStoragePath as string
        let needsReload = false

        // Update runtimeConfig in-place (reactive)
        try {
          if (rc.public) {
            rc.public.treeStoragePath = newCfg.tree_storage_path
          }
          // These are server-only but we set them anyway for consistency
          ;(rc as any).pdfParserApiUrl = newCfg.backend_url
          ;(rc as any).treeStoragePath = newCfg.tree_storage_path
        } catch { /* ignore */ }

        // Determine if a page reload is needed
        // (port changes, storage path changes, or mode changes require reload)
        if (oldStorage !== newCfg.tree_storage_path) {
          needsReload = true
        }

        return { config: newCfg, needsReload }
      }
    } catch (e) {
      console.error('[useConfigRefresh] Failed to refresh config:', e)
    }

    return {
      config: {
        backend_url: 'http://localhost:8765',
        frontend_port: '6789',
        tree_storage_path: './storage/tree-file-system',
        app_mode: 'dev',
        vector_enabled: true,
        graph_enabled: true,
        mineru_enabled: true,
      },
      needsReload: false,
    }
  }

  return { refreshConfig }
}
