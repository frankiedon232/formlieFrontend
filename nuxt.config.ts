// https://nuxt.com/docs/api/configuration/nuxt-config
import { writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { DEFAULT_LOCALE, LOCALE_COOKIE, SITE_LOCALES } from './app/utils/locales'
import { headersFile, REDIRECTS, redirectsFile, securityHeaders } from './deploy/headers'

const siteUrl = process.env.NUXT_PUBLIC_SITE_URL || 'https://formalie.dev:3033'
// The origins the CSP allows (docs/SECURITY.md): set NUXT_PUBLIC_API_URL and NUXT_PUBLIC_FORMS_URL before a
// production build (docs/PRODUCTION-CHECKLIST.md, section 7), so `_headers` names the production hosts.
const origins = {
  api: process.env.NUXT_PUBLIC_API_URL || 'https://formalie.dev:5004/api/v1',
  forms: process.env.NUXT_PUBLIC_FORMS_URL || 'https://forms.formalie.dev:2202',
}

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

  ui: {
    // Styles only for the Nuxt UI components the site uses (a smaller stylesheet, a faster first paint; S7).
    experimental: { componentDetection: true },
  },

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
      formsUrl: origins.forms,
      // Formalie's backend API (/public/plans, /public/legal, /public/platform). Production:
      // https://services.formalie.com/api/v1, never api.formalie.com (customers' own API service).
      apiUrl: origins.api,
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

  routeRules: {
    // The same security headers as production, without the CSP (Vite's dev server needs eval and websockets).
    '/**': { headers: securityHeaders(origins, false) },
    // Short addresses used in emails and older links (owner, 2026-10-13): prerendered redirect pages, and 301s from
    // Cloudflare's `_redirects` in production.
    ...Object.fromEntries(REDIRECTS.map(([from, to]) => [from, { redirect: to }])),
  },

  hooks: {
    // Only the entry script is preloaded: dozens of preloaded chunks competed with the stylesheet for the first paint
    // on slow phones (Lighthouse, S7). Other chunks load when a page or section needs them.
    'build:manifest': manifest => {
      for (const chunk of Object.values(manifest)) {
        if (!chunk.isEntry) {
          chunk.preload = false
          chunk.prefetch = false
        }
      }
    },
    // The static build's headers and redirects for Cloudflare (deploy/headers.ts).
    'nitro:build:public-assets': async nitro => {
      await writeFile(join(nitro.options.output.publicDir, '_headers'), headersFile(origins))
      await writeFile(join(nitro.options.output.publicDir, '_redirects'), redirectsFile())
    },
  },

  nitro: {
    prerender: {
      // Every language's home page; the crawler finds the rest from their links.
      routes: [
        ...SITE_LOCALES.map(({ code }) => (code === DEFAULT_LOCALE ? '/' : `/${code}`)),
        '/sitemap.xml',
        '/terms',
        '/privacy',
        '/refunds',
        '/robots.txt',
      ],
      // A broken link or a page that fails stops the build (every page exists since S7).
      failOnError: true,
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
    // Fallbacks for Arabic, Hindi and Bengali (Manrope has no such letters), also self-hosted.
    families: [
      { name: 'Noto Sans Arabic', provider: 'google', subsets: ['arabic'] },
      { name: 'Noto Sans Devanagari', provider: 'google', subsets: ['devanagari'] },
      { name: 'Noto Sans Bengali', provider: 'google', subsets: ['bengali'] },
    ],
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
