export default defineNuxtConfig({
  devtools: { enabled: true },
  css: ['~/assets/main.css'],
  app: {
    head: {
      title: 'QDCVR Benchmark — CIKM 2027',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      ],
    },
  },
  vite: {
    server: {
      proxy: {
        '/api': 'http://localhost:8800',
      },
    },
  },
});
