<!--
  Settings → Notifications (F14 M4): for every event, whether it shows in the app and / or by email, and
  for whom (admins, everyone, chosen people; an export only ever tells whoever asked for it). Optional
  daily summary instead of an email each time, with "send it now" to try. Saving applies at once.
-->
<script setup lang="ts">
import { NOTIFICATION_EVENTS, type NotificationEvent } from '#shared/types/notifications'
import { notificationsSchema } from '#shared/utils/settings/schemas'

definePageMeta({ breadcrumb: 'settings.nav.notifications' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.notifications') })
const api = useApi()
const form = useSettingsForm('notifications', { schema: notificationsSchema })
const { draft, errorOf } = form
const { busy, run } = useBusy()

const people = ref<{ value: string; label: string; description: string }[]>([])
onMounted(async () => {
  try {
    const { data } = await api.get<{ users: { id: string; name: string; detail: string }[] }>('/directory', undefined, { background: true })
    people.value = data.users.map(user => ({ value: user.id, label: user.name, description: user.detail }))
  } catch {
    people.value = []
  }
})

const GROUPS: { key: string; events: NotificationEvent[] }[] = [
  { key: 'responses', events: ['response_new', 'response_duplicate'] },
  { key: 'forms', events: ['form_limit', 'form_closing', 'export_ready'] },
  { key: 'problems', events: ['webhook_failing', 'security_alert'] },
]
const audiences = computed(() => (['admins', 'everyone', 'people'] as const).map(value => ({ value, label: t(`settings.notifications.to.${value}`) })))
const hours = computed(() => Array.from({ length: 24 }, (_, hour) => ({ value: hour, label: `${String(hour).padStart(2, '0')}:00 UTC` })))
const onCount = computed(() => (draft.value ? NOTIFICATION_EVENTS.filter(key => draft.value!.events[key].in_app || draft.value!.events[key].email).length : 0))

const sendNow = () => run(async () => (await api.post<{ sent: number }>('/notifications/digest/send')).data, {}).then(result => result && useToast().add({ title: t('settings.notifications.digestSent', { n: result.sent }, result.sent), color: 'success', icon: 'i-lucide-mail-check' }))
</script>

<template>
  <SettingsPage id="settings-notifications" :title="t('settings.nav.notifications')" :subtitle="t('settings.desc.notifications')" icon="i-lucide-bell-ring" :form="{ dirty: form.dirty.value, saving: form.saving.value, updated: form.updated.value }" @save="form.save" @discard="form.discard">
    <AppEmpty v-if="form.failed.value && !draft" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => form.reload() }]" />
    <div v-else-if="!draft" class="flex flex-col gap-6"><USkeleton v-for="n in 3" :key="n" class="h-40 rounded-lg" /></div>
    <div v-else class="flex flex-col gap-6">
      <SettingsBlock v-for="group in GROUPS" :key="group.key" :title="t(`settings.notifications.group.${group.key}`)" :description="t(`settings.notifications.groupHint.${group.key}`)" :icon="NOTIFICATION_ICONS[group.events[0]!]">
        <div class="flex flex-col divide-y divide-default rounded-lg border border-default">
          <div class="hidden grid-cols-[minmax(0,1fr)_4.5rem_4.5rem_14rem] items-center gap-3 px-3 py-2 text-[11px] font-medium tracking-wide text-muted uppercase lg:grid">
            <span>{{ t('settings.notifications.event') }}</span><span class="text-center">{{ t('settings.notifications.inApp') }}</span><span class="text-center">{{ t('settings.notifications.email') }}</span><span>{{ t('settings.notifications.who') }}</span>
          </div>
          <div v-for="key in group.events" :key="key" class="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-x-3 gap-y-2 px-3 py-3 lg:grid-cols-[minmax(0,1fr)_4.5rem_4.5rem_14rem]">
            <span class="col-span-3 flex min-w-0 items-start gap-2.5 lg:col-span-1">
              <UIcon :name="NOTIFICATION_ICONS[key]" class="mt-0.5 size-4 shrink-0 text-muted" />
              <span class="flex min-w-0 flex-col"><span class="text-sm font-medium text-highlighted">{{ t(`settings.notifications.name.${key}`) }}</span><span class="text-xs text-muted">{{ t(`settings.notifications.hint.${key}`) }}</span></span>
            </span>
            <label class="flex items-center gap-2 lg:justify-center"><USwitch v-model="draft.events[key].in_app" color="neutral" size="sm" /><span class="text-xs text-muted lg:sr-only">{{ t('settings.notifications.inApp') }}</span></label>
            <label class="flex items-center gap-2 lg:justify-center"><USwitch v-model="draft.events[key].email" color="neutral" size="sm" /><span class="text-xs text-muted lg:sr-only">{{ t('settings.notifications.email') }}</span></label>
            <div class="col-span-3 flex min-w-0 flex-col gap-2 lg:col-span-1">
              <span v-if="key === 'export_ready'" class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-user-round" class="size-3.5" />{{ t('settings.notifications.whoAsked') }}</span>
              <template v-else>
                <USelect v-model="draft.events[key].to" :items="audiences" size="sm" class="w-full" :disabled="!draft.events[key].in_app && !draft.events[key].email" :aria-label="t('settings.notifications.who')" />
                <USelectMenu v-if="draft.events[key].to === 'people'" v-model="draft.events[key].people" :items="people" value-key="value" multiple size="sm" :placeholder="t('settings.notifications.pickPeople')" :search-input="{ placeholder: t('common.search') }" class="w-full" />
                <span v-if="errorOf(`events.${key}.people`)" class="text-xs text-error">{{ errorOf(`events.${key}.people`) }}</span>
              </template>
            </div>
          </div>
        </div>
      </SettingsBlock>

      <SettingsBlock :title="t('settings.notifications.digest')" :description="t('settings.notifications.digestHint')" icon="i-lucide-mails">
        <div class="flex items-center gap-3 rounded-lg border border-default p-3">
          <span class="flex min-w-0 flex-1 flex-col gap-0.5"><span class="text-sm font-medium text-highlighted">{{ t('settings.notifications.digestOn') }}</span><span class="text-xs text-muted">{{ t('settings.notifications.digestOnHint') }}</span></span>
          <USwitch v-model="draft.digest.enabled" color="neutral" :aria-label="t('settings.notifications.digestOn')" />
        </div>
        <div v-if="draft.digest.enabled" class="flex flex-wrap items-end gap-3">
          <UFormField :label="t('settings.notifications.digestAt')"><USelect v-model="draft.digest.hour" :items="hours" class="w-36" /></UFormField>
          <UButton :label="t('settings.notifications.sendNow')" icon="i-lucide-send" color="neutral" variant="outline" :loading="busy" :disabled="form.dirty.value" @click="sendNow" />
        </div>
        <p class="flex items-start gap-1.5 text-xs text-muted"><UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" />{{ t('settings.notifications.summary', { n: onCount, total: NOTIFICATION_EVENTS.length }) }}</p>
      </SettingsBlock>
    </div>
  </SettingsPage>
</template>
