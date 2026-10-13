<script setup lang="ts">
// A legal document, documentation style (docs/LEGAL-PAGES.md), made calm and premium (owner, 2026-10-13):
// a hero band with the status, dates and reading time; the navigator card on the start side (chips on phones);
// numbered sections with ink tiles and anchors; "On this page" with reading progress on the end side.
// Text from GET /public/legal/{slug} (useLegal), never invented; a Draft status while the owner hasn't published it.
definePageMeta({ layout: 'legal' })

const route = useRoute()
const { t, locale } = useI18n()
const localePath = useLocalePath()
const links = useSiteLinks()
const toast = useToast()
const { copy } = useClipboard()

const slug = String(route.params.slug)
if (!isLegalSlug(slug)) throw createError({ statusCode: 404, statusMessage: 'Page not found', fatal: true })

const { document, source, otherLanguage } = useLegal(slug)
// The sections that arrived as prerendered or server-rendered HTML, by id. Only those may stay unhydrated: a page
// reached by a link inside the site, or a section whose text changed after the API refresh, is rendered normally
// (a never-hydrated component mounted in the browser would stay empty).
const prerendered = new Map(
  import.meta.server || useNuxtApp().isHydrating
    ? document.value.sections.map(section => [section.id, section.body_markdown])
    : [],
)
const fromServer = (section: { id: string; body_markdown: string }) =>
  prerendered.get(section.id) === section.body_markdown
const name = computed(() => t(`legal.${LEGAL_KEYS[slug]}`))
const draft = computed(() => document.value.status === 'draft')
const slugs = LEGAL_SLUGS
const icons = LEGAL_ICONS
const keys = LEGAL_KEYS

const updated = computed(() =>
  document.value.updated_at
    ? t('legalPage.lastUpdated', {
        date: new Intl.DateTimeFormat(locale.value, { dateStyle: 'long' }).format(
          new Date(document.value.updated_at),
        ),
      })
    : t('legalPage.notPublished'),
)
const minutes = computed(() => readingMinutes(document.value))
const sections = computed(() =>
  document.value.sections.map(section => ({ ...section, ...splitHeading(section.heading) })),
)

// Reading progress through the article (the bar in "On this page").
const article = useTemplateRef<HTMLElement>('article')
const { y } = useWindowScroll()
const progress = computed(() => {
  void y.value
  const el = article.value
  if (!el || import.meta.server) return 0
  const rect = el.getBoundingClientRect()
  const total = rect.height - window.innerHeight * 0.6
  return Math.min(
    100,
    Math.max(0, Math.round(((window.innerHeight * 0.3 - rect.top) / Math.max(total, 1)) * 100)),
  )
})

const pageUrl = computed(() => `${links.site}${localePath(`/legal/${slug}`)}`)
async function copyLink(id?: string) {
  await copy(id ? `${pageUrl.value}#${id}` : pageUrl.value)
  toast.add({ title: t('legalPage.copied'), icon: 'i-lucide-link', color: 'neutral' })
}
const print = () => window.print()

const index = LEGAL_SLUGS.indexOf(slug)
const neighbours = computed(() =>
  [
    { slug: LEGAL_SLUGS[index - 1], label: t('legalPage.previous'), next: false },
    { slug: LEGAL_SLUGS[index + 1], label: t('legalPage.next'), next: true },
  ].filter((item): item is { slug: LegalSlug; label: string; next: boolean } => !!item.slug),
)

usePageSeo({
  title: () => name.value,
  description: () => t(`legalPage.descriptions.${slug}`),
  breadcrumbs: () => [
    { name: t('legal.title'), path: '/legal/privacy' },
    { name: name.value, path: `/legal/${slug}` },
  ],
  schema: () => [
    {
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: document.value.title,
      description: t(`legalPage.descriptions.${slug}`),
      inLanguage: document.value.language,
      version: String(document.value.version),
      ...(document.value.updated_at ? { dateModified: document.value.updated_at } : {}),
      publisher: { '@type': 'Organization', name: 'Formalie', url: links.site },
    },
  ],
})
</script>

<template>
  <div class="pb-16">
    <!-- Hero band -->
    <section
      class="relative isolate mt-4 overflow-hidden rounded-3xl bg-elevated/40 px-6 py-10 ring-1 ring-default sm:px-10 sm:py-12 print:bg-transparent print:p-0 print:ring-0"
    >
      <div
        aria-hidden="true"
        class="absolute inset-0 -z-10 opacity-70 print:hidden"
        style="
          background-image:
            linear-gradient(var(--ui-border) 1px, transparent 1px),
            linear-gradient(90deg, var(--ui-border) 1px, transparent 1px);
          background-size: 32px 32px;
          mask-image: radial-gradient(ellipse at 20% 0%, black 10%, transparent 70%);
        "
      />
      <div
        aria-hidden="true"
        class="absolute -end-24 -top-32 -z-10 size-96 rounded-full bg-violet-500/10 blur-3xl print:hidden"
      />

      <nav :aria-label="t('legal.title')" class="flex items-center gap-2 text-sm text-muted print:hidden">
        <UIcon name="i-lucide-scale" class="size-4" />
        <ULink :to="localePath('/legal/privacy')" class="hover:text-highlighted">{{
          t('legal.title')
        }}</ULink>
        <UIcon name="i-lucide-chevron-right" class="size-3.5 rtl:rotate-180" />
        <span class="text-highlighted">{{ name }}</span>
      </nav>

      <div class="mt-6 flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
        <div class="max-w-2xl">
          <div class="flex items-center gap-4">
            <span
              class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-inverted text-inverted shadow-lg shadow-black/10 print:hidden"
            >
              <UIcon :name="icons[slug]" class="size-5" />
            </span>
            <h1
              class="text-3xl font-semibold tracking-tight text-pretty text-highlighted sm:text-5xl"
              :lang="document.language"
            >
              {{ document.title }}
            </h1>
          </div>
          <p class="mt-4 text-base text-muted sm:text-lg">{{ t(`legalPage.descriptions.${slug}`) }}</p>

          <!-- Status chips -->
          <ul class="mt-6 flex flex-wrap items-center gap-2 text-xs font-medium">
            <li
              class="flex items-center gap-1.5 rounded-full px-3 py-1.5 ring-1"
              :class="
                draft
                  ? 'bg-amber-500/10 text-amber-700 ring-amber-500/25 dark:text-amber-300'
                  : 'bg-emerald-500/10 text-emerald-700 ring-emerald-500/25 dark:text-emerald-300'
              "
            >
              <span class="relative flex size-2">
                <span
                  class="absolute inline-flex size-full rounded-full bg-current opacity-60 motion-safe:animate-ping-soft"
                />
                <span class="relative inline-flex size-2 rounded-full bg-current" />
              </span>
              {{ draft ? t('legalPage.draft') : t('legalPage.published') }}
            </li>
            <li
              class="flex items-center gap-1.5 rounded-full bg-default px-3 py-1.5 text-toned ring-1 ring-default"
            >
              <UIcon name="i-lucide-calendar" class="size-3.5" />{{ updated }}
            </li>
            <li
              class="flex items-center gap-1.5 rounded-full bg-default px-3 py-1.5 text-toned ring-1 ring-default"
            >
              <UIcon name="i-lucide-git-commit-horizontal" class="size-3.5" />{{
                t('legalPage.version', { n: document.version })
              }}
            </li>
            <li
              class="flex items-center gap-1.5 rounded-full bg-default px-3 py-1.5 text-toned ring-1 ring-default"
            >
              <UIcon name="i-lucide-clock" class="size-3.5" />{{ t('legalPage.readingTime', { n: minutes }) }}
            </li>
            <li
              class="flex items-center gap-1.5 rounded-full bg-default px-3 py-1.5 text-toned ring-1 ring-default"
            >
              <UIcon name="i-lucide-list" class="size-3.5" />{{
                t('legalPage.sectionCount', { n: sections.length })
              }}
            </li>
          </ul>
        </div>

        <div class="flex shrink-0 gap-2 print:hidden">
          <UButton :label="t('legalPage.print')" icon="i-lucide-printer" color="neutral" @click="print" />
          <UButton
            :aria-label="t('legalPage.copyPage')"
            icon="i-lucide-link"
            color="neutral"
            variant="outline"
            @click="copyLink()"
          />
        </div>
      </div>
    </section>

    <!-- Phones and tablets: the documents as a row of chips -->
    <nav
      :aria-label="t('legalPage.documents')"
      class="-mx-4 mt-4 overflow-x-auto px-4 pb-1 lg:hidden print:hidden"
    >
      <ul class="flex w-max gap-2">
        <li v-for="other in slugs" :key="other">
          <ULink
            :to="localePath(`/legal/${other}`)"
            :aria-current="other === slug ? 'page' : undefined"
            class="flex items-center gap-2 rounded-full px-3.5 py-2 text-sm font-medium whitespace-nowrap ring-1 transition-colors"
            :class="
              other === slug
                ? 'bg-inverted text-inverted ring-transparent'
                : 'bg-default text-toned ring-default hover:text-highlighted'
            "
          >
            <UIcon :name="icons[other]" class="size-4" />
            {{ t(`legal.${keys[other]}`) }}
          </ULink>
        </li>
      </ul>
    </nav>

    <div
      class="mt-8 grid gap-10 lg:grid-cols-[15rem_minmax(0,1fr)_13rem] xl:grid-cols-[16rem_minmax(0,1fr)_15rem]"
    >
      <aside class="hidden lg:block print:hidden">
        <div class="sticky top-24">
          <LegalNav :current="slug" />
        </div>
      </aside>

      <div class="min-w-0">
        <!-- One slim status strip instead of stacked alerts -->
        <div
          v-if="draft || otherLanguage || source === 'fallback' || document.summary_of_changes"
          class="divide-y divide-default overflow-hidden rounded-2xl bg-default text-sm ring-1 ring-default print:hidden"
        >
          <p v-if="draft" class="flex items-start gap-3 px-4 py-3 text-toned">
            <UIcon name="i-lucide-pencil-line" class="mt-0.5 size-4 shrink-0 text-amber-500" />
            {{ t('legalPage.draftNote') }}
          </p>
          <p v-if="otherLanguage" class="flex items-start gap-3 px-4 py-3 text-toned">
            <UIcon name="i-lucide-languages" class="mt-0.5 size-4 shrink-0 text-muted" />
            {{ t('legalPage.shownInEnglish') }}
          </p>
          <p v-if="source === 'fallback'" class="flex items-start gap-3 px-4 py-3 text-toned">
            <UIcon name="i-lucide-cloud-off" class="mt-0.5 size-4 shrink-0 text-muted" />
            {{ t('legalPage.offline') }}
          </p>
          <p v-if="document.summary_of_changes" class="flex items-start gap-3 px-4 py-3 text-toned">
            <UIcon name="i-lucide-history" class="mt-0.5 size-4 shrink-0 text-muted" />
            <span>
              <span class="font-semibold text-highlighted">{{ t('legalPage.whatChanged') }}:</span>
              <span :lang="document.language" class="ms-1"> {{ document.summary_of_changes }}</span>
            </span>
          </p>
        </div>

        <!-- The document: numbered sections, calm type, about 72 characters wide -->
        <article
          ref="article"
          :lang="document.language"
          :dir="otherLanguage ? 'ltr' : undefined"
          class="mt-10 max-w-[72ch]"
        >
          <section
            v-for="(section, i) in sections"
            :id="section.id"
            :key="section.id"
            class="group scroll-mt-24"
            :class="i > 0 ? 'mt-12 border-t border-default pt-12' : ''"
          >
            <h2 class="flex items-start gap-4">
              <span
                v-if="section.number"
                class="flex h-9 min-w-9 shrink-0 items-center justify-center rounded-xl bg-inverted px-2 font-mono text-sm font-semibold text-inverted tabular-nums"
              >
                {{ section.number }}
              </span>
              <span class="flex flex-1 items-center gap-2 pt-1">
                <a
                  :href="`#${section.id}`"
                  class="text-xl font-semibold tracking-tight text-highlighted hover:underline sm:text-2xl"
                >
                  {{ section.title }}
                </a>
                <UButton
                  icon="i-lucide-link"
                  color="neutral"
                  variant="ghost"
                  size="xs"
                  :aria-label="t('legalPage.copyLink')"
                  class="opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100 print:hidden"
                  @click="copyLink(section.id)"
                />
              </span>
            </h2>
            <!-- Prerendered text stays as it is (never re-parsed in the browser); anything else is rendered. -->
            <LazyLegalBody v-if="fromServer(section)" :markdown="section.body_markdown" hydrate-never />
            <LazyLegalBody v-else :markdown="section.body_markdown" />
          </section>
        </article>

        <!-- Previous and next -->
        <div class="mt-16 grid gap-4 sm:grid-cols-2 print:hidden">
          <ULink
            v-for="item in neighbours"
            :key="item.slug"
            :to="localePath(`/legal/${item.slug}`)"
            class="group flex items-center gap-4 rounded-2xl bg-default p-5 ring-1 ring-default transition hover:shadow-xl hover:shadow-black/5 motion-safe:hover:-translate-y-0.5"
            :class="item.next ? 'sm:col-start-2 sm:flex-row-reverse sm:text-end' : ''"
          >
            <span
              class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-elevated ring-1 ring-default"
            >
              <UIcon :name="icons[item.slug]" class="size-4 text-highlighted" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="block text-xs text-muted">{{ item.label }}</span>
              <span class="block truncate font-semibold text-highlighted">{{
                t(`legal.${keys[item.slug]}`)
              }}</span>
            </span>
            <UIcon
              :name="item.next ? 'i-lucide-arrow-right' : 'i-lucide-arrow-left'"
              class="size-4 text-muted rtl:-scale-x-100"
            />
          </ULink>
        </div>
      </div>

      <!-- On this page: compact, numbered, with reading progress -->
      <aside class="hidden lg:block print:hidden">
        <div class="sticky top-24">
          <LegalToc :sections="sections" :progress="progress" />
        </div>
      </aside>
    </div>
  </div>
</template>
