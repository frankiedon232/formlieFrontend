<!--
  Settings → Email templates (F14 M4): who emails come from (name, reply-to, a footer line), every
  email Formalie sends in each language the workspace uses (Formalie's text or the workspace's own,
  with a live preview and a test send), and the sent log. Saving applies to the next email.
-->
<script setup lang="ts">
import { EMAIL_TEMPLATES, type EmailTemplateKey } from '#shared/types/emails'
import { APP_LOCALES } from '#shared/utils/i18n/locales'
import { emailsSchema } from '#shared/utils/settings/schemas'

definePageMeta({ breadcrumb: 'settings.nav.emails' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.emails') })
const form = useSettingsForm('emails', { schema: emailsSchema })
const { draft, errorOf } = form
const store = useWorkspaceSettings()
const sentLog = useTemplateRef<{ reload: () => void }>('sentLog')

const ICONS: Record<EmailTemplateKey, string> = {
  signin_code: 'i-lucide-key-round',
  password_reset: 'i-lucide-rotate-ccw-key',
  invitation: 'i-lucide-user-plus',
  response_notification: 'i-lucide-inbox',
  response_receipt: 'i-lucide-receipt-text',
  notification: 'i-lucide-bell',
  daily_digest: 'i-lucide-mails',
}
const selected = ref<EmailTemplateKey>('response_notification')
const workspaceName = computed(() => store.settings.value?.company.display_name ?? '')

// The workspace's language first, then the other languages its forms use
const languages = computed(() => {
  const loc = store.settings.value?.localisation
  if (!loc) return []
  const codes = [loc.language, ...loc.form_languages.filter(code => code !== loc.language)]
  return codes.map(code => APP_LOCALES.find(item => item.code === code)).filter(item => !!item).map(item => ({ value: item.code, label: item.name, icon: item.flag }))
})
const language = ref('')
watch(languages, list => !list.some(item => item.value === language.value) && (language.value = list[0]?.value ?? 'en'), { immediate: true })
const customCount = (key: EmailTemplateKey) => Object.keys(draft.value?.custom[key] ?? {}).length
</script>

<template>
  <SettingsPage id="settings-emails" :title="t('settings.nav.emails')" :subtitle="t('settings.desc.emails')" icon="i-lucide-mail" :form="{ dirty: form.dirty.value, saving: form.saving.value, updated: form.updated.value }" @save="form.save" @discard="form.discard">
    <AppEmpty v-if="form.failed.value && !draft" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => form.reload() }]" />
    <div v-else-if="!draft" class="flex flex-col gap-6"><USkeleton v-for="n in 3" :key="n" class="h-40 rounded-lg" /></div>
    <div v-else class="flex flex-col gap-6">
      <SettingsBlock :title="t('settings.emails.sender')" :description="t('settings.emails.senderHint')" icon="i-lucide-send">
        <div class="grid gap-4 sm:grid-cols-2">
          <UFormField :label="t('settings.emails.senderName')" :help="t('settings.emails.senderNameHelp')">
            <SettingsText v-model="draft.sender_name" :placeholder="workspaceName" icon="i-lucide-user-round" class="w-full" />
          </UFormField>
          <UFormField :label="t('settings.emails.replyTo')" :help="t('settings.emails.replyToHelp')" :error="errorOf('reply_to')">
            <SettingsText v-model="draft.reply_to" type="email" placeholder="support@example.com" icon="i-lucide-reply" class="w-full" />
          </UFormField>
        </div>
        <UFormField :label="t('settings.emails.footer')" :help="t('settings.emails.footerHelp')">
          <SettingsText v-model="draft.footer" :placeholder="t('settings.emails.footerPlaceholder')" class="w-full" />
        </UFormField>
      </SettingsBlock>

      <SettingsBlock :title="t('settings.emails.templates')" :description="t('settings.emails.templatesHint')" icon="i-lucide-mail">
        <div class="flex flex-col gap-4">
          <div class="flex flex-wrap items-center gap-2">
            <USelect v-model="selected" :items="EMAIL_TEMPLATES.map(key => ({ value: key, label: t(`settings.emails.template.${key}`), icon: ICONS[key] }))" :icon="ICONS[selected]" class="w-full sm:hidden" :aria-label="t('settings.emails.templates')" />
            <USelect v-model="language" :items="languages" :icon="languages.find(item => item.value === language)?.icon" class="w-full sm:w-48" :aria-label="t('settings.emails.language')" />
          </div>
          <div class="hidden gap-2 sm:grid sm:grid-cols-4 2xl:grid-cols-7">
            <button v-for="key in EMAIL_TEMPLATES" :key="key" type="button" class="flex min-w-0 flex-col items-start gap-1.5 rounded-lg border p-2.5 text-start transition-colors focus-visible:outline-2 focus-visible:outline-primary" :class="selected === key ? 'border-inverted bg-elevated/60' : 'border-default hover:border-accented'" @click="selected = key">
              <UIcon :name="ICONS[key]" class="size-4 text-muted" />
              <span class="line-clamp-2 text-xs font-medium text-highlighted">{{ t(`settings.emails.template.${key}`) }}</span>
              <span class="text-[10px] text-muted">{{ customCount(key) ? t('settings.emails.ownIn', { n: customCount(key) }, customCount(key)) : t('settings.emails.formalie') }}</span>
            </button>
          </div>
          <p class="text-xs text-muted">{{ t(`settings.emails.when.${selected}`) }}</p>
          <SettingsEmailsEditor v-if="language" v-model="draft.custom" :template-key="selected" :language="language" @sent="sentLog?.reload()" />
        </div>
      </SettingsBlock>

      <SettingsBlock :title="t('settings.emails.sent')" :description="t('settings.emails.sentHint')" icon="i-lucide-inbox">
        <SettingsEmailsSent ref="sentLog" />
      </SettingsBlock>
    </div>
  </SettingsPage>
</template>
