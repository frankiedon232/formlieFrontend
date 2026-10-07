<!--
  Settings → Security (F14 M3): how long people stay signed in (idle time out, maximum length; under
  the 1-hour minimum shows a warning), and who is signed in right now: device, address, last activity,
  sign out one, or everyone but you (asks first). Your own session is marked and can't be ended here.
-->
<script setup lang="ts">
import type { ActiveSession, SecuritySettings } from '#shared/types/settings'
import { IDLE_MINUTES, IDLE_MINUTES_SAFE, MAX_SESSION_HOURS } from '#shared/utils/settings/schemas'

const model = defineModel<SecuritySettings['sessions']>({ required: true })
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const confirm = useConfirm()
const { handle } = useErrorHandler()
const { relative, dateTime, number } = useFormat()

const minutes = (value: number) => (value < 60 ? t('settings.signin.minutes', { n: value }, value) : t('settings.security.hours', { n: value / 60 }, value / 60))
const idles = computed(() => IDLE_MINUTES.map((value): { value: number; label: string } => ({ value, label: minutes(value) })))
const maxes = computed(() => MAX_SESSION_HOURS.map((value): { value: number; label: string } => ({ value, label: value % 24 ? t('settings.security.hours', { n: value }, value) : t('settings.security.days', { n: value / 24 }, value / 24) })))

const list = ref<ActiveSession[] | null>(null)
const failed = ref(false)
const busy = ref<string | null>(null)
async function load() {
  failed.value = false
  try {
    list.value = (await api.get<ActiveSession[]>('/settings/security/sessions', undefined, { background: !!list.value })).data
  } catch {
    failed.value = true
  }
}
onMounted(load)
const others = computed(() => (list.value ?? []).filter(item => !item.current))

async function signOut(body: { ids: string[] } | { everyone_else: true }, key: string) {
  if (busy.value) return
  busy.value = key
  try {
    const { data } = await api.post<{ signed_out: number }>('/settings/security/sessions/sign-out', body)
    toast.add({ title: t('settings.security.signedOut', { n: data.signed_out }, data.signed_out), color: 'success', icon: 'i-lucide-log-out' })
    await load()
  } catch (error) {
    handle(error)
  } finally {
    busy.value = null
  }
}
const signOutOne = (item: ActiveSession) => signOut({ ids: [item.id] }, item.id)
async function signOutAll() {
  if (await confirm({ title: t('settings.security.allTitle'), description: t('settings.security.allDesc', { n: others.value.length }, others.value.length), confirmLabel: t('settings.security.allConfirm'), danger: true })) await signOut({ everyone_else: true }, 'all')
}
const DEVICE_ICONS = { desktop: 'i-lucide-monitor', mobile: 'i-lucide-smartphone', tablet: 'i-lucide-tablet', unknown: 'i-lucide-circle-help' } as const
const deviceOf = (item: ActiveSession) => [item.device.browser, item.device.os].filter(Boolean).join(' · ') || t('settings.security.unknownDevice')
</script>

<template>
  <div class="grid gap-4 sm:grid-cols-2">
    <UFormField :label="t('settings.security.idle')" :description="t('settings.security.idleHint')">
      <USelect v-model="model.idle_minutes" :items="idles" class="w-full" />
    </UFormField>
    <UFormField :label="t('settings.security.max')" :description="t('settings.security.maxHint')">
      <USelect v-model="model.max_hours" :items="maxes" class="w-full" />
    </UFormField>
  </div>
  <UAlert v-if="model.idle_minutes < IDLE_MINUTES_SAFE" color="warning" variant="subtle" icon="i-lucide-clock-alert" :title="t('settings.security.idleShort')" :description="t('settings.security.idleShortDesc')" />

  <div class="flex flex-col rounded-lg border border-default">
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-default px-3 py-2">
      <span class="text-xs font-medium text-highlighted">{{ t('settings.security.active', { n: number(list?.length ?? 0) }, list?.length ?? 0) }}</span>
      <UButton :label="t('settings.security.allConfirm')" icon="i-lucide-log-out" color="error" variant="outline" size="xs" :disabled="!others.length" :loading="busy === 'all'" @click="signOutAll" />
    </div>
    <AppEmpty v-if="failed && !list" size="xs" icon="i-lucide-cloud-off" :title="t('settings.security.sessionsFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
    <div v-else-if="!list" class="flex flex-col gap-2 p-3"><USkeleton v-for="n in 2" :key="n" class="h-10" /></div>
    <ul v-else class="flex max-h-72 flex-col divide-y divide-default overflow-y-auto">
      <li v-for="item in list" :key="item.id" class="flex items-center gap-3 px-3 py-2.5" :class="busy === item.id ? 'opacity-60' : ''">
        <span class="flex size-8 shrink-0 items-center justify-center rounded-lg border border-default"><UIcon :name="DEVICE_ICONS[item.device.type]" class="size-4 text-muted" /></span>
        <span class="flex min-w-0 flex-1 flex-col">
          <span class="flex min-w-0 items-center gap-2">
            <span class="truncate text-sm font-medium text-highlighted">{{ item.user.name }}</span>
            <UBadge v-if="item.current" :label="t('settings.security.thisDevice')" color="neutral" variant="solid" size="xs" class="shrink-0" />
          </span>
          <span class="truncate text-xs text-muted">{{ deviceOf(item) }}<template v-if="item.ip !== 'unknown'"> · <span class="font-mono">{{ item.ip }}</span></template></span>
        </span>
        <UTooltip :text="t('settings.security.since', { when: dateTime(item.started_at) })"><span class="hidden shrink-0 text-xs whitespace-nowrap text-muted sm:inline">{{ relative(item.last_active_at) }}</span></UTooltip>
        <UButton v-if="!item.current" icon="i-lucide-log-out" color="neutral" variant="ghost" size="xs" :loading="busy === item.id" :disabled="!!busy" :aria-label="t('settings.security.signOutOne', { name: item.user.name })" @click="signOutOne(item)" />
        <span v-else class="size-6 shrink-0" />
      </li>
    </ul>
  </div>
</template>
