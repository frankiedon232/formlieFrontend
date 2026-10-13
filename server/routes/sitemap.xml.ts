// sitemap.xml (docs/SEO.md): every built page in every language, each with its hreflang alternates and
// x-default (English). Prerendered with the site (nuxt.config.ts). Add new pages to SITE_PATHS.
import { FEATURE_PAGES, SOLUTION_PAGES } from '../../app/utils/catalog'
import { DEFAULT_LOCALE, SITE_LOCALES } from '../../app/utils/locales'

/** The pages that exist (later phases add pricing, legal, contact …). */
export const SITE_PATHS = [
  '/',
  '/features',
  ...FEATURE_PAGES.map(page => `/features/${page.slug}`),
  ...SOLUTION_PAGES.map(page => `/solutions/${page.slug}`),
  '/pricing',
  '/integrations',
  '/security',
  '/about',
]

const localised = (code: string, path: string) =>
  code === DEFAULT_LOCALE ? path : `/${code}${path === '/' ? '' : path}`

export default defineEventHandler(event => {
  const site = useRuntimeConfig().public.siteUrl.replace(/\/$/, '')
  const today = new Date().toISOString().slice(0, 10)

  const urls = SITE_PATHS.flatMap(path =>
    SITE_LOCALES.map(({ code }) => {
      const alternates = [
        ...SITE_LOCALES.map(
          alt =>
            `    <xhtml:link rel="alternate" hreflang="${alt.code}" href="${site}${localised(alt.code, path)}"/>`,
        ),
        `    <xhtml:link rel="alternate" hreflang="x-default" href="${site}${path}"/>`,
      ].join('\n')
      return [
        '  <url>',
        `    <loc>${site}${localised(code, path)}</loc>`,
        `    <lastmod>${today}</lastmod>`,
        `    <changefreq>${path === '/' ? 'weekly' : 'monthly'}</changefreq>`,
        `    <priority>${path === '/' ? '1.0' : path.split('/').length > 2 ? '0.7' : '0.8'}</priority>`,
        alternates,
        '  </url>',
      ].join('\n')
    }),
  )

  setHeader(event, 'content-type', 'application/xml; charset=utf-8')
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ...urls,
    '</urlset>',
    '',
  ].join('\n')
})
