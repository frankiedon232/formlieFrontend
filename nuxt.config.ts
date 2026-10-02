// https://nuxt.com/docs/api/configuration/nuxt-config
import { APP_LOCALES, DEFAULT_LOCALE, LOCALE_COOKIE } from './shared/utils/i18n/locales'

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
// Embeds (/f/**/embed) get a per-form frame-ancestors from the server in F8.
if (!isDev) {
  securityHeaders['Content-Security-Policy'] = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "font-src 'self' data:",
    "connect-src 'self'",
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
    public: {
      apiBase: '/api/v1',
      apiMock,
      rootDomain: 'formalie.dev',
      manageSubdomain: 'manage',
    },
  },

  serverHandlers: [
    { route: '/api/**', handler: apiMock ? '~~/server/mock/index.ts' : '~~/server/proxy/api.ts' },
  ],

  routeRules: {
    // Portal: client-rendered. Public forms and short links: server-rendered for SEO.
    '/**': { ssr: false, headers: securityHeaders },
    '/f/**': { ssr: true },
    '/s/**': { ssr: true },
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

  icon: {
    // /api/** belongs to the backend (mock, dev proxy, Nginx in production) — keep icons out of it.
    localApiEndpoint: '/_nuxt_icon',
    // Bundle every icon used in the source so menus never render blank while icons load.
    clientBundle: { scan: true, sizeLimitKb: 256 },
  },

  eslint: {
    config: {
      // Formatting is Prettier's job.
      stylistic: false,
    },
  },
})
