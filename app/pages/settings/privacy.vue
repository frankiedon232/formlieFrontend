<!--
  Settings → Privacy and data (F14 M5): how long responses are kept (each form may set its own; what a
  shorter limit would remove now is shown, and saving asks first), the organisation's privacy notice and
  a consent line on every public form (with a live sample), and data requests (find, export, delete one
  person's responses). Where data is stored comes with the plans (F23).
-->
<script setup lang="ts">
import { RETENTION_DAYS, type RetentionPreview } from '#shared/types/privacy'
import { privacySchema } from '#shared/utils/settings/schemas'

definePageMeta({ breadcrumb: 'settings.nav.privacy' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.privacy') })
const api = useApi()
const confirm = useConfirm()
const { number, dateTime } = useFormat()
const form = useSettingsForm('privacy', { schema: privacySchema, beforeSave: () => confirmRemoval() })
const { draft, errorOf } = form
const store = useWorkspaceSettings()
const org = computed(() => store.settings.value?.company.display_name ?? '')

const options = computed(() => RETENTION_DAYS.map(days => ({ value: days, label: days ? t('settings.privacy.keepFor', { n: days }, days) : t('settings.privacy.keepAll') })))

// What the chosen limit would remove right now
const preview = ref<RetentionPreview | null>(null)
const checking = ref(false)
watch(
  () => draft.value?.retention_days,
  async days => {
    preview.value = null
    if (!days) return
    checking.value = true
    try {
      preview.value = (await api.get<RetentionPreview>('/settings/privacy/retention-preview', { days }, { background: true })).data
    } catch {
      preview.value = null
    } finally {
      checking.value = false
    }
  },
  { immediate: true },
)
/** Saving a limit that removes responses now asks first (button and Ctrl / ⌘ + S alike). */
async function confirmRemoval(): Promise<boolean> {
  const removing: number = preview.value && draft.value?.retention_days !== form.saved.value?.retention_days ? preview.value.responses : 0
  return !removing || (await confirm({ title: t('settings.privacy.confirmTitle', { n: number(removing) }, removing), description: t('settings.privacy.confirmDesc'), confirmLabel: t('settings.privacy.confirm'), danger: true }))
}
const consentLine = computed(() => draft.value?.consent_text || t('renderer.consentLine', { org: org.value }))
</script>

<template>
  <SettingsPage id="settings-privacy" :title="t('settings.nav.privacy')" :subtitle="t('settings.desc.privacy')" icon="i-lucide-lock-keyhole" :form="{ dirty: form.dirty.value, saving: form.saving.value, updated: form.updated.value }" @save="form.save" @discard="form.discard">
    <AppEmpty v-if="form.failed.value && !draft" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => form.reload() }]" />
    <div v-else-if="!draft" class="flex flex-col gap-6"><USkeleton v-for="n in 3" :key="n" class="h-36 rounded-lg" /></div>
    <div v-else class="flex flex-col gap-6">
      <SettingsBlock :title="t('settings.privacy.retention')" :description="t('settings.privacy.retentionHint')" icon="i-lucide-calendar-x">
        <UFormField :label="t('settings.privacy.keep')" :help="t('settings.privacy.perForm')">
          <USelect v-model="draft.retention_days" :items="options" class="w-full sm:max-w-xs" />
        </UFormField>
        <USkeleton v-if="checking" class="h-14 rounded-lg" />
        <UAlert v-else-if="preview?.responses" color="warning" variant="subtle" icon="i-lucide-triangle-alert" :title="t('settings.privacy.wouldRemove', { n: number(preview.responses), forms: preview.forms }, preview.responses)" :description="preview.oldest_kept ? t('settings.privacy.newestRemoved', { when: dateTime(preview.oldest_kept) }) : undefined" />
        <p v-else-if="draft.retention_days" class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-circle-check" class="size-3.5 text-success" />{{ t('settings.privacy.nothingNow') }}</p>
      </SettingsBlock>

      <SettingsBlock :title="t('settings.privacy.notice')" :description="t('settings.privacy.noticeHint')" icon="i-lucide-file-lock">
        <UFormField :label="t('settings.privacy.noticeUrl')" :error="errorOf('notice_url')">
          <SettingsText v-model="draft.notice_url" type="url" placeholder="https://www.example.com/privacy" icon="i-lucide-link" class="w-full" />
        </UFormField>
        <div class="flex items-center gap-3 rounded-lg border border-default p-3">
          <span class="flex min-w-0 flex-1 flex-col gap-0.5"><span class="text-sm font-medium text-highlighted">{{ t('settings.privacy.consent') }}</span><span class="text-xs text-muted">{{ t('settings.privacy.consentHint') }}</span></span>
          <USwitch v-model="draft.consent" color="neutral" :aria-label="t('settings.privacy.consent')" />
        </div>
        <template v-if="draft.consent">
          <UFormField :label="t('settings.privacy.consentText')" :help="t('settings.privacy.consentTextHelp')">
            <SettingsText v-model="draft.consent_text" :placeholder="t('renderer.consentLine', { org })" class="w-full" />
          </UFormField>
          <div class="flex flex-col gap-2 rounded-lg border border-dashed border-default p-3">
            <span class="text-[11px] font-medium tracking-wide text-muted uppercase">{{ t('settings.privacy.sample') }}</span>
            <p class="flex items-start gap-1.5 text-xs text-muted"><UIcon name="i-lucide-shield-check" class="mt-0.5 size-3.5 shrink-0" /><span>{{ consentLine }} <span v-if="draft.notice_url" class="font-medium text-highlighted underline underline-offset-2">{{ t('renderer.privacyNotice') }}</span></span></p>
            <UButton :label="t('renderer.submit')" color="neutral" size="sm" class="w-fit" tabindex="-1" aria-hidden="true" />
          </div>
        </template>
      </SettingsBlock>

      <SettingsBlock :title="t('settings.privacy.requests')" :description="t('settings.privacy.requestsHint')" icon="i-lucide-user-search">
        <SettingsPrivacyRequests />
      </SettingsBlock>

      <SettingsBlock :title="t('settings.privacy.residency')" :description="t('settings.privacy.residencyHint')" icon="i-lucide-server">
        <p class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-info" class="size-3.5 shrink-0" />{{ t('settings.privacy.residencyLater') }}</p>
      </SettingsBlock>
    </div>
  </SettingsPage>
</template>
