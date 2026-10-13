// robots.txt (docs/SEO.md): everything may be crawled, including /_nuxt (search engines need the CSS and
// scripts to render the pages); the sitemap is named. Prerendered with the site.
export default defineEventHandler(event => {
  const site = useRuntimeConfig().public.siteUrl.replace(/\/$/, '')
  setHeader(event, 'content-type', 'text/plain; charset=utf-8')
  return ['User-agent: *', 'Allow: /', '', `Sitemap: ${site}/sitemap.xml`, ''].join('\n')
})
