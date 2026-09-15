// Nuxt config for the QDCVR benchmark dashboard.
//
// The backend base URL is a runtime setting, not a build-time constant, so the
// same build works whether the API runs on the default port or not:
//   NUXT_PUBLIC_API_BASE=http://127.0.0.1:8800 npm run dev
// The Vite dev proxy additionally forwards /api to the same origin, so relative
// fetches keep working in development without CORS.
const apiBase = process.env.NUXT_PUBLIC_API_BASE || 'http://127.0.0.1:8800';

export default defineNuxtConfig({
  devtools: { enabled: true },
  css: ['~/assets/main.css'],
  app: {
    head: {
      title: 'QDCVR Benchmark — CIKM 2027',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content:
            'Upload documents, then compare RAG retrieval algorithms with per-algorithm parameters.',
        },
      ],
    },
  },
  runtimeConfig: {
    public: { apiBase },
  },
  vite: {
    server: {
      proxy: {
        '/api': { target: apiBase, changeOrigin: true },
      },
    },
  },
});
