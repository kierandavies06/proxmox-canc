// https://nuxt.com/docs/api/configuration/nuxt-config
const fallbackApiBaseUrl = process.env.NUXT_API_BASE_URL || "http://127.0.0.1:5000";
import tailwindcss from '@tailwindcss/vite';

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  modules: [
    '@nuxt/ui',
    '@nuxt/image',
    '@nuxt/icon',
    '@nuxt/fonts',
    '@nuxt/scripts',
    '@nuxt/hints',
    '@nuxt/eslint'
  ],
  vite: {
    plugins: [
      tailwindcss(),
    ],
  },
  css: ['@/assets/css/main.css'],
  runtimeConfig: {
    apiBaseUrl: fallbackApiBaseUrl,
    public: {
      apiBaseUrl: process.env.NUXT_PUBLIC_API_BASE_URL || fallbackApiBaseUrl,
      apiDocsUrl: process.env.NUXT_PUBLIC_API_DOCS_URL || "http://127.0.0.1:5000/docs",
      releaseStage: process.env.NUXT_PUBLIC_RELEASE_STAGE || "development",
      requireAuth: process.env.NUXT_PUBLIC_REQUIRE_AUTH === "true",
    },
  },
  nitro: {
    preset: 'cloudflare-pages'
  },
})