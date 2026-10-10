<!--
  A token in a panel from the side (F13 M2, detail panel model): header with its name, visible part,
  status, live / test and ⋯ (edit, delete when revoked or expired); a one-click bar (Rotate, Revoke);
  fact tiles; what it may call; calls per day. Previous (K) · position · Next (J).
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ApiToken } from '#shared/types/apiService'

const props = defineProps<{ id: string | null; ids: string[]; busy: boolean }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string]; edit: [token: ApiToken]; rotate: [token: ApiToken]; revoke: [token: ApiToken]; remove: [token: ApiToken] }>()
const { t, d } = useI18n()
const api = useApi()
const { number, relative, dateTime, date } = useFormat()
const format = useTokenFormat()
// Changing a token or showing its secret needs api.tokens (F22 R2 M4)
const { can } = useCan()
const manage = computed(() => can('api.tokens'))

const token = ref<ApiToken | null>(null)
const failed = ref(false)
async function load(id: string) {
  failed.value = false
  try {
    const { data } = await api.get<ApiToken>(`/api-tokens/${id}`)
    if (props.id === id) token.value = data
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

const ended = computed(() => token.value?.status === 'revoked' || token.value?.status === 'expired')
const tiles = computed(() => {
  const k = token.value
  if (!k) return []
  return [
    { key: 'kind', icon: 'i-lucide-key-round', label: t('apiService.tokens.col.kind'), value: format.kindLabel(k) },
    { key: 'expires', icon: 'i-lucide-calendar-clock', label: t('apiService.tokens.col.expires'), value: format.expiresText(k) },
    { key: 'used', icon: 'i-lucide-clock', label: t('apiService.tokens.col.lastUsed'), value: k.last_used_at ? relative(k.last_used_at) : t('apiService.tokens.notUsed') },
    { key: 'calls', icon: 'i-lucide-arrow-left-right', label: t('apiService.col.calls'), value: number(k.calls_30d) },
    { key: 'lifetime', icon: 'i-lucide-timer', label: t('apiService.tokens.lifetime'), value: k.lifetime_minutes ? t('apiService.tokens.minutes', { n: k.lifetime_minutes }) : '–' },
    { key: 'by', icon: 'i-lucide-user-round', label: t('apiService.createdBy'), value: `${k.created_by.name} · ${date(k.created_at)}` },
  ]
})
const points = computed(() => (token.value?.daily ?? []).map(day => ({ label: d(new Date(`${day.date}T12:00:00`), { day: 'numeric', month: 'short' }), value: day.count })))
const menu = computed<DropdownMenuItem[][]>(() => {
  const k = token.value
  if (!k || !manage.value) return []
  return [
    ...(k.status !== 'revoked' ? [[{ label: t('apiService.actions.edit'), icon: 'i-lucide-pencil', onSelect: () => emit('edit', k) }]] : []),
    ...(ended.value ? [[{ label: t('apiService.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => emit('remove', k) }]] : []),
  ]
})
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="token?.name || t('nav.apiAuth')"
    :ui="{ content: 'w-full sm:max-w-2xl', header: 'border-b-0 pb-2', body: 'flex flex-col gap-6 pb-40', footer: 'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4' }"
  >
    <template #header>
      <div v-if="!token" class="flex w-full items-center gap-3.5">
        <USkeleton class="size-14 rounded-2xl" />
        <div class="flex flex-1 flex-col gap-2"><USkeleton class="h-5 w-48" /><USkeleton class="h-4 w-32" /></div>
      </div>
      <div v-else class="flex w-full flex-col gap-4">
        <div class="flex items-start gap-3.5">
          <span class="flex size-14 shrink-0 items-center justify-center rounded-2xl" :class="ended ? 'bg-elevated text-muted' : 'bg-inverted text-inverted'"><UIcon :name="token.kind === 'client' ? 'i-lucide-key-square' : 'i-lucide-key-round'" class="size-6" /></span>
          <div class="flex min-w-0 flex-1 flex-col gap-1">
            <h2 class="truncate text-lg leading-tight font-semibold text-highlighted">{{ token.name }}</h2>
            <p class="truncate font-mono text-xs text-muted" dir="ltr">{{ token.preview }}</p>
            <div class="mt-1 flex flex-wrap items-center gap-1.5">
              <DataStatusBadge :status="token.status" />
              <UBadge :label="t(`apiService.tokens.mode.${token.mode}`)" :icon="token.mode === 'test' ? 'i-lucide-flask-conical' : 'i-lucide-zap'" color="neutral" :variant="token.mode === 'test' ? 'soft' : 'outline'" size="sm" class="rounded-md" />
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-1">
            <UDropdownMenu v-if="menu.length" :items="menu" :content="{ align: 'end' }">
              <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="sm" square :aria-label="t('dataView.actions')" />
            </UDropdownMenu>
            <UButton icon="i-lucide-x" color="neutral" variant="soft" size="sm" square class="rounded-full" :aria-label="t('common.close')" @click="open = false" />
          </div>
        </div>
        <div v-if="token.status !== 'revoked' && manage" class="flex flex-wrap items-center gap-2">
          <UButton :label="t('apiService.tokens.rotate')" icon="i-lucide-refresh-cw" color="neutral" size="sm" :disabled="busy" @click="emit('rotate', token)" />
          <UButton :label="t('apiService.tokens.revoke')" icon="i-lucide-ban" color="error" variant="outline" size="sm" :disabled="busy" @click="emit('revoke', token)" />
        </div>
      </div>
    </template>

    <template #body>
      <AppEmpty v-if="failed && !token" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" />
      <div v-else-if="!token" class="flex flex-col gap-4">
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <USkeleton v-for="n in 6" :key="n" class="h-14 rounded-lg" />
        </div>
      </div>
      <template v-else>
        <UAlert v-if="token.rotating_until" icon="i-lucide-refresh-cw" color="warning" variant="subtle" :title="t('apiService.tokens.rotating', { until: dateTime(token.rotating_until) })" />
        <UAlert v-if="token.status === 'revoked'" icon="i-lucide-ban" color="error" variant="subtle" :title="t('apiService.tokens.revokedOn', { date: dateTime(token.revoked_at!) })" :description="t('apiService.tokens.revokedDesc')" />
        <UAlert v-if="token.scope_gone && token.status !== 'revoked'" icon="i-lucide-triangle-alert" color="warning" variant="subtle" :title="t('apiService.tokens.scopeGone.title', { n: token.scope_gone }, token.scope_gone)" :description="t('apiService.tokens.scopeGone.text')" :actions="manage ? [{ label: t('apiService.actions.edit'), icon: 'i-lucide-pencil', color: 'neutral', variant: 'outline', size: 'xs', onClick: () => emit('edit', token!) }] : []" />
        <AppSecretReveal v-if="token.status !== 'revoked' && manage" :preview="token.kind === 'client' ? (token.client_id ?? token.preview) : token.preview" :endpoint="`/api-tokens/${token.id}/reveal`" :viewable="token.viewable" :title="t('apiService.tokens.secret.title')" :labels="{ token: t('apiService.tokens.secret.token'), client_secret: t('apiService.tokens.secret.clientSecret') }" />
        <div class="grid grid-cols-2 gap-2 transition-opacity sm:grid-cols-3" :class="busy ? 'opacity-60' : ''">
          <div v-for="tile in tiles" :key="tile.key" class="flex min-w-0 items-center gap-2.5 rounded-lg border border-default p-2.5">
            <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="tile.icon" class="size-4 text-muted" /></span>
            <div class="flex min-w-0 flex-col">
              <span class="truncate text-[11px] text-muted">{{ tile.label }}</span>
              <span class="truncate text-sm font-semibold text-highlighted tabular-nums">{{ tile.value }}</span>
            </div>
          </div>
        </div>
        <ApiConnections :id="token.id" type="token" />

        <p v-if="token.kind === 'webhook'" class="flex items-start gap-2 rounded-lg border border-default p-3 text-sm text-muted"><UIcon name="i-lucide-webhook" class="mt-0.5 size-4 shrink-0" />{{ t('apiService.tokens.webhookScope') }}</p>
        <section v-else class="flex flex-col gap-3">
          <h3 class="text-sm font-semibold text-highlighted">{{ t('apiService.tokens.scope.title') }}</h3>
          <div class="grid gap-2 sm:grid-cols-3">
            <div class="flex h-full flex-col gap-1.5 rounded-lg border border-default p-3">
              <span class="text-[11px] text-muted">{{ t('nav.apiServices') }}</span>
              <span class="text-sm text-highlighted">{{ token.scope_names.services.join(', ') || (token.scopes.services.length ? t('apiService.tokens.scope.gone') : t('apiService.tokens.scope.allServices')) }}</span>
            </div>
            <div class="flex h-full flex-col gap-1.5 rounded-lg border border-default p-3">
              <span class="text-[11px] text-muted">{{ t('nav.apiEndpoints') }}</span>
              <span class="text-sm text-highlighted" :class="token.scope_names.endpoints.length ? 'font-mono' : ''" dir="ltr">{{ token.scope_names.endpoints.map(name => `/${name}`).join(', ') || (token.scopes.endpoints.length ? t('apiService.tokens.scope.gone') : t('apiService.tokens.scope.allEndpoints')) }}</span>
            </div>
            <div class="flex h-full flex-col gap-1.5 rounded-lg border border-default p-3">
              <span class="text-[11px] text-muted">{{ t('apiService.col.methods') }}</span>
              <ApiMethods v-if="token.scopes.methods.length" :methods="token.scopes.methods" size="xs" />
              <span v-else class="text-sm text-highlighted">{{ t('apiService.tokens.scope.allMethods') }}</span>
            </div>
          </div>
        </section>

        <section class="flex flex-col gap-3">
          <h3 class="text-sm font-semibold text-highlighted">{{ t('apiService.kpi.calls') }}</h3>
          <ChartsBars v-if="token.calls_30d" :points="points" height="h-32" :unit="n => t('apiService.callsCount', { n: number(n) }, n)" />
          <p v-else class="text-sm text-muted">{{ t('apiService.noCalls') }}</p>
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
