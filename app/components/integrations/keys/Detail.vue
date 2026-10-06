<!--
  An API key in a panel from the side (F13 M6, detail panel model): header with its name, preview,
  status and ⋯ (delete once revoked or expired); a one-click bar (Edit, Revoke); fact tiles; then
  What it may do · Calls · How to call (chips). Previous (K) · position · Next (J). Esc closes.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ManagementKey } from '#shared/types/integrations'

const props = defineProps<{ id: string | null; ids: string[]; busy: boolean; base: string }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string]; edit: [key: ManagementKey]; revoke: [key: ManagementKey]; remove: [key: ManagementKey] }>()
const { t, d } = useI18n()
const api = useApi()
const { number, relative, date } = useFormat()

const apiKey = ref<ManagementKey | null>(null)
const failed = ref(false)
async function load(id: string) {
  failed.value = false
  try {
    const { data } = await api.get<ManagementKey>(`/api-keys/${id}`)
    if (props.id === id) apiKey.value = data
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
const done = computed(() => apiKey.value?.status === 'revoked' || apiKey.value?.status === 'expired')
const tiles = computed(() => {
  const k = apiKey.value
  if (!k) return []
  return [
    { key: 'calls', icon: 'i-lucide-arrow-left-right', label: t('integrations.keys.col.calls'), value: number(k.calls_30d) },
    { key: 'last', icon: 'i-lucide-clock', label: t('integrations.keys.col.lastUsed'), value: k.last_used_at ? relative(k.last_used_at) : t('integrations.keys.neverUsed') },
    { key: 'ip', icon: 'i-lucide-globe', label: t('integrations.keys.lastFrom'), value: k.last_used_ip ?? '–' },
    { key: 'expires', icon: 'i-lucide-calendar-clock', label: t('apiService.tokens.col.expires'), value: k.expires_at ? date(k.expires_at) : t('apiService.tokens.never') },
    { key: 'by', icon: 'i-lucide-user-round', label: t('apiService.createdBy'), value: `${k.created_by.name} · ${date(k.created_at)}` },
    { key: 'revoked', icon: 'i-lucide-ban', label: t('status.revoked'), value: k.revoked_at ? date(k.revoked_at) : '–' },
  ]
})
const tab = ref<'scopes' | 'calls' | 'use'>('scopes')
const chips = computed(() => [
  { key: 'scopes' as const, label: t('integrations.keys.col.scopes'), count: apiKey.value?.scopes.length ?? 0 },
  { key: 'calls' as const, label: t('integrations.keys.col.calls'), count: apiKey.value?.calls_30d ?? 0 },
  { key: 'use' as const, label: t('integrations.keys.howToCall'), count: null },
])
const points = computed(() => (apiKey.value?.daily ?? []).map(day => ({ label: d(new Date(`${day.date}T12:00:00`), { day: 'numeric', month: 'short' }), value: day.count })))
const example = computed(() => `curl "${props.base}/v1/forms?per_page=20" \\\n  -H "Authorization: Bearer formalie_key_…"`)
const menu = computed<DropdownMenuItem[][]>(() => (apiKey.value && done.value ? [[{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => emit('remove', apiKey.value!) }]] : []))
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="apiKey?.name ?? t('nav.apiKeys')"
    :ui="{ content: 'w-full sm:max-w-2xl', header: 'border-b-0 pb-2', body: 'flex flex-col gap-6 pb-40', footer: 'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4' }"
  >
    <template #header>
      <div v-if="!apiKey" class="flex w-full items-center gap-3.5">
        <USkeleton class="size-14 rounded-2xl" />
        <div class="flex flex-1 flex-col gap-2"><USkeleton class="h-5 w-48" /><USkeleton class="h-4 w-32" /></div>
      </div>
      <div v-else class="flex w-full flex-col gap-4">
        <div class="flex items-start gap-3.5">
          <span class="flex size-14 shrink-0 items-center justify-center rounded-2xl" :class="done ? 'bg-elevated text-muted' : 'bg-inverted text-inverted'"><UIcon name="i-lucide-key-round" class="size-6" /></span>
          <div class="flex min-w-0 flex-1 flex-col gap-1">
            <h2 class="truncate text-lg leading-tight font-semibold text-highlighted">{{ apiKey.name }}</h2>
            <p class="truncate font-mono text-xs text-muted" dir="ltr">{{ apiKey.preview }}</p>
            <div class="mt-1 flex flex-wrap items-center gap-1.5"><DataStatusBadge :status="apiKey.status" /></div>
          </div>
          <div class="flex shrink-0 items-center gap-1">
            <UDropdownMenu v-if="menu.length" :items="menu" :content="{ align: 'end' }">
              <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="sm" square :aria-label="t('dataView.actions')" />
            </UDropdownMenu>
            <UButton icon="i-lucide-x" color="neutral" variant="soft" size="sm" square class="rounded-full" :aria-label="t('common.close')" @click="open = false" />
          </div>
        </div>
        <div v-if="apiKey.status !== 'revoked'" class="flex flex-wrap items-center gap-2">
          <UButton :label="t('apiService.actions.edit')" icon="i-lucide-pencil" color="neutral" size="sm" :disabled="busy" @click="emit('edit', apiKey)" />
          <UButton :label="t('integrations.keys.revoke')" icon="i-lucide-ban" color="error" variant="outline" size="sm" :disabled="busy" @click="emit('revoke', apiKey)" />
        </div>
      </div>
    </template>

    <template #body>
      <AppEmpty v-if="failed && !apiKey" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" />
      <div v-else-if="!apiKey" class="flex flex-col gap-4"><div class="grid grid-cols-2 gap-2 sm:grid-cols-3"><USkeleton v-for="n in 6" :key="n" class="h-14 rounded-lg" /></div></div>
      <template v-else>
        <UAlert v-if="apiKey.status === 'expiring'" icon="i-lucide-calendar-clock" color="warning" variant="subtle" :title="t('integrations.keys.expiringTitle', { when: relative(apiKey.expires_at!) })" :description="t('integrations.keys.expiringDesc')" />
        <AppSecretReveal v-if="apiKey.status !== 'revoked'" :preview="apiKey.preview" :endpoint="`/api-keys/${apiKey.id}/reveal`" :title="t('integrations.keys.secret')" :labels="{ secret: t('integrations.keys.secret') }" />
        <div class="grid grid-cols-2 gap-2 transition-opacity sm:grid-cols-3" :class="busy ? 'opacity-60' : ''">
          <div v-for="tile in tiles" :key="tile.key" class="flex min-w-0 items-center gap-2.5 rounded-lg border border-default p-2.5">
            <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="tile.icon" class="size-4 text-muted" /></span>
            <div class="flex min-w-0 flex-col">
              <span class="truncate text-[11px] text-muted">{{ tile.label }}</span>
              <span class="truncate text-sm font-semibold text-highlighted tabular-nums" :class="tile.key === 'ip' ? 'font-mono text-xs' : ''">{{ tile.value }}</span>
            </div>
          </div>
        </div>

        <section class="flex flex-col gap-3">
          <div class="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1" role="tablist">
            <UButton v-for="chip in chips" :key="chip.key" :label="chip.label" role="tab" :aria-selected="tab === chip.key" color="neutral" :variant="tab === chip.key ? 'solid' : 'outline'" size="sm" class="shrink-0 rounded-full" @click="tab = chip.key">
              <template v-if="chip.count !== null" #trailing><span class="text-xs tabular-nums opacity-70">{{ chip.count }}</span></template>
            </UButton>
          </div>
          <div v-if="tab === 'scopes'" class="grid gap-2 sm:grid-cols-2">
            <div v-for="scope in apiKey.scopes" :key="scope" class="flex h-full min-w-0 flex-col gap-0.5 rounded-lg border border-default px-3 py-2">
              <span class="text-sm font-medium text-highlighted">{{ t(`integrations.keys.scope.${scope.replace(':', '_')}`) }}</span>
              <span class="text-xs text-muted">{{ t(`integrations.keys.scopeHint.${scope.replace(':', '_')}`) }}</span>
              <code class="mt-1 font-mono text-[11px] text-muted">{{ scope }}</code>
            </div>
          </div>
          <template v-else-if="tab === 'calls'">
            <ChartsBars v-if="apiKey.calls_30d" :points="points" height="h-32" :unit="n => t('apiService.callsCount', { n: number(n) }, n)" />
            <AppEmpty v-else size="sm" icon="i-lucide-arrow-left-right" :title="t('integrations.keys.noCalls')" />
          </template>
          <div v-else class="flex flex-col gap-2">
            <p class="text-sm text-muted">{{ t('integrations.keys.howToCallText') }}</p>
            <pre class="overflow-x-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-highlighted" dir="ltr">{{ example }}</pre>
            <ul class="flex flex-col gap-1 font-mono text-xs text-muted" dir="ltr">
              <li>GET /v1/forms · GET /v1/forms/{id} · PATCH /v1/forms/{id}</li>
              <li>GET /v1/forms/{id}/responses · GET · PATCH · DELETE /v1/responses/{id}</li>
              <li>GET /v1/webhooks · GET /v1/audit</li>
            </ul>
          </div>
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
