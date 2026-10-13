<script setup lang="ts">
import type { ContentNavigationLink } from '@nuxt/ui'

// The legal documents navigator (docs/LEGAL-PAGES.md): the seven documents, the current one marked, and a search
// across the legal text that jumps straight to a section.
const props = defineProps<{ current: LegalSlug }>()
const { t } = useI18n()
const localePath = useLocalePath()

const ICONS: Record<LegalSlug, string> = {
  privacy: 'i-lucide-eye-off',
  terms: 'i-lucide-file-text',
  'data-protection': 'i-lucide-file-lock',
  cookies: 'i-lucide-cookie',
  'acceptable-use': 'i-lucide-scale',
  subprocessors: 'i-lucide-network',
  refunds: 'i-lucide-receipt',
}

const links = computed<ContentNavigationLink[]>(() =>
  LEGAL_SLUGS.map(slug => ({
    title: t(`legal.${LEGAL_KEYS[slug]}`),
    path: localePath(`/legal/${slug}`),
    icon: ICONS[slug],
    active: slug === props.current,
  })),
)

const query = ref('')
const results = computed(() => searchLegal(query.value).slice(0, 12))
</script>

<template>
  <div class="flex flex-col gap-4">
    <p class="text-sm font-semibold text-highlighted">{{ t('legal.title') }}</p>
    <UInput
      v-model="query"
      icon="i-lucide-search"
      :placeholder="t('legalPage.search')"
      :aria-label="t('legalPage.search')"
      color="neutral"
      variant="subtle"
      class="w-full"
    />

    <!-- Search results: sections across the documents -->
    <ul v-if="query.trim().length > 1" class="space-y-1" aria-live="polite">
      <li v-for="hit in results" :key="`${hit.slug}-${hit.id}`">
        <ULink
          :to="`${localePath(`/legal/${hit.slug}`)}#${hit.id}`"
          class="block rounded-md px-2 py-1.5 text-sm hover:bg-elevated"
          @click="query = ''"
        >
          <span class="block truncate font-medium text-highlighted" lang="en">{{ hit.heading }}</span>
          <span class="block truncate text-xs text-muted" lang="en">{{ hit.title }}</span>
        </ULink>
      </li>
      <li v-if="!results.length" class="px-2 text-sm text-muted">{{ t('legalPage.noResults') }}</li>
    </ul>

    <UContentNavigation v-else :navigation="links" highlight color="neutral" />
  </div>
</template>
