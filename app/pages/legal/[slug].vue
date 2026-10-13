<script setup lang="ts">
import type { ContentSurroundLink } from '@nuxt/ui'

// A legal document in the documentation layout (docs/LEGAL-PAGES.md): the documents on the start side (a drawer on
// phones), the document with its numbered, linkable sections, and "On this page" on the end side. Text from
// GET /public/legal/{slug} (useLegal), never invented; a "Draft" note while the owner hasn't published it.
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
const name = computed(() => t(`legal.${LEGAL_KEYS[slug]}`))

const updated = computed(() =>
  document.value.updated_at
    ? t('legalPage.lastUpdated', {
        date: new Intl.DateTimeFormat(locale.value, { dateStyle: 'long' }).format(
          new Date(document.value.updated_at),
        ),
      })
    : t('legalPage.notPublished'),
)

const toc = computed(() =>
  document.value.sections.map(section => ({ id: section.id, text: section.heading, depth: 2 })),
)

const index = LEGAL_SLUGS.indexOf(slug)
// [previous, next]; an empty end is left out by UContentSurround.
const surround = computed(
  () =>
    [LEGAL_SLUGS[index - 1], LEGAL_SLUGS[index + 1]].map(other =>
      other ? { title: t(`legal.${LEGAL_KEYS[other]}`), path: localePath(`/legal/${other}`) } : undefined,
    ) as unknown as ContentSurroundLink[],
)

const navOpen = ref(false)

async function copyLink(id: string) {
  await copy(`${links.site}${localePath(`/legal/${slug}`)}#${id}`)
  toast.add({ title: t('legalPage.copied'), icon: 'i-lucide-link', color: 'neutral' })
}

function print() {
  window.print()
}

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
  <UPage :ui="{ root: 'lg:gap-8', center: 'lg:col-span-6', left: 'lg:col-span-2', right: 'lg:col-span-2' }">
    <template #left>
      <UPageAside class="print:hidden">
        <LegalNav :current="slug" />
      </UPageAside>
    </template>

    <!-- Phones and tablets: the documents in a drawer -->
    <div class="mt-4 lg:hidden print:hidden">
      <USlideover v-model:open="navOpen" side="left" :title="t('legalPage.documents')">
        <UButton
          :label="t('legalPage.documents')"
          icon="i-lucide-panel-left"
          color="neutral"
          variant="outline"
        />
        <template #body>
          <LegalNav :current="slug" @click="navOpen = false" />
        </template>
      </USlideover>
    </div>

    <UPageHeader :title="document.title" :ui="{ root: 'pt-6 sm:pt-8 pb-6', title: 'text-3xl sm:text-4xl' }">
      <template #headline>
        <span class="flex flex-wrap items-center gap-2 text-sm text-muted">
          <UIcon name="i-lucide-scale" class="size-4" />
          {{ t('legal.title') }}
        </span>
      </template>
      <template #description>
        <span class="flex flex-wrap items-center gap-2 text-sm">
          <UBadge
            v-if="document.status === 'draft'"
            :label="t('legalPage.draft')"
            color="warning"
            variant="soft"
            icon="i-lucide-pencil-line"
          />
          <UBadge :label="updated" color="neutral" variant="outline" icon="i-lucide-calendar" />
          <UBadge
            :label="t('legalPage.version', { n: document.version })"
            color="neutral"
            variant="outline"
            icon="i-lucide-git-commit-horizontal"
          />
        </span>
      </template>
      <template #links>
        <UButton
          :label="t('legalPage.print')"
          icon="i-lucide-printer"
          color="neutral"
          variant="outline"
          class="print:hidden"
          @click="print"
        />
      </template>
    </UPageHeader>

    <UPageBody class="mt-6">
      <div class="space-y-3 print:hidden">
        <UAlert
          v-if="document.status === 'draft'"
          :title="t('legalPage.draft')"
          :description="t('legalPage.draftNote')"
          icon="i-lucide-pencil-line"
          color="warning"
          variant="subtle"
        />
        <UAlert
          v-if="otherLanguage"
          :description="t('legalPage.shownInEnglish')"
          icon="i-lucide-languages"
          color="neutral"
          variant="subtle"
        />
        <UAlert
          v-if="source === 'fallback'"
          :description="t('legalPage.offline')"
          icon="i-lucide-cloud-off"
          color="neutral"
          variant="subtle"
        />
        <UAlert
          v-if="document.summary_of_changes"
          :title="t('legalPage.whatChanged')"
          :description="document.summary_of_changes"
          icon="i-lucide-history"
          color="neutral"
          variant="outline"
        />
      </div>

      <!-- The document: about 72 characters wide, calm, no animation -->
      <article :lang="document.language" :dir="otherLanguage ? 'ltr' : undefined" class="mt-8 max-w-[72ch]">
        <section
          v-for="section in document.sections"
          :id="section.id"
          :key="section.id"
          class="group scroll-mt-24"
        >
          <h2
            class="mt-10 flex items-center gap-2 text-xl font-semibold tracking-tight text-highlighted first:mt-0"
          >
            <a :href="`#${section.id}`" class="hover:underline">{{ section.heading }}</a>
            <UButton
              icon="i-lucide-link"
              color="neutral"
              variant="ghost"
              size="xs"
              :aria-label="t('legalPage.copyLink')"
              class="opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100 print:hidden"
              @click="copyLink(section.id)"
            />
          </h2>
          <MDC :value="section.body_markdown" tag="div" class="mt-3 text-[15px]/7 text-toned" />
        </section>
      </article>

      <USeparator class="my-10 print:hidden" />
      <UContentSurround :surround="surround" class="print:hidden" />
    </UPageBody>

    <template #right>
      <UContentToc
        :links="toc"
        :title="t('legalPage.onThisPage')"
        highlight
        color="neutral"
        class="print:hidden"
      />
    </template>
  </UPage>
</template>
