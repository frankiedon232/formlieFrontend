<!--
  Settings → Sign-in → Single sign-on (owner 2026-10-10): one connection to the company's identity provider
  (Okta, Microsoft Entra ID, Google Workspace, OneLogin or any SAML 2.0 / OpenID Connect provider). Pick the
  provider, copy Formalie's values into it, paste its values here, test, then switch it on. On the sign-in page
  people see "Continue with …", and addresses of the chosen domains go straight to the provider (required, if set).
  Saves on its own, apart from the page's Save.
-->
<script setup lang="ts">
import { SSO_ICONS, SSO_NAMES, SSO_PROVIDERS, type SsoProvider, type SsoSettings } from '#shared/types/sso'

const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { relative } = useFormat()
const confirm = useConfirm()
const access = usePlanAccess()

const settings = ref<SsoSettings | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    settings.value = (await api.get<SsoSettings>('/settings/sso')).data
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  }
}
onMounted(load)

/** The provider being set up (a new one, or the saved one being changed). */
const editing = ref<SsoProvider | null>(null)
const connection = computed(() => settings.value?.connection ?? null)

function saved(value: SsoSettings) {
  settings.value = value
  editing.value = null
}

const testing = ref(false)
async function test() {
  if (testing.value) return
  testing.value = true
  try {
    settings.value = (await api.post<SsoSettings>('/settings/sso/test')).data
    const problem = settings.value.connection?.problem
    toast.add({ title: problem ? t(`settings.sso.problem.${problem}`) : t('settings.sso.passed'), color: problem ? 'error' : 'success', icon: problem ? 'i-lucide-circle-x' : 'i-lucide-badge-check' })
  } catch (error) {
    handle(error)
  } finally {
    testing.value = false
  }
}

const { busy, run } = useBusy()
async function setActive(active: boolean) {
  await run(async () => {
    settings.value = (await api.post<SsoSettings>('/settings/sso/status', { active })).data
    toast.add({ title: active ? t('settings.sso.turnedOn') : t('settings.sso.turnedOff'), color: 'success', icon: active ? 'i-lucide-log-in' : 'i-lucide-power-off' })
  })
}
async function remove() {
  if (!connection.value || !(await confirm({ title: t('settings.sso.removeTitle', { name: connection.value.label }), description: t('settings.sso.removeDesc'), confirmLabel: t('settings.sso.remove'), danger: true }))) return
  await run(async () => (settings.value = (await api.del<SsoSettings>('/settings/sso')).data))
}
const STATUS_COLOR = { draft: 'warning', tested: 'neutral', active: 'success' } as const
</script>

<template>
  <AppEmpty v-if="failed && !settings" size="sm" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
  <USkeleton v-else-if="!settings" class="h-40 rounded-lg" />

  <SettingsSigninSsoForm v-else-if="editing" :provider="editing" :connection="connection?.provider === editing ? connection : null" :service-provider="settings.service_provider" @saved="saved" @cancel="editing = null" />

  <div v-else-if="connection" class="flex flex-col gap-3 rounded-lg border border-default p-3 sm:p-4">
    <div class="flex flex-wrap items-center gap-2">
      <UIcon :name="SSO_ICONS[connection.provider]" class="size-5 shrink-0 text-highlighted" />
      <span class="text-sm font-medium text-highlighted">{{ SSO_NAMES[connection.provider] }}</span>
      <UBadge :label="t(`settings.sso.status.${connection.status}`)" :color="STATUS_COLOR[connection.status]" variant="subtle" />
      <span v-if="connection.tested_at" class="text-xs text-muted">{{ t('settings.sso.testedWhen', { when: relative(connection.tested_at) }) }}</span>
    </div>
    <ul class="flex flex-col gap-1 text-xs text-muted">
      <li class="flex items-start gap-1.5"><UIcon name="i-lucide-log-in" class="mt-0.5 size-3.5 shrink-0" />{{ t('settings.sso.buttonShows', { label: connection.label }) }}</li>
      <li class="flex items-start gap-1.5"><UIcon name="i-lucide-at-sign" class="mt-0.5 size-3.5 shrink-0" />{{ connection.domains.length ? t(connection.enforce ? 'settings.sso.sumRequired' : 'settings.sso.sumDomains', { list: connection.domains.join(', ') }) : t('settings.sso.sumAnyone') }}</li>
      <li class="flex items-start gap-1.5"><UIcon name="i-lucide-user-plus" class="mt-0.5 size-3.5 shrink-0" />{{ connection.auto_create ? t('settings.sso.sumCreate') : t('settings.sso.sumInvited') }}</li>
    </ul>
    <BillingLocked v-if="!access.allows('sso')" feature="sso" />
    <UAlert v-if="connection.problem" color="error" variant="subtle" icon="i-lucide-circle-x" :description="t(`settings.sso.problem.${connection.problem}`)" />
    <div class="flex flex-wrap items-center gap-2">
      <UButton :label="t('settings.sso.test')" icon="i-lucide-flask-conical" color="neutral" :variant="connection.status === 'draft' ? 'solid' : 'outline'" :loading="testing" @click="test" />
      <UButton v-if="connection.status !== 'active'" :label="t('settings.sso.turnOn')" icon="i-lucide-power" color="neutral" :variant="connection.status === 'tested' ? 'solid' : 'outline'" :disabled="connection.status === 'draft' || busy" @click="setActive(true)" />
      <UButton v-else :label="t('settings.sso.turnOff')" icon="i-lucide-power-off" color="neutral" variant="outline" :loading="busy" @click="setActive(false)" />
      <UButton :label="t('settings.smtp.edit')" icon="i-lucide-pencil" color="neutral" variant="outline" :disabled="busy" @click="editing = connection.provider" />
      <UButton :label="t('settings.sso.remove')" icon="i-lucide-trash-2" color="error" variant="ghost" :disabled="busy" @click="remove" />
    </div>
    <p v-if="connection.status === 'draft'" class="text-xs text-muted">{{ t('settings.sso.testFirst') }}</p>
  </div>

  <BillingLocked v-else-if="!access.allows('sso')" feature="sso" />
  <div v-else class="flex flex-col gap-3">
    <p class="text-xs text-muted">{{ t('settings.sso.pick') }}</p>
    <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
      <UButton v-for="provider in SSO_PROVIDERS" :key="provider" :label="SSO_NAMES[provider]" :icon="SSO_ICONS[provider]" color="neutral" variant="outline" class="justify-start" :ui="{ label: 'truncate' }" @click="editing = provider" />
    </div>
  </div>
</template>
