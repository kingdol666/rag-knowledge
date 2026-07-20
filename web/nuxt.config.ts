﻿import { getServerConfig, resolveProjectPath } from './utils/paths.mjs'

// All backend URL from shared config.yml — no hardcoded port
// ENV > config.yml: BACKEND_URL > BACKEND_PORT > config.yml
const serverCfg = getServerConfig()
const backEndUrl = process.env.BACKEND_URL
  || (process.env.BACKEND_PORT ? `http://localhost:${process.env.BACKEND_PORT}` : undefined)
  || serverCfg.backend_url
  || 'http://localhost:8765'

// Read storage path: .env > config.yml > hardcoded default
const configStoragePath = serverCfg.tree_fs_root || './storage/tree-file-system'
const defaultTreeStoragePath = process.env.TREE_STORAGE_PATH || configStoragePath

export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: true },
  ssr: false,

  modules: [
    '@pinia/nuxt',
  ],

  app: {
    head: {
      title: 'RAG Knowledge Base — Intelligent Document Management',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'AI-powered knowledge management system with RAG technology, document parsing, knowledge retrieval and graph visualization' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/images/logo.svg' },
        { rel: 'apple-touch-icon', href: '/images/logo.svg' },
      ],
    },
    pageTransition: { name: 'page', mode: 'out-in' },
    layoutTransition: { name: 'layout', mode: 'out-in' },
  },

 css: [
   'ant-design-vue/dist/reset.css',
   '~/assets/css/theme.css',
 ],

  vite: {
    optimizeDeps: {
      include: ['ant-design-vue', '@ant-design/icons-vue'],
    },
    resolve: {
      alias: {
        // Workaround for Nuxt 3.21.x + Vite 7 SPA-mode regression:
        // `#app-manifest` is only resolved inside @nuxt/vite-builder's
        // EnvironmentsPlugin (gated behind experimental.viteEnvironmentApi,
        // which defaults to false). In SPA dev mode the legacy serial-build
        // path never registers the `nuxt:client:aliases` resolver, so Vite's
        // import-analysis fails on the dead `import("#app-manifest")` in
        // nuxt/dist/app/composables/manifest.js. Mirror Nuxt's own mapping
        // (see @nuxt/vite-builder clientAliases) so it resolves to an empty
        // stub. Safe to remove once Nuxt ships a fallback in the serial path.
        '#app-manifest': 'mocked-exports/empty',
      },
    },
  },

  runtimeConfig: {
    treeStoragePath: defaultTreeStoragePath,
    pdfParserApiUrl: backEndUrl,
    public: {
      treeStoragePath: defaultTreeStoragePath,
    },
  },
})