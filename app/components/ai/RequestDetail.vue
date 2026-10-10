<!--
  One assistant request in a panel from the side (detail panel model, rule 21): header with the kind's
  icon, title, status, kind and ⋯ (open what it made, delete); fact tiles; what was asked and what came
  back; what it read and whether personal data was masked. Previous (K) · position · Next (J).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { AiRequestDetail } from '#shared/types/ai'
import { AI_KIND_META } from '#shared/utils/ai/kinds'

const props = defineProps<{ id: string | null; ids: string[]; actions: (item: AiRequestDetail) => DropdownMenuItem[][] }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { dateTime, relative, number } = useFormat()
const { titleOf, askedOf } = useAiText()

const item = ref<AiRequestDetail | null>(null)
const loading = ref(false)
const failed = ref(false)
async function load(id: string) {
  loading.value = true
  failed.value = false
  try {
    item.value = (await api.get<AiRequestDetail>(`/ai/requests/${id}`)).data
  } catch (error) {
    failed.value = true
    handle(error)
  } finally {
    loading.value = false
  }
}
watch(
  () => [props.id, open.value] as const,
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

const tiles = computed(() =>
  item.value
    ? [
        { key: 'by', label: t('ai.history.col.by'), value: item.value.by.name, icon: 'i-lucide-user' },
        { key: 'when', label: t('ai.history.col.when'), value: dateTime(item.value.created_at), icon: 'i-lucide-clock' },
        { key: 'credits', label: t('ai.history.col.credits'), value: number(item.value.credits), icon: 'i-lucide-coins' },
        { key: 'applied', label: t('ai.history.col.applied'), value: item.value.applied_at ? relative(item.value.applied_at) : '–', icon: 'i-lucide-check-check' },
        { key: 'read', label: t('ai.history.read'), value: item.value.read.length ? item.value.read.map(source => t(`ai.source.${source}.label`)).join(', ') : t('ai.history.readNothing'), icon: 'i-lucide-eye' },
        { key: 'kept', label: t('ai.history.keptUntil'), value: dateTime(item.value.expires_at), icon: 'i-lucide-calendar-clock' },
      ]
    : [],
)
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="item ? titleOf(item) : t('nav.aiHistory')"
    :ui="{ content: 'w-full sm:max-w-2xl', header: 'border-b-0 pb-2', body: 'flex flex-col gap-5 pb-40', footer: 'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4' }"
  >
    <template #header>
      <div v-if="!item" class="flex w-full items-center gap-3.5">
        <USkeleton class="size-14 rounded-2xl" />
        <div class="flex flex-1 flex-col gap-2"><USkeleton class="h-5 w-48" /><USkeleton class="h-4 w-32" /></div>
      </div>
      <div v-else class="flex w-full items-start gap-3.5">
        <span class="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-inverted text-inverted"><UIcon :name="AI_KIND_META[item.kind].icon" class="size-6" /></span>
        <div class="flex min-w-0 flex-1 flex-col gap-1">
          <h2 class="truncate text-lg leading-tight font-semibold text-highlighted">{{ titleOf(item) }}</h2>
          <p class="truncate text-sm text-muted">{{ item.target?.name || t(`ai.kindHint.${item.kind}`) }}</p>
          <div class="mt-1 flex flex-wrap items-center gap-1.5">
            <DataStatusBadge :status="item.status" />
            <UBadge :label="t(`ai.kind.${item.kind}`)" :icon="AI_KIND_META[item.kind].icon" color="neutral" variant="outline" size="sm" class="rounded-md" />
            <UBadge :label="t('ai.label.made')" icon="i-lucide-sparkles" color="neutral" variant="soft" size="sm" class="rounded-md" />
          </div>
        </div>
        <div class="flex shrink-0 items-center gap-1">
          <UDropdownMenu :items="actions(item)" :content="{ align: 'end' }">
            <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="sm" square :aria-label="t('dataView.actions')" />
          </UDropdownMenu>
          <UButton icon="i-lucide-x" color="neutral" variant="soft" size="sm" square class="rounded-full" :aria-label="t('common.close')" @click="open = false" />
        </div>
      </div>
    </template>

    <template #body>
      <div v-if="loading && !item" class="flex flex-col gap-4" :aria-label="t('common.loading')">
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3"><USkeleton v-for="n in 6" :key="n" class="h-14 rounded-lg" /></div>
        <USkeleton v-for="n in 2" :key="n" class="h-24 w-full rounded-lg" />
      </div>
      <AppEmpty v-else-if="failed && !item" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" />
      <div v-else-if="item" class="flex flex-col gap-5 transition-opacity" :class="loading ? 'opacity-60' : ''" :aria-busy="loading || undefined">
        <dl class="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <div v-for="tile in tiles" :key="tile.key" class="flex min-w-0 flex-col gap-0.5 rounded-lg border border-default px-3 py-2">
            <dt class="flex items-center gap-1.5 truncate text-[11px] text-muted"><UIcon :name="tile.icon" class="size-3.5 shrink-0" />{{ tile.label }}</dt>
            <dd class="truncate text-sm font-medium text-highlighted">{{ tile.value }}</dd>
          </div>
        </dl>

        <section class="grid gap-3 sm:grid-cols-2">
          <div class="flex flex-col gap-2 rounded-lg border border-default p-4">
            <h3 class="flex items-center gap-1.5 text-xs font-medium text-muted"><UIcon name="i-lucide-message-square" class="size-3.5" />{{ t('ai.history.asked') }}</h3>
            <p class="text-sm whitespace-pre-line text-default">{{ askedOf(item) }}</p>
          </div>
          <div class="flex flex-col gap-2 rounded-lg border border-default p-4">
            <h3 class="flex items-center gap-1.5 text-xs font-medium text-muted"><UIcon name="i-lucide-sparkles" class="size-3.5" />{{ t('ai.history.answer') }}</h3>
            <AiNotes v-if="item.notes?.length" :notes="item.notes" :stats="item.stats" />
            <p v-else class="text-sm whitespace-pre-line text-default">{{ item.result }}</p>
          </div>
        </section>

        <p class="flex items-start gap-2 text-xs text-muted">
          <UIcon :name="item.masked ? 'i-lucide-shield-check' : 'i-lucide-shield'" class="mt-0.5 size-3.5 shrink-0" />
          {{ item.masked ? t('ai.history.masked') : t('ai.history.notMasked') }}
        </p>
      </div>
    </template>

    <template #footer>
      <nav class="pointer-events-auto flex items-center gap-1 rounded-full border border-default bg-default/95 p-1 shadow-lg backdrop-blur" :aria-label="t('ai.history.navigate')">
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
