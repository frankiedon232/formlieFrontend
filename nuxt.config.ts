import { randomUUID } from 'node:crypto'
// https://nuxt.com/docs/api/configuration/nuxt-config
import { APP_LOCALES, DEFAULT_LOCALE, LOCALE_COOKIE } from './shared/utils/i18n/locales'
import pkg from './package.json'

const isDev = process.env.NODE_ENV !== 'production'
// Read at build/start time: switching mock ↔ real backend needs a dev-server restart.
const apiMock = process.env.NUXT_PUBLIC_API_MOCK === 'true'

const securityHeaders: Record<string, string> = {
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
  'Cross-Origin-Opener-Policy': 'same-origin',
  'X-Frame-Options': 'SAMEORIGIN',
}

// Vite HMR needs eval + websockets, so the CSP is production-only.
// Embeds (/{formKey}/embed) get a per-form frame-ancestors from the server in F10.
if (!isDev) {
  securityHeaders['Content-Security-Policy'] = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "font-src 'self' data:",
    "connect-src 'self'",
    // The in-app browser on public forms shows https pages (website, terms, privacy) in a frame (F10).
    "frame-src 'self' https:",
    "frame-ancestors 'self'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
  ].join('; ')
}

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  modules: ['@nuxt/ui', '@nuxt/eslint', '@nuxtjs/i18n', '@vueuse/nuxt'],

  css: ['~/assets/css/main.css'],

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
    // Server-only: where the dev proxy forwards /api/** when the mock is off.
    apiProxyTarget: 'https://formalie.dev:5004',
    // Server-only: lets the Nuxt server read published forms for server-rendered pages (F10).
    // Production sets NUXT_INTERNAL_TOKEN (shared with the API); development makes one per start.
    internalToken: randomUUID(),
    public: {
      apiBase: '/api/v1',
      appVersion: pkg.version,
      apiMock,
      rootDomain: 'formalie.dev',
      manageSubdomain: 'manage',
      // Public links (docs/01-ARCHITECTURE.md → Public URLs). Production: forms.formalie.com / https://api.formalie.com
      formsHost: 'forms.formalie.dev',
      apiServiceUrl: 'https://api.formalie.dev',
      // Formalie's legal pages, linked in the footer of every public form (owner, 2026-10-03).
      legal: { termsUrl: 'https://formalie.com/terms', privacyUrl: 'https://formalie.com/privacy' },
    },
  },

  serverHandlers: [
    { route: '/api/**', handler: apiMock ? '~~/server/mock/index.ts' : '~~/server/proxy/api.ts' },
    // The public API service in the mock (F13; Postman: https://localhost:2202/public-api/{apiKey}/{endpoint}).
    ...(apiMock ? [{ route: '/public-api/**', handler: '~~/server/mock/publicApi.ts' }] : []),
  ],

  routeRules: {
    // Portal: client-rendered. Public forms (/{formKey}/fill · /embed) and short links: server-rendered for SEO.
    '/**': { ssr: false, headers: securityHeaders },
    '/*/fill': { ssr: true },
    '/*/embed': { ssr: true },
    '/s/**': { ssr: true },
    // Destinations moved to the Data sources area (F12).
    '/integrations/destinations': { redirect: '/data-sources/destinations' },
    // Integrations moved to the API service area (owner, 2026-10-03).
    '/integrations': { redirect: '/api-service/webhooks' },
    '/integrations/webhooks': { redirect: '/api-service/webhooks' },
    '/integrations/api-keys': { redirect: '/api-service/api-keys' },
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
    defaults: { weights: [300, 400, 500, 600, 700] },
  },

  // Icon sets: lucide (UI), circle-flags (languages), simple-icons (sign-in providers).
  icon: {
    // /api/** belongs to the backend (mock, dev proxy, Nginx in production), keep icons out of it.
    localApiEndpoint: '/_nuxt_icon',
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
