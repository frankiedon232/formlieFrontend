import type { BreadcrumbItem } from '@nuxt/ui'

/** Labels for dynamic segments (e.g. a form's name), set by the page that knows them. */
const dynamicLabels = ref<Record<string, string>>({})

/**
 * Breadcrumbs from the URL: one segment per path prefix that resolves to a page with
 * `definePageMeta({ breadcrumb })` or a label registered via `setLabel`. Every segment is
 * clickable; prefixes without a page are skipped so there are never dead links.
 */
export function useBreadcrumbs() {
  const { t } = useI18n()
  const route = useRoute()
  const router = useRouter()

  function setLabel(path: string, label: string) {
    dynamicLabels.value = { ...dynamicLabels.value, [path]: label }
  }

  const items = computed<BreadcrumbItem[]>(() => {
    const segments = route.path.split('/').filter(Boolean)
    const crumbs: BreadcrumbItem[] = []

    segments.forEach((_, index) => {
      const path = `/${segments.slice(0, index + 1).join('/')}`
      const resolved = router.resolve(path)
      if (!resolved.matched.length || resolved.name === 'catchall') return

      const key = resolved.meta.breadcrumb
      const label = dynamicLabels.value[path] ?? (key ? t(key) : undefined)
      if (label) crumbs.push({ label, to: path })
    })

    return crumbs
  })

  return { items, setLabel }
}
