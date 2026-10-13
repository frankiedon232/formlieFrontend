/**
 * One legal document from GET {API}/public/legal/{slug}?lang= (docs/LEGAL-PAGES.md), read while the page is
 * prerendered and again in the browser (cached by the API for an hour), so a version the owner publishes shows
 * without a rebuild. When the API doesn't answer, the copy of formlyBackend's drafts is used and `source` says so.
 */
export function useLegal(slug: LegalSlug) {
  const { locale } = useI18n()
  const links = useSiteLinks()

  const { data, refresh } = useAsyncData(
    `legal-${slug}-${locale.value}`,
    async () => {
      try {
        const answer = await $fetch(links.api(`public/legal/${slug}`), {
          query: { lang: locale.value },
          timeout: 5000,
          retry: 0,
        })
        const document = parseLegal(answer)
        if (document) return { document, source: 'api' as LegalSource }
      } catch {
        // Falls through to the copy.
      }
      return { document: fallbackLegal(slug), source: 'fallback' as LegalSource }
    },
    { default: () => ({ document: fallbackLegal(slug), source: 'fallback' as LegalSource }) },
  )

  // After hydration: during it, refresh() would return the prerendered copy from the payload instead of fetching.
  onNuxtReady(() => refresh())

  const document = computed(() => data.value.document)
  const source = computed(() => data.value.source)
  /** The text is in another language than the page (English while a translation is missing). */
  const otherLanguage = computed(() => !locale.value.startsWith(document.value.language))

  return { document, source, otherLanguage }
}
