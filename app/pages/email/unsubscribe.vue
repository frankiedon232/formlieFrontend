<!--
  The page an email's Unsubscribe link opens (owner, 2026-10-12), no sign-in needed: the signed link says who and
  what. Nothing changes until the person presses Unsubscribe (mail scanners open links on their own), then Undo is
  offered. Only optional emails have the link: new responses for one form, one kind of notification, the daily
  summary, or form invitations from a workspace.
-->
<script setup lang="ts">
import type { UnsubscribeView } from '#shared/types/emails'

definePageMeta({ layout: 'auth', auth: false })
const { t, te } = useI18n()
const route = useRoute()
const api = useApi()
const { busy, run } = useBusy()
useHead({ title: () => t('emailPrefs.title') })

const token = typeof route.query.t === 'string' ? route.query.t : ''
const view = ref<UnsubscribeView | null>(null)
const invalid = ref(false)
onMounted(async () => {
  try {
    if (!token) throw new Error('no token')
    view.value = (await api.get<UnsubscribeView>('/public/unsubscribe', { t: token })).data
  } catch {
    invalid.value = true
  }
})

/** "new responses to Customer feedback", "Form is full notifications", "the daily summary", "form invitations". */
const what = computed(() => {
  const item = view.value
  if (!item) return ''
  if (item.kind === 'response_notification') return item.subject ? t('emailPrefs.what.responsesTo', { form: item.subject }) : t('emailPrefs.what.responses')
  if (item.kind === 'notification') {
    const key = `settings.notifications.name.${item.subject}`
    return t('emailPrefs.what.notification', { event: item.subject && te(key) ? t(key) : t('emailPrefs.what.updates') })
  }
  return t(`emailPrefs.what.${item.kind}`)
})

async function set(stop: boolean) {
  const result = await run(() => api.post<UnsubscribeView>(stop ? '/public/unsubscribe' : '/public/unsubscribe/undo', { t: token }))
  if (result) view.value = result.data
}
</script>

<template>
  <div>
    <AppEmpty v-if="invalid" icon="i-lucide-link-2-off" :title="t('emailPrefs.invalidTitle')" :description="t('emailPrefs.invalidDesc')" />
    <div v-else-if="!view" class="flex flex-col gap-4">
      <USkeleton class="h-8 w-64" />
      <USkeleton class="h-4 w-full" />
      <USkeleton class="h-4 w-4/5" />
      <USkeleton class="h-11 w-40" />
    </div>
    <template v-else-if="!view.unsubscribed">
      <AuthHeading :title="t('emailPrefs.askTitle')" :description="t('emailPrefs.askDesc', { what, workspace: view.workspace, email: view.email })" />
      <UButton :label="t('emailPrefs.stop')" icon="i-lucide-mail-x" color="neutral" size="xl" :loading="busy" @click="set(true)" />
      <p class="mt-6 flex items-start gap-2 text-xs text-muted">
        <UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" />{{ t('emailPrefs.kept') }}
      </p>
    </template>
    <template v-else>
      <AuthHeading :title="t('emailPrefs.doneTitle')" :description="t('emailPrefs.doneDesc', { what, workspace: view.workspace, email: view.email })" />
      <UButton :label="t('emailPrefs.undo')" icon="i-lucide-undo-2" color="neutral" variant="outline" size="xl" :loading="busy" @click="set(false)" />
    </template>
  </div>
</template>
