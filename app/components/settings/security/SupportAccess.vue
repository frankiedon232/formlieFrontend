<!--
  Settings → Security → Formalie support access (B16). Off: a plain line of what it means, how long
  (1 hour, 24 hours, 7 days) and how much (read only, or changes too), Turn on. On: who allowed it, the
  mode, a live countdown, Extend or change, Turn off (asks first; live support sessions end at once).
  Below: Formalie's open requests (Approve / Decline) and the latest support sessions. Changing needs
  settings.manage; people who may only look see the state without the buttons.
-->
<script setup lang="ts">
import type { SupportAccessState, SupportAllowRequest, SupportHours, SupportMode, SupportRequest } from '#shared/types/support'
import { SUPPORT_HOURS, SUPPORT_MODES } from '#shared/types/support'

const { t } = useI18n()
const api = useApi()
const toast = useToast()
const confirm = useConfirm()
const { handle, normalise } = useErrorHandler()
const { dateTime } = useFormat()
const canManage = computed(() => useCan().can('settings.manage'))
// A Formalie support session never sees or changes the consent itself (the server refuses it too)
const isSupport = computed(() => !!useSession().user.value?.support)
// A one-second clock for the countdown
const now = ref(Date.now())
useIntervalFn(() => (now.value = Date.now()), 1000)

const state = ref<SupportAccessState | null>(null)
const failed = ref(false)
/** Which action runs: 'allow', 'off', or a request id (approve / decline). */
const busy = ref<string | null>(null)
const choice = reactive<{ hours: SupportHours; mode: SupportMode }>({ hours: 24, mode: 'read' })
const editing = ref(false)

async function load() {
  failed.value = false
  try {
    state.value = (await api.get<SupportAccessState>('/settings/security/support-access', undefined, { background: !!state.value })).data
  } catch {
    failed.value = true
  }
}
onMounted(() => !isSupport.value && void load())

const grant = computed(() => state.value?.grant ?? null)
const left = computed(() => msLeft(grant.value?.expires_at, now.value))
// The grant ran out while the page was open: show it as off after the next check
watch(left, value => value === 0 && void load())

const hoursLabel = (hours: number) => (hours >= 24 ? t('settings.security.days', { n: hours / 24 }, hours / 24) : t('settings.security.hours', { n: hours }, hours))
const hourItems = computed(() => (state.value?.hours ?? [...SUPPORT_HOURS]).map(value => ({ value, label: hoursLabel(value) })))
const modeItems = computed(() => (state.value?.modes ?? [...SUPPORT_MODES]).map(value => ({ value, label: t(`support.access.mode.${value}`), description: t(`support.access.modeHint.${value}`) })))

async function change(key: string, work: () => Promise<{ data: SupportAccessState }>, success: string) {
  if (busy.value) return
  busy.value = key
  try {
    state.value = (await work()).data
    editing.value = false
    toast.add({ title: success, color: 'success', icon: 'i-lucide-circle-check' })
  } catch (error) {
    const failure = normalise(error)
    // The request was answered elsewhere or ran out: say so and show what is true now
    if (failure.code === 'FRM-GEN-1009' || failure.code === 'FRM-GEN-1004') {
      toast.add({ title: t('support.access.requestGone'), color: 'warning', icon: 'i-lucide-info' })
      void load()
    } else handle(failure)
  } finally {
    busy.value = null
  }
}

const allow = (body: SupportAllowRequest, key: string, success: string) => change(key, () => api.post<SupportAccessState>('/settings/security/support-access', body), success)
const turnOn = () => allow({ hours: choice.hours, mode: choice.mode }, 'allow', grant.value ? t('support.access.changed') : t('support.access.turnedOn'))
const approve = (request: SupportRequest) => allow({ hours: request.hours, mode: request.mode, request_id: request.id }, request.id, t('support.access.approved', { name: request.staff_name }))
const decline = (request: SupportRequest) => change(request.id, () => api.post<SupportAccessState>(`/settings/security/support-access/requests/${request.id}/decline`), t('support.access.declined'))

async function turnOff() {
  const live = state.value?.sessions.some(item => item.active) ?? false
  if (!(await confirm({ title: t('support.access.offTitle'), description: live ? t('support.access.offDescLive') : t('support.access.offDesc'), confirmLabel: t('support.access.turnOff'), danger: true }))) return
  await change('off', () => api.del<SupportAccessState>('/settings/security/support-access'), t('support.access.turnedOff'))
}

function startEdit() {
  if (grant.value) Object.assign(choice, { hours: grant.value.hours, mode: grant.value.mode })
  editing.value = true
}
</script>

<template>
  <AppEmpty v-if="isSupport" size="xs" icon="i-lucide-lock" :title="t('errors.detail.notInSupportSessions')" />
  <AppEmpty v-else-if="failed && !state" size="xs" icon="i-lucide-cloud-off" :title="t('support.access.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
  <div v-else-if="!state" class="flex flex-col gap-3"><USkeleton class="h-24 rounded-lg" /><USkeleton class="h-16 rounded-lg" /></div>
  <template v-else>
    <!-- On: who, how much, how long -->
    <div v-if="grant" class="flex flex-col gap-3 rounded-lg border border-default p-3 sm:p-4" :class="busy === 'off' ? 'opacity-60' : ''">
      <div class="flex flex-wrap items-center gap-2">
        <UBadge :label="t('support.access.on')" color="success" variant="subtle" icon="i-lucide-circle-check" />
        <UBadge :label="t(`support.access.mode.${grant.mode}`)" color="neutral" variant="outline" :icon="grant.mode === 'write' ? 'i-lucide-pencil' : 'i-lucide-eye'" />
        <span class="ms-auto font-mono text-sm font-semibold text-highlighted tabular-nums" role="timer" :aria-label="t('support.access.timeLeft')">{{ countdownText(left ?? 0) }}</span>
      </div>
      <dl class="grid gap-x-6 gap-y-1.5 text-xs sm:grid-cols-2">
        <div class="flex min-w-0 gap-1.5"><dt class="text-muted">{{ t('support.access.grantedBy') }}</dt><dd class="truncate font-medium text-highlighted">{{ grant.granted_by.name || t('support.access.someone') }}</dd></div>
        <div class="flex min-w-0 gap-1.5"><dt class="text-muted">{{ t('support.access.ends') }}</dt><dd class="truncate font-medium text-highlighted">{{ dateTime(grant.expires_at) }}</dd></div>
      </dl>
      <div v-if="canManage && !editing" class="flex flex-wrap gap-2">
        <UButton :label="t('support.access.extend')" icon="i-lucide-clock-plus" color="neutral" variant="outline" size="sm" :disabled="!!busy" @click="startEdit" />
        <UButton :label="t('support.access.turnOff')" icon="i-lucide-power" color="error" variant="outline" size="sm" :loading="busy === 'off'" :disabled="!!busy" @click="turnOff" />
      </div>
    </div>
    <p v-else class="text-sm text-muted">{{ t('support.access.offExplain') }}</p>

    <!-- Turn on, or extend / change -->
    <div v-if="canManage && (!grant || editing)" class="flex flex-col gap-4">
      <UFormField :label="t('support.access.howLong')">
        <URadioGroup v-model="choice.hours" :items="hourItems" orientation="horizontal" variant="card" color="neutral" :ui="{ fieldset: 'grid grid-cols-3 gap-2', item: 'w-full justify-center' }" />
      </UFormField>
      <UFormField :label="t('support.access.howMuch')">
        <URadioGroup v-model="choice.mode" :items="modeItems" variant="card" color="neutral" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2', item: 'w-full' }" />
      </UFormField>
      <p class="text-xs text-muted">{{ grant ? t('support.access.extendHint', { time: hoursLabel(choice.hours) }) : t('support.access.onHint') }}</p>
      <div class="flex flex-wrap gap-2">
        <UButton :label="grant ? t('support.access.save') : t('support.access.turnOn')" :icon="grant ? 'i-lucide-check' : 'i-lucide-life-buoy'" color="neutral" size="sm" :loading="busy === 'allow'" :disabled="!!busy && busy !== 'allow'" @click="turnOn" />
        <UButton v-if="editing" :label="t('common.cancel')" color="neutral" variant="ghost" size="sm" :disabled="!!busy" @click="editing = false" />
      </div>
    </div>
    <p v-else-if="!canManage" class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-lock" class="size-3.5 shrink-0" />{{ t('support.access.viewOnly') }}</p>

    <SettingsSecuritySupportRequests v-if="state.requests.length" :requests="state.requests" :busy="busy" :can-manage="canManage" @approve="approve" @decline="decline" />
    <SettingsSecuritySupportSessions :sessions="state.sessions" />
  </template>
</template>
