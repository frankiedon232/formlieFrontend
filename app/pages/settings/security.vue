<!--
  Settings → Security (F14 M3): sign-in activity on top (last 14 days, latest attempts, links to the
  audit trail), then the password rules, how long sessions last with who is signed in now, and the IP
  allowlist. Save applies the rules at once: new passwords, every request (idle and maximum session
  length, allowed networks) and sign-in (expired passwords set a new one first).
-->
<script setup lang="ts">
import type { SecurityActivity } from '#shared/types/settings'
import { securitySchema } from '#shared/utils/settings/schemas'

definePageMeta({ breadcrumb: 'settings.nav.security' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.security') })
const api = useApi()
const form = useSettingsForm('security', { schema: securitySchema })
const { draft, errorOf } = form

const activity = ref<SecurityActivity | null>(null)
const activityFailed = ref(false)
async function loadActivity() {
  activityFailed.value = false
  try {
    activity.value = (await api.get<SecurityActivity>('/settings/security/activity', undefined, { background: !!activity.value })).data
  } catch {
    activityFailed.value = true
  }
}
onMounted(loadActivity)
</script>

<template>
  <SettingsPage id="settings-security" :title="t('settings.nav.security')" :subtitle="t('settings.desc.security')" icon="i-lucide-shield-check" :form="{ dirty: form.dirty.value, saving: form.saving.value, updated: form.updated.value }" @save="form.save" @discard="form.discard">
    <AppEmpty v-if="form.failed.value && !draft" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => form.reload() }]" />
    <div v-else-if="!draft" class="flex flex-col gap-6"><USkeleton class="h-44 rounded-xl" /><USkeleton v-for="n in 3" :key="n" class="h-36 rounded-lg" /></div>
    <div v-else class="flex flex-col gap-8">
      <SettingsSecurityActivity :activity="activity" :failed="activityFailed" @retry="loadActivity" />

      <div class="flex min-w-0 flex-col gap-6">
        <SettingsBlock :title="t('settings.security.password')" :description="t('settings.security.passwordHint')" icon="i-lucide-key-round">
          <SettingsSecurityPassword v-model="draft.password" />
        </SettingsBlock>
        <SettingsBlock :title="t('settings.security.sessions')" :description="t('settings.security.sessionsHint')" icon="i-lucide-timer">
          <SettingsSecuritySessions v-model="draft.sessions" />
        </SettingsBlock>
        <SettingsBlock :title="t('settings.security.network')" :description="t('settings.security.networkHint')" icon="i-lucide-network">
          <SettingsSecurityNetwork v-model="draft.ip_allowlist" :my-ip="activity?.my_ip ?? null" />
          <p v-if="errorOf('ip_allowlist.entries')" class="text-xs text-error">{{ errorOf('ip_allowlist.entries') }}</p>
        </SettingsBlock>
      </div>
    </div>
  </SettingsPage>
</template>
