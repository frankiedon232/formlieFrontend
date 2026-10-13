import { writeFile } from 'node:fs/promises'
import { join } from 'node:path'
// https://nuxt.com/docs/api/configuration/nuxt-config
import { APP_LOCALES, DEFAULT_LOCALE, LOCALE_COOKIE } from './shared/utils/i18n/locales'
import { WEB_FONTS } from './shared/utils/forms/fonts'
import pkg from './package.json'
import { headersFile, securityHeaders } from './edge/security-headers'

const isDev = process.env.NODE_ENV !== 'production'
// Read at build/start time: switching mock ↔ real backend needs a dev-server restart.
const apiMock = process.env.NUXT_PUBLIC_API_MOCK === 'true'

// Same headers as production (edge/security-headers.ts); the CSP is production-only because Vite's HMR needs eval
// and websockets. Production is a static build: the headers come from `_headers` (written below) and the Worker.
const pageHeaders = securityHeaders(!isDev)

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  // Every page renders in the browser, in development and production alike (owner 2026-10-12): production is a
  // static build (`pnpm generate` → .output/public) on Cloudflare, with a Worker (edge/worker.ts) for /api,
  // short links and form link previews. Nothing in server/ runs in production.
  ssr: false,
  // Production builds (`pnpm generate`) use their own build folder, so they never disturb a running dev server's `.nuxt`.
  buildDir: isDev ? '.nuxt' : 'node_modules/.cache/nuxt-build',

  modules: ['@nuxt/ui', '@nuxt/eslint', '@nuxtjs/i18n', '@vueuse/nuxt'],

  css: ['~/assets/css/main.css'],

  // Formalie's brand icons (Field F, docs/brand/BRAND.md). A workspace's own tab icon replaces them in app.vue.
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

  // composables/, utils/ and shared/utils/ are organised in sub-folders (max two levels).
  imports: {
    dirs: ['~/composables/**', '~/utils/**', '~~/shared/utils/**'],
  },

  nitro: {
    imports: {
      dirs: ['./shared/utils/**'],
    },
  },

  runtimeConfig: {
    // Development only (dev server): where the dev proxy forwards /api/** when the mock is off.
    apiProxyTarget: 'https://formalie.dev:5004',
    // Development only (mock, F24): the secret Payoneer signs its payment notifications with. Production: NUXT_PAYONEER_WEBHOOK_SECRET.
    // Empty outside development = every notification is refused (never trusted unsigned).
    payoneerWebhookSecret: '',
    public: {
      apiBase: '/api/v1',
      appVersion: pkg.version,
      apiMock,
      rootDomain: 'formalie.dev',
      manageSubdomain: 'manage',
      // Public links (docs/01-ARCHITECTURE.md → Public URLs). Production: forms.formalie.com / https://api.formalie.com
      formsHost: 'forms.formalie.dev',
      apiServiceUrl: 'https://api.formalie.dev',
      // The website (formalieSite): its legal pages /legal/{slug} (public forms, sign-up) and the Enterprise enquiry.
      // Production: NUXT_PUBLIC_SITE_URL=https://formalie.com (shared/utils/urls/public.ts → legalUrl).
      siteUrl: 'https://formalie.dev:3033',
    },
  },

  // Development only: the mock API, the dev proxy to the backend and the mock public API. A static build has no
  // server; in production the Worker sends /api to https://services.formalie.com.
  serverHandlers: [
    { route: '/api/**', handler: apiMock ? '~~/server/mock/index.ts' : '~~/server/proxy/api.ts' },
    // The public API service in the mock (F13; Postman: https://localhost:2202/public-api/{apiKey}/{endpoint}).
    ...(apiMock ? [{ route: '/public-api/**', handler: '~~/server/mock/publicApi.ts' }] : []),
  ],

  routeRules: {
    // Every page is client-rendered (ssr: false above). Headers apply on the dev server; production uses `_headers`.
    '/**': { headers: pageHeaders },
    // Destinations moved to the Data sources area (F12).
    '/integrations/destinations': { redirect: '/data-sources/destinations' },
    // Integrations moved to the API service area (owner, 2026-10-03).
    '/integrations': { redirect: '/api-service/webhooks' },
    '/integrations/webhooks': { redirect: '/api-service/webhooks' },
    // Old links land somewhere real (owner, 2026-10-06)
    '/integrations/api-keys': { redirect: '/api-service/auth' },
    '/api-service/api-keys': { redirect: '/api-service/auth' },
    '/api-service/apps': { redirect: '/api-service/webhooks' },
  },

  hooks: {
    // The static build's security headers for Cloudflare (the Worker sets its own for the pages it answers).
    'nitro:build:public-assets': async nitro => {
      await writeFile(join(nitro.options.output.publicDir, '_headers'), headersFile())
    },
  },

  devServer: {
    host: '0.0.0.0',
    port: 2202,
    // Optional: point these at the mkcert files to skip the --https CLI flags.
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
    defaultLocale: DEFAULT_LOCALE,
    strategy: 'no_prefix',
    locales: APP_LOCALES.map(({ code, language, name, dir }) => ({
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

  fonts: {
    // Manrope (main.css), light 300 to bold 700; titles use 600, body 400/500.
    defaults: {
      weights: [300, 400, 500, 600, 700],
      // Latin, Cyrillic, Greek, Vietnamese, plus Arabic (Cairo) and Devanagari (Poppins, Noto Sans)
      subsets: ['latin', 'latin-ext', 'cyrillic', 'cyrillic-ext', 'greek', 'greek-ext', 'vietnamese', 'arabic', 'devanagari'],
    },
    // The form designer's web fonts (shared/utils/forms/fonts.ts, leftovers L2): self-hosted under /_fonts, declared
    // everywhere because a form picks its font at run time; a browser only downloads the one a form uses.
    families: Object.values(WEB_FONTS).map(font => ({ name: font.family, provider: 'google', global: true, weights: [400, 500, 600, 700] })),
  },

  // Icon sets: lucide (UI), circle-flags (languages), simple-icons (sign-in providers), formalie (brand).
  icon: {
    // /api/** belongs to the backend (mock, dev proxy, Nginx in production), keep icons out of it.
    localApiEndpoint: '/_nuxt_icon',
    // i-formalie-mark: the Formalie mark (Field F glyph, currentColor) from app/assets/icons.
    customCollections: [{ prefix: 'formalie', dir: './app/assets/icons' }],
    // Bundle every icon used in the source so menus never render blank while icons load.
    clientBundle: {
      scan: true,
      // Flag names are built at runtime, so the scanner cannot see them.
      icons: APP_LOCALES.map(locale => locale.flag.replace(/^i-circle-flags-/, 'circle-flags:')),
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
