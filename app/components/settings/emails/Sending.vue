<!--
  Settings → Emails → Sending address (owner 2026-10-10): where the workspace's emails come from. Three choices,
  one in use: Formalie's address (ready at once), the workspace's own address on a domain it verifies (DNS records
  and a real check), or its own mail server (tested before use). Saves on its own, apart from the page's Save.
-->
<script setup lang="ts">
import type { EmailSending, SendingMode } from '#shared/types/emails'

const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { relative } = useFormat()
const confirm = useConfirm()

const sending = ref<EmailSending | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    sending.value = (await api.get<EmailSending>('/settings/emails/sending')).data
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  }
}
onMounted(load)

const { busy, run } = useBusy()
const set = (value: EmailSending) => (sending.value = value)

// Own address
const address = ref('')
const addDomain = () => run(async () => set((await api.put<EmailSending>('/settings/emails/sending/domain', { address: address.value.trim() })).data))
const checking = ref(false)
async function check() {
  if (checking.value) return
  checking.value = true
  try {
    set((await api.post<EmailSending>('/settings/emails/sending/domain/check')).data)
    const status = sending.value?.domain?.status
    toast.add({ title: t(`settings.address.status.${status}`), color: status === 'verified' ? 'success' : 'warning', icon: status === 'verified' ? 'i-lucide-badge-check' : 'i-lucide-clock' })
  } catch (error) {
    handle(error)
  } finally {
    checking.value = false
  }
}
async function removeDomain() {
  const entry = sending.value?.domain
  if (!entry || !(await confirm({ title: t('settings.sending.removeAddress', { address: entry.address }), description: t('settings.sending.removeDesc'), confirmLabel: t('settings.sending.remove'), danger: true }))) return
  await run(async () => set((await api.del<EmailSending>('/settings/emails/sending/domain')).data))
}

async function use(mode: SendingMode) {
  await run(async () => {
    set((await api.post<EmailSending>('/settings/emails/sending/mode', { mode })).data)
    toast.add({ title: t('settings.sending.nowFrom', { address: sending.value!.from_address }), color: 'success', icon: 'i-lucide-send' })
  })
}

const STATUS_COLOR = { pending: 'warning', verified: 'success', failed: 'error', untested: 'neutral', working: 'success' } as const
const options = computed(() => {
  const value = sending.value
  if (!value) return []
  return [
    { mode: 'formalie' as const, icon: 'i-lucide-file-check-2', title: t('settings.sending.formalie'), hint: value.formalie_address, ready: true },
    { mode: 'domain' as const, icon: 'i-lucide-at-sign', title: t('settings.sending.domain'), hint: value.domain?.address ?? t('settings.sending.domainHint'), ready: value.domain?.status === 'verified' },
    { mode: 'smtp' as const, icon: 'i-lucide-server', title: t('settings.sending.smtp'), hint: value.smtp ? `${value.smtp.host}:${value.smtp.port}` : t('settings.sending.smtpHint'), ready: value.smtp?.status === 'working' },
  ]
})
</script>

<template>
  <AppEmpty v-if="failed && !sending" size="sm" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
  <USkeleton v-else-if="!sending" class="h-40 rounded-lg" />
  <div v-else class="flex flex-col gap-4">
    <p class="flex items-center gap-1.5 text-sm">
      <UIcon name="i-lucide-send" class="size-4 shrink-0 text-muted" /><span class="text-muted">{{ t('settings.sending.current') }}</span>
      <span class="truncate font-mono text-highlighted">{{ sending.from_address }}</span>
    </p>

    <div class="grid grid-cols-1 gap-2 sm:grid-cols-3">
      <div v-for="option in options" :key="option.mode" class="flex h-full flex-col gap-2 rounded-lg border p-3" :class="sending.mode === option.mode ? 'border-inverted bg-elevated/60' : 'border-default'">
        <div class="flex items-center gap-2">
          <UIcon :name="option.icon" class="size-4 shrink-0 text-muted" />
          <span class="min-w-0 flex-1 truncate text-sm font-medium text-highlighted">{{ option.title }}</span>
          <UBadge v-if="sending.mode === option.mode" :label="t('settings.sending.inUse')" color="success" variant="subtle" size="sm" />
        </div>
        <span class="truncate text-xs text-muted">{{ option.hint }}</span>
        <UButton
          v-if="sending.mode !== option.mode"
          :label="t('settings.sending.use')"
          color="neutral"
          variant="outline"
          size="xs"
          class="mt-auto self-start"
          :aria-label="`${t('settings.sending.use')}: ${option.title}`"
          :disabled="!option.ready || busy"
          @click="use(option.mode)"
        />
      </div>
    </div>
    <p class="flex items-start gap-1.5 text-xs text-muted"><UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" />{{ t('settings.sending.markNote') }}</p>

    <!-- Own address on the workspace's domain -->
    <div class="flex flex-col gap-3 rounded-lg border border-default p-3 sm:p-4">
      <h3 class="flex items-center gap-2 text-sm font-medium text-highlighted"><UIcon name="i-lucide-at-sign" class="size-4 text-muted" />{{ t('settings.sending.domain') }}</h3>
      <form v-if="!sending.domain" class="flex flex-col gap-2 sm:flex-row" @submit.prevent="addDomain">
        <UInput v-model="address" type="email" icon="i-lucide-mail" placeholder="forms@example.com" class="w-full sm:max-w-sm" :aria-label="t('settings.sending.addressLabel')" />
        <UButton type="submit" :label="t('settings.sending.addAddress')" icon="i-lucide-plus" color="neutral" variant="outline" :loading="busy" :disabled="!address.trim()" />
      </form>
      <template v-else>
        <div class="flex flex-wrap items-center gap-2">
          <span class="font-mono text-sm text-highlighted">{{ sending.domain.address }}</span>
          <UBadge :label="t(`settings.address.status.${sending.domain.status}`)" :color="STATUS_COLOR[sending.domain.status]" variant="subtle" />
          <span v-if="sending.domain.checked_at" class="text-xs text-muted">{{ t('settings.address.checked', { when: relative(sending.domain.checked_at) }) }}</span>
        </div>
        <p class="text-xs text-muted">{{ sending.domain.status === 'verified' ? t('settings.sending.verifiedDesc') : t('settings.sending.addRecords', { domain: sending.domain.domain }) }}</p>
        <SettingsDnsRecords :records="sending.domain.records" />
        <UAlert v-if="sending.domain.problem" :color="sending.domain.problem === 'wrong_value' ? 'error' : 'neutral'" variant="subtle" icon="i-lucide-info" :description="t(`settings.sending.problem.${sending.domain.problem}`)" />
        <div class="flex flex-wrap gap-2">
          <UButton :label="t('settings.address.check')" icon="i-lucide-refresh-cw" color="neutral" :loading="checking" @click="check" />
          <UButton :label="t('settings.sending.remove')" icon="i-lucide-trash-2" color="error" variant="outline" :disabled="busy" @click="removeDomain" />
        </div>
      </template>
    </div>

    <!-- Own mail server -->
    <SettingsEmailsSmtp :server="sending.smtp" @saved="set" />
  </div>
</template>
