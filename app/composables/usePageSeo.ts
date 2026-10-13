/**
 * SEO for every page (docs/SEO.md, owner 2026-10-13: "this is the real central page, so it must be loaded with
 * SEO"). One call sets the title ("{Page} · Formalie"), the description, Open Graph and Twitter cards with the
 * 1200 × 630 image, robots hints, a BreadcrumbList and any extra structured data. The canonical address, hreflang
 * for the 20 languages and og:locale come from useLocaleHead in app.vue.
 */
export interface PageSeo {
  /** The page name; the title becomes "{title} · Formalie" unless `fullTitle` is set. */
  title: MaybeRefOrGetter<string>
  fullTitle?: MaybeRefOrGetter<string>
  description: MaybeRefOrGetter<string>
  /** Path under public/, 1200 × 630. */
  image?: string
  imageAlt?: MaybeRefOrGetter<string>
  /** The trail from the home page, without the home page itself: [{ name, path }]. */
  breadcrumbs?: MaybeRefOrGetter<{ name: string; path: string }[]>
  /** Extra JSON-LD objects (SoftwareApplication, FAQPage, Product …). */
  schema?: MaybeRefOrGetter<Record<string, unknown>[]>
  type?: 'website' | 'article'
  noindex?: boolean
}

export function usePageSeo(options: PageSeo) {
  const { t } = useI18n()
  const localePath = useLocalePath()
  const links = useSiteLinks()

  const title = computed(() => toValue(options.fullTitle) || `${toValue(options.title)} · Formalie`)
  const description = computed(() => toValue(options.description))
  const image = `${links.site}${options.image ?? '/og-image.png'}`
  const imageAlt = computed(() => toValue(options.imageAlt) || t('site.tagline'))

  useSeoMeta({
    title,
    description,
    ogTitle: title,
    ogDescription: description,
    ogType: options.type ?? 'website',
    ogSiteName: 'Formalie',
    ogImage: image,
    ogImageWidth: 1200,
    ogImageHeight: 630,
    ogImageType: 'image/png',
    ogImageAlt: imageAlt,
    twitterCard: 'summary_large_image',
    twitterTitle: title,
    twitterDescription: description,
    twitterImage: image,
    twitterImageAlt: imageAlt,
    robots: options.noindex
      ? 'noindex, follow'
      : 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1',
  })

  useHead(() => {
    const scripts: Record<string, unknown>[] = [...(toValue(options.schema) ?? [])]
    const trail = toValue(options.breadcrumbs)
    if (trail?.length) {
      scripts.push({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [{ name: 'Formalie', path: '/' }, ...trail].map((item, i) => ({
          '@type': 'ListItem',
          position: i + 1,
          name: item.name,
          item: `${links.site}${localePath(item.path)}`.replace(/\/$/, '') || links.site,
        })),
      })
    }
    return {
      script: scripts.map((data, i) => ({
        key: `page-schema-${i}`,
        type: 'application/ld+json',
        innerHTML: JSON.stringify(data),
      })),
    }
  })
}
