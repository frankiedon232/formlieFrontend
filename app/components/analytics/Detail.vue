<!--
  A form's analytics in a panel from the side (F18, detail panel model): header with the form,
  its status and ⋯ (open the form, its responses, answers per question, the builder) and a
  one-click bar; then AnalyticsDetailBody (fact tiles, the funnel, pages and questions).
  Previous (K) · position · Next (J). Esc closes.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { FormFunnel } from '#shared/types/analytics'

const props = defineProps<{ id: string | null; ids: string[]; from: string; to: string }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string] }>()
const { t, d } = useI18n()
const day = (date: string) => d(new Date(`${date}T12:00:00`), { day: 'numeric', month: 'short', year: 'numeric' })
const api = useApi()
const { handle } = useErrorHandler()

const funnel = ref<FormFunnel | null>(null)
const loading = ref(false)
const failed = ref(false)
async function load(id: string) {
  loading.value = true
  failed.value = false
  try {
    funnel.value = (await api.get<FormFunnel>(`/analytics/forms/${id}/funnel`, { from: props.from, to: props.to })).data
  } catch (error) {
    failed.value = true
    handle(error)
  } finally {
    loading.value = false
  }
}
watch(
  () => [props.id, open.value, props.from, props.to] as const,
  ([id, isOpen]) => id && isOpen && void load(id),
  { immediate: true },
)

const index = computed(() => (props.id ? props.ids.indexOf(props.id) : -1))
const prev = computed(() => (index.value > 0 ? props.ids[index.value - 1] : null))
const next = computed(() => (index.value >= 0 && index.value < props.ids.length - 1 ? props.ids[index.value + 1] : null))
defineShortcuts({
  j: { usingInput: false, handler: () => open.value && next.value && emit('go', next.value) },
  k: { usingInput: false, handler: () => open.value && prev.value && emit('go', prev.value) },
})
const menu = computed<DropdownMenuItem[][]>(() => {
  const id = funnel.value?.form.id
  if (!id) return []
  return [
    [
      { label: t('analytics.actions.openForm'), icon: 'i-lucide-file-text', to: `/forms/${id}` },
      { label: t('analytics.actions.responses'), icon: 'i-lucide-inbox', to: `/forms/${id}/responses` },
      { label: t('analytics.actions.builder'), icon: 'i-lucide-pencil-ruler', to: `/forms/${id}/build` },
    ],
  ]
})
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="funnel?.form.name || t('nav.analytics')"
    :ui="{ content: 'w-full sm:max-w-2xl', header: 'border-b-0 pb-2', body: 'flex flex-col gap-5 pb-40', footer: 'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4' }"
  >
    <template #header>
      <div v-if="!funnel" class="flex w-full items-center gap-3.5">
        <USkeleton class="size-14 rounded-2xl" />
        <div class="flex flex-1 flex-col gap-2"><USkeleton class="h-5 w-48" /><USkeleton class="h-4 w-32" /></div>
      </div>
      <div v-else class="flex w-full flex-col gap-4">
        <div class="flex items-start gap-3.5">
          <span class="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-inverted text-inverted"><UIcon name="i-lucide-chart-spline" class="size-6" /></span>
          <div class="flex min-w-0 flex-1 flex-col gap-1">
            <h2 class="truncate text-lg leading-tight font-semibold text-highlighted">{{ funnel.form.name }}</h2>
            <p class="truncate text-sm text-muted">{{ t('analytics.detail.subtitle', { from: day(from), to: day(to) }) }}</p>
            <div class="mt-1 flex flex-wrap items-center gap-1.5"><DataStatusBadge :status="funnel.form.status" /></div>
          </div>
          <div class="flex shrink-0 items-center gap-1">
            <UDropdownMenu :items="menu" :content="{ align: 'end' }">
              <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="sm" square :aria-label="t('dataView.actions')" />
            </UDropdownMenu>
            <UButton icon="i-lucide-x" color="neutral" variant="soft" size="sm" square class="rounded-full" :aria-label="t('common.close')" @click="open = false" />
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <UButton :label="t('analytics.actions.perQuestion')" icon="i-lucide-chart-no-axes-combined" color="neutral" size="sm" :to="{ path: `/forms/${funnel.form.id}/responses`, query: { view: 'insights' } }" />
          <UButton :label="t('analytics.actions.responses')" icon="i-lucide-inbox" color="neutral" variant="outline" size="sm" :to="`/forms/${funnel.form.id}/responses`" />
        </div>
      </div>
    </template>

    <template #body>
      <div v-if="loading && !funnel" class="flex flex-col gap-4" :aria-label="t('common.loading')">
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3"><USkeleton v-for="n in 6" :key="n" class="h-14 rounded-lg" /></div>
        <USkeleton v-for="n in 4" :key="n" class="h-14 w-full rounded-lg" />
      </div>
      <AppEmpty v-else-if="failed && !funnel" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" />
      <div v-else-if="funnel" class="transition-opacity" :class="loading ? 'opacity-60' : ''" :aria-busy="loading || undefined">
        <AnalyticsDetailBody :funnel="funnel" />
      </div>
    </template>

    <template #footer>
      <nav class="pointer-events-auto flex items-center gap-1 rounded-full border border-default bg-default/95 p-1 shadow-lg backdrop-blur" :aria-label="t('analytics.detail.navigate')">
        <UButton :label="t('responses.detail.prevShort')" icon="i-lucide-arrow-up" color="neutral" variant="ghost" size="sm" class="rounded-full" :disabled="!prev" @click="prev && emit('go', prev)">
          <template #trailing><UKbd value="K" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
        <span v-if="index >= 0" class="px-2 text-xs text-muted tabular-nums">{{ t('responses.detail.position', { n: index + 1, total: ids.length }) }}</span>
        <UButton :label="t('responses.detail.nextShort')" icon="i-lucide-arrow-down" color="neutral" variant="solid" size="sm" class="rounded-full" :disabled="!next" @click="next && emit('go', next)">
          <template #trailing><UKbd value="J" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
      </nav>
    </template>
  </USlideover>
</template>
