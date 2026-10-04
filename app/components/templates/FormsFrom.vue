<!--
  Template page side panel → usage: forms / responses / last used, then the latest forms made from
  the template in a small slider (up to 5) and "View all" (the forms list filtered by template).
-->
<script setup lang="ts">
import type { FormSummary } from '#shared/types/forms'
import type { TemplateSummary } from '#shared/types/templates'

const props = defineProps<{ template: TemplateSummary }>()
const emit = defineEmits<{ use: [] }>()
const { t } = useI18n()
const api = useApi()
const { number, relative } = useFormat()

const forms = ref<FormSummary[]>([])
const loading = ref(true)
async function load() {
  loading.value = true
  try {
    forms.value = (
      await api.list<FormSummary>('/forms', { 'filter[template]': props.template.key, sort: '-updated_at', page_size: 5 }, { background: true })
    ).data
  } catch {
    forms.value = []
  } finally {
    loading.value = false
  }
}
watch(() => props.template.key, load, { immediate: true })

const usage = computed(() => [
  { icon: 'i-lucide-file-text', label: t('templates.stats.forms'), value: number(props.template.forms_count) },
  { icon: 'i-lucide-inbox', label: t('templates.stats.responses'), value: number(props.template.responses_count) },
  { icon: 'i-lucide-clock-3', label: t('templates.stats.lastUsed'), value: props.template.last_used_at ? relative(props.template.last_used_at) : '-' },
])
</script>

<template>
  <section class="flex flex-col gap-3 rounded-lg border border-default p-4" :aria-label="t('templates.usage')">
    <div class="flex items-center justify-between gap-2">
      <h2 class="text-xs font-medium text-muted uppercase">{{ t('templates.usage') }}</h2>
      <UButton
        v-if="template.forms_count"
        :label="t('templates.viewAll')"
        color="neutral"
        variant="link"
        size="xs"
        trailing-icon="i-lucide-arrow-right"
        :to="`/forms?template=${encodeURIComponent(template.key)}`"
      />
    </div>
    <dl class="grid grid-cols-3 gap-2">
      <div v-for="item in usage" :key="item.label" class="flex min-w-0 flex-col gap-0.5 rounded-md bg-elevated/60 p-2">
        <dt class="flex items-center gap-1 truncate text-[11px] text-muted"><UIcon :name="item.icon" class="size-3 shrink-0" />{{ item.label }}</dt>
        <dd class="truncate text-sm font-semibold text-highlighted tabular-nums">{{ item.value }}</dd>
      </div>
    </dl>

    <USkeleton v-if="loading" class="h-28 w-full rounded-md" />
    <UCarousel
      v-else-if="forms.length"
      v-slot="{ item }"
      :items="forms"
      :arrows="forms.length > 1"
      :dots="forms.length > 1"
      :prev="{ color: 'neutral', variant: 'outline', size: 'xs' }"
      :next="{ color: 'neutral', variant: 'outline', size: 'xs' }"
      :ui="{ root: 'pb-6', controls: 'absolute -bottom-0.5 inset-x-10', dots: 'gap-1.5', dot: 'size-1.5', prev: 'start-0 top-auto bottom-0 translate-y-0', next: 'end-0 top-auto bottom-0 translate-y-0' }"
      :aria-label="t('templates.formsFrom', { count: template.forms_count }, template.forms_count)"
    >
      <NuxtLink
        :to="`/forms/${(item as FormSummary).id}`"
        class="flex h-full flex-col gap-2 rounded-md border border-default p-3 transition-colors hover:border-accented focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
      >
        <span class="flex items-start justify-between gap-2">
          <span class="line-clamp-2 text-sm font-medium text-highlighted">{{ (item as FormSummary).name }}</span>
          <DataStatusBadge :status="(item as FormSummary).status" />
        </span>
        <span class="flex items-center gap-2 text-xs text-muted">
          <UIcon name="i-lucide-inbox" class="size-3.5" />{{ number((item as FormSummary).responses_count) }}
          <span aria-hidden="true">·</span>
          {{ relative((item as FormSummary).updated_at) }}
        </span>
        <UProgress :model-value="(item as FormSummary).completion_rate" color="neutral" size="xs" :aria-label="t('forms.col.completion')" />
      </NuxtLink>
    </UCarousel>
    <div v-else class="flex flex-col items-center gap-2 rounded-md border border-dashed border-default p-4 text-center">
      <UIcon name="i-lucide-file-plus" class="size-5 text-muted" />
      <p class="text-sm text-highlighted">{{ t('templates.noFormsTitle') }}</p>
      <UButton :label="t('templates.use')" icon="i-lucide-file-plus" color="neutral" variant="outline" size="xs" @click="emit('use')" />
    </div>
  </section>
</template>
