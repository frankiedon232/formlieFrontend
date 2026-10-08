<!--
  An access rule in a panel from the side (F13 M3, detail panel model): header with Allow / Block,
  what it matches and where, ⋯ (delete); a one-click bar (On / off, Edit); fact tiles; every value
  (countries with their flags) in a sliding grid; calls it decided per day. Previous (K) · Next (J).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ApiAccessRule } from '#shared/types/apiService'

const props = defineProps<{ id: string | null; ids: string[]; busy: boolean }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string]; edit: [rule: ApiAccessRule]; toggle: [rule: ApiAccessRule, on: boolean]; remove: [rule: ApiAccessRule] }>()
const { t, d } = useI18n()
const api = useApi()
const { number, relative, date } = useFormat()
const format = useRuleFormat()

const rule = ref<ApiAccessRule | null>(null)
const failed = ref(false)
async function load(id: string) {
  failed.value = false
  try {
    const { data } = await api.get<ApiAccessRule>(`/api-access-rules/${id}`)
    if (props.id === id) rule.value = data
  } catch {
    failed.value = true
  }
}
watch(() => [props.id, open.value] as const, ([id, isOpen]) => id && isOpen && void load(id), { immediate: true })
defineExpose({ reload: () => props.id && load(props.id) })

const index = computed(() => (props.id ? props.ids.indexOf(props.id) : -1))
const prev = computed(() => (index.value > 0 ? props.ids[index.value - 1] : null))
const next = computed(() => (index.value >= 0 && index.value < props.ids.length - 1 ? props.ids[index.value + 1] : null))
defineShortcuts({
  j: { usingInput: false, handler: () => open.value && next.value && emit('go', next.value) },
  k: { usingInput: false, handler: () => open.value && prev.value && emit('go', prev.value) },
})
const tiles = computed(() => {
  const r = rule.value
  if (!r) return []
  return [
    { key: 'kind', icon: format.kindIcon(r.kind), label: t('apiService.access.col.kind'), value: format.kindLabel(r.kind) },
    { key: 'scope', icon: 'i-lucide-target', label: t('apiService.access.col.scope'), value: format.scopeText(r.scope) },
    { key: 'hits', icon: 'i-lucide-arrow-left-right', label: t('apiService.access.col.hits'), value: number(r.hits_30d) },
    { key: 'last', icon: 'i-lucide-clock', label: t('apiService.access.col.lastHit'), value: r.last_hit_at ? relative(r.last_hit_at) : t('apiService.access.neverHit') },
    { key: 'by', icon: 'i-lucide-user-round', label: t('apiService.createdBy'), value: `${r.created_by.name} · ${date(r.created_at)}` },
    { key: 'changed', icon: 'i-lucide-pencil', label: t('apiService.col.updated'), value: relative(r.updated_at) },
  ]
})
const points = computed(() => (rule.value?.daily ?? []).map(day => ({ label: d(new Date(`${day.date}T12:00:00`), { day: 'numeric', month: 'short' }), value: day.count })))
const menu = computed<DropdownMenuItem[][]>(() => (rule.value ? [[{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => emit('remove', rule.value!) }]] : []))
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="rule ? format.valuesText(rule) : t('nav.apiAccess')"
    :ui="{ content: 'w-full sm:max-w-2xl', header: 'border-b-0 pb-2', body: 'flex flex-col gap-6 pb-40', footer: 'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4' }"
  >
    <template #header>
      <div v-if="!rule" class="flex w-full items-center gap-3.5">
        <USkeleton class="size-14 rounded-2xl" />
        <div class="flex flex-1 flex-col gap-2"><USkeleton class="h-5 w-48" /><USkeleton class="h-4 w-32" /></div>
      </div>
      <div v-else class="flex w-full flex-col gap-4">
        <div class="flex items-start gap-3.5">
          <span class="flex size-14 shrink-0 items-center justify-center rounded-2xl" :class="rule.action === 'block' ? 'bg-error/10 text-error' : 'bg-inverted text-inverted'"><UIcon :name="rule.action === 'block' ? 'i-lucide-shield-x' : 'i-lucide-shield-check'" class="size-6" /></span>
          <div class="flex min-w-0 flex-1 flex-col gap-1">
            <h2 class="truncate text-lg leading-tight font-semibold text-highlighted" dir="ltr">{{ format.valuesText(rule, 3) }}</h2>
            <p class="truncate text-sm text-muted">{{ rule.note || format.scopeText(rule.scope) }}</p>
            <div class="mt-1 flex flex-wrap items-center gap-1.5">
              <UBadge :label="t(`apiService.access.action.${rule.action}`)" :icon="rule.action === 'block' ? 'i-lucide-ban' : 'i-lucide-check'" :color="rule.action === 'block' ? 'error' : 'success'" variant="subtle" size="sm" class="rounded-md" />
              <UBadge :label="rule.enabled ? t('apiService.access.on') : t('apiService.access.off')" color="neutral" :variant="rule.enabled ? 'outline' : 'soft'" size="sm" class="rounded-md" />
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-1">
            <UDropdownMenu :items="menu" :content="{ align: 'end' }">
              <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="sm" square :aria-label="t('dataView.actions')" />
            </UDropdownMenu>
            <UButton icon="i-lucide-x" color="neutral" variant="soft" size="sm" square class="rounded-full" :aria-label="t('common.close')" @click="open = false" />
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <USwitch :model-value="rule.enabled" :label="t('apiService.access.enabled')" :disabled="busy" @update:model-value="value => emit('toggle', rule!, !!value)" />
          <span class="mx-1 h-5 w-px bg-(--ui-border)" aria-hidden="true" />
          <UButton :label="t('apiService.actions.edit')" icon="i-lucide-pencil" color="neutral" size="sm" @click="emit('edit', rule)" />
        </div>
      </div>
    </template>

    <template #body>
      <AppEmpty v-if="failed && !rule" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" />
      <div v-else-if="!rule" class="flex flex-col gap-4"><div class="grid grid-cols-2 gap-2 sm:grid-cols-3"><USkeleton v-for="n in 6" :key="n" class="h-14 rounded-lg" /></div></div>
      <template v-else>
        <div class="grid grid-cols-2 gap-2 transition-opacity sm:grid-cols-3" :class="busy ? 'opacity-60' : ''">
          <div v-for="tile in tiles" :key="tile.key" class="flex min-w-0 items-center gap-2.5 rounded-lg border border-default p-2.5">
            <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="tile.icon" class="size-4 text-muted" /></span>
            <div class="flex min-w-0 flex-col">
              <span class="truncate text-[11px] text-muted">{{ tile.label }}</span>
              <span class="truncate text-sm font-semibold text-highlighted tabular-nums">{{ tile.value }}</span>
            </div>
          </div>
        </div>
        <ApiConnections :id="rule.id" type="rule" />

        <section class="flex flex-col gap-3">
          <h3 class="text-sm font-semibold text-highlighted">{{ t(`apiService.access.valuesLabel.${rule.kind}`) }} <span class="font-normal text-muted tabular-nums">· {{ rule.values.length }}</span></h3>
          <div class="grid max-h-72 gap-2 overflow-y-auto sm:grid-cols-2">
            <div v-for="value in rule.values" :key="value" class="flex min-w-0 items-center gap-2 rounded-lg border border-default px-3 py-2">
              <UIcon :name="rule.kind === 'country' ? `i-circle-flags-${value.toLowerCase()}` : format.kindIcon(rule.kind)" class="size-4 shrink-0" :class="rule.kind === 'country' ? '' : 'text-muted'" />
              <span class="truncate text-sm text-highlighted" :class="rule.kind === 'ip' || rule.kind === 'domain' ? 'font-mono' : ''" dir="ltr">{{ format.valueText(rule.kind, value) }}</span>
            </div>
          </div>
        </section>

        <section class="flex flex-col gap-3">
          <h3 class="text-sm font-semibold text-highlighted">{{ t('apiService.access.col.hits') }}</h3>
          <ChartsBars v-if="rule.hits_30d" :points="points" height="h-32" :unit="n => t('apiService.callsCount', { n: number(n) }, n)" />
          <p v-else class="text-sm text-muted">{{ t('apiService.access.noHits') }}</p>
        </section>
      </template>
    </template>

    <template #footer>
      <nav class="pointer-events-auto flex items-center gap-1 rounded-full border border-default bg-default/95 p-1 shadow-lg backdrop-blur" :aria-label="t('apiService.navigate')">
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
