export default defineNuxtConfig({
  compatibilityDate: '2026-05-12',
  devtools: { enabled: false },
  ssr: false,
  experimental: {
    viteEnvironmentApi: true,
  },
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://127.0.0.1:8088',
      ragBase: process.env.NUXT_PUBLIC_RAG_BASE || 'http://127.0.0.1:8090',
      observerBase: process.env.NUXT_PUBLIC_OBSERVER_BASE || 'http://127.0.0.1:8094',
      workerBase: process.env.NUXT_PUBLIC_WORKER_BASE || 'http://127.0.0.1:8095',
      gatewaySecret: process.env.NUXT_PUBLIC_GATEWAY_SECRET || '',
    },
  },
})
