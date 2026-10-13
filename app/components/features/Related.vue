<script setup lang="ts">
// Related feature pages as cards with ink icon tiles.
const props = defineProps<{ slugs: string[]; title?: string }>()
const { t } = useI18n()
const localePath = useLocalePath()

const pages = computed(() => props.slugs.map(slug => featurePage(slug)).filter(page => !!page))
</script>

<template>
  <UPageSection :title="title ?? t('common.related')" :ui="{ container: 'py-16 sm:py-20' }">
    <UPageGrid>
      <UPageCard
        v-for="page in pages"
        :key="page.slug"
        :title="t(`features.${page.slug}.label`)"
        :description="t(`features.${page.slug}.description`)"
        :to="localePath(`/features/${page.slug}`)"
        variant="outline"
        class="group"
        :ui="{ description: 'line-clamp-3' }"
      >
        <template #leading>
          <span
            class="flex size-10 items-center justify-center rounded-lg bg-inverted text-inverted transition-transform motion-safe:group-hover:-translate-y-0.5"
          >
            <UIcon :name="page.icon" class="size-5" />
          </span>
        </template>
        <template #footer>
          <span class="flex items-center gap-1 text-sm font-medium text-highlighted">
            {{ t('common.learnMore') }}
            <UIcon
              name="i-lucide-arrow-right"
              class="size-4 transition-transform group-hover:translate-x-0.5 rtl:group-hover:-translate-x-0.5"
            />
          </span>
        </template>
      </UPageCard>
    </UPageGrid>
  </UPageSection>
</template>
