<script setup lang="ts">
// The legal documents navigator (docs/LEGAL-PAGES.md): a floating card with the seven documents (the current one
// in an ink pill), a search across the legal text that jumps to a section, and who to ask.
const props = defineProps<{ current: LegalSlug }>()
const { t } = useI18n()
const slugs = LEGAL_SLUGS
const icons = LEGAL_ICONS
const keys = LEGAL_KEYS
const localePath = useLocalePath()

const query = ref('')
const results = computed(() => searchLegal(query.value).slice(0, 10))
const searching = computed(() => query.value.trim().length > 1)
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="rounded-2xl bg-default/80 p-3 shadow-lg shadow-black/5 ring-1 ring-default backdrop-blur">
      <UInput
        v-model="query"
        icon="i-lucide-search"
        :placeholder="t('legalPage.search')"
        :aria-label="t('legalPage.search')"
        color="neutral"
        variant="soft"
        size="md"
        class="w-full"
        :ui="{ base: 'rounded-xl' }"
      />

      <!-- Search results: sections across the documents -->
      <ul v-if="searching" class="mt-2 space-y-0.5" aria-live="polite">
        <li v-for="hit in results" :key="`${hit.slug}-${hit.id}`">
          <ULink
            :to="`${localePath(`/legal/${hit.slug}`)}#${hit.id}`"
            class="block rounded-xl px-3 py-2 hover:bg-elevated"
            @click="query = ''"
          >
            <span class="block truncate text-sm font-medium text-highlighted" lang="en">{{
              hit.heading
            }}</span>
            <span class="block truncate text-xs text-muted" lang="en">{{ hit.title }}</span>
          </ULink>
        </li>
        <li v-if="!results.length" class="px-3 py-2 text-sm text-muted">{{ t('legalPage.noResults') }}</li>
      </ul>

      <nav v-else :aria-label="t('legalPage.documents')" class="mt-2">
        <ul class="space-y-0.5">
          <li v-for="slug in slugs" :key="slug">
            <ULink
              :to="localePath(`/legal/${slug}`)"
              :aria-current="slug === props.current ? 'page' : undefined"
              class="group flex items-center gap-3 rounded-xl px-2.5 py-2 text-sm transition-colors"
              :class="
                slug === props.current
                  ? 'bg-inverted text-inverted shadow-md shadow-black/10'
                  : 'text-toned hover:bg-elevated hover:text-highlighted'
              "
            >
              <span
                class="flex size-7 shrink-0 items-center justify-center rounded-lg transition-colors"
                :class="
                  slug === props.current
                    ? 'bg-white/15'
                    : 'bg-elevated ring-1 ring-default group-hover:bg-default'
                "
              >
                <UIcon :name="icons[slug]" class="size-3.5" />
              </span>
              <span class="flex-1 truncate font-medium">{{ t(`legal.${keys[slug]}`) }}</span>
              <UIcon
                v-if="slug === props.current"
                name="i-lucide-chevron-right"
                class="size-4 opacity-70 rtl:rotate-180"
              />
            </ULink>
          </li>
        </ul>
      </nav>
    </div>

    <!-- Who to ask -->
    <div class="rounded-2xl bg-elevated/50 p-4 ring-1 ring-default">
      <span class="flex size-8 items-center justify-center rounded-lg bg-inverted text-inverted">
        <UIcon name="i-lucide-message-circle-question" class="size-4" />
      </span>
      <p class="mt-3 text-sm font-semibold text-highlighted">{{ t('legalPage.questionsTitle') }}</p>
      <i18n-t keypath="legalPage.questionsText" tag="p" class="mt-1 text-xs/5 text-muted" scope="global">
        <template #email>
          <a
            href="mailto:privacy@formalie.com"
            class="font-medium text-highlighted underline underline-offset-4"
            >privacy@formalie.com</a
          >
        </template>
      </i18n-t>
    </div>
  </div>
</template>
