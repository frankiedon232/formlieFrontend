// https://nuxt.com/docs/api/configuration/nuxt-config
import { DEFAULT_LOCALE, LOCALE_COOKIE, SITE_LOCALES } from './app/utils/locales'

const siteUrl = process.env.NUXT_PUBLIC_SITE_URL || 'https://formalie.dev:3033'

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  // Server-rendered in development, prerendered for production (`pnpm generate` → .output/public, static files on
  // Cloudflare). Never client-only: every page is real HTML for search engines (CLAUDE.md, Rendering).
  ssr: true,
  // Production builds use their own build folder, so they never disturb a running dev server's `.nuxt`.
  buildDir: process.env.NODE_ENV === 'production' ? '.nuxt-build' : '.nuxt',

  modules: ['@nuxt/ui', '@nuxt/eslint', '@nuxt/content', '@nuxt/image', '@nuxtjs/i18n', '@vueuse/nuxt'],

  css: ['~/assets/css/main.css'],

  // Formalie's brand icons and manifest (docs/brand/web, copied to public/ as they are).
  app: {
    head: {
      link: [
        { key: 'icon-ico', rel: 'icon', href: '/favicon.ico', sizes: '48x48' },
        { key: 'icon-svg', rel: 'icon', href: '/favicon.svg', type: 'image/svg+xml' },
        { rel: 'apple-touch-icon', href: '/apple-touch-icon.png' },
        { rel: 'manifest', href: '/site.webmanifest' },
      ],
      meta: [{ name: 'theme-color', content: '#0a0a0a' }],
    },
  },

  runtimeConfig: {
    public: {
      // Development values; production sets NUXT_PUBLIC_* (docs/PRODUCTION-CHECKLIST.md, section 7).
      siteUrl,
      portalUrl: 'https://manage.formalie.dev:2202',
      formsUrl: 'https://forms.formalie.dev:2202',
      // Formalie's backend API (/public/plans, /public/legal, /public/platform). Production:
      // https://services.formalie.com/api/v1, never api.formalie.com (customers' own API service).
      apiUrl: 'https://formalie.dev:5004/api/v1',
    },
  },

  devServer: {
    host: '0.0.0.0',
    port: 3033,
    // The development certificate (docs/02-DEV-ENVIRONMENT.md): DEV_HTTPS_CERT and DEV_HTTPS_KEY in .env.
    https:
      process.env.DEV_HTTPS_CERT && process.env.DEV_HTTPS_KEY
        ? { cert: process.env.DEV_HTTPS_CERT, key: process.env.DEV_HTTPS_KEY }
        : undefined,
  },

  vite: {
    server: {
      allowedHosts: ['.formalie.dev'],
    },
  },

  typescript: {
    strict: true,
  },

  i18n: {
    baseUrl: siteUrl,
    defaultLocale: DEFAULT_LOCALE,
    // English without a prefix, every other language under its code (/fr/pricing). docs/01-ARCHITECTURE.md.
    strategy: 'prefix_except_default',
    locales: SITE_LOCALES.map(({ code, language, name, dir }) => ({
      code,
      language,
      name,
      dir,
      file: `${code}.json`,
    })),
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: LOCALE_COOKIE,
      redirectOn: 'root',
      fallbackLocale: DEFAULT_LOCALE,
    },
  },

  content: {
    // Node's own SQLite (Node 22.5+), so no native module has to be built.
    experimental: { sqliteConnector: 'native' },
  },

  image: {
    format: ['avif', 'webp'],
    quality: 80,
  },

  fonts: {
    // Manrope, self-hosted under /_fonts (no request to another site): light 300 to bold 700.
    defaults: {
      weights: [300, 400, 500, 600, 700],
      subsets: ['latin', 'latin-ext', 'cyrillic', 'cyrillic-ext', 'greek', 'vietnamese'],
    },
  },

  // Icon sets: lucide (UI), circle-flags (languages), simple-icons (integration logos), formalie (the brand glyph).
  icon: {
    customCollections: [{ prefix: 'formalie', dir: './app/assets/icons' }],
    serverBundle: { collections: ['lucide', 'circle-flags', 'simple-icons'] },
    clientBundle: {
      scan: true,
      // Flag names are built at run time, so the scanner can't see them.
      icons: SITE_LOCALES.map(locale => locale.flag.replace(/^i-circle-flags-/, 'circle-flags:')),
      sizeLimitKb: 256,
    },
  },

  eslint: {
    config: {
      // Formatting is Prettier's job.
      stylistic: false,
    },
  },
})
