<!--
  Settings → Email templates (F14 M4): the sent log. Every email Formalie sent for the workspace
  (codes, notifications, responses, tests), newest first, searchable and paged; one opens in a
  preview as people receive it. Sign-in and reset codes are never kept in it (shown as dots).
-->
<script setup lang="ts">
import type { SentEmail } from '#shared/types/emails'
import type { ListMeta } from '#shared/types/api'

const { t } = useI18n()
const api = useApi()
const { relative, dateTime } = useFormat()

const rows = ref<Omit<SentEmail, 'html' | 'text'>[] | null>(null)
const meta = ref<ListMeta | null>(null)
const failed = ref(false)
const page = ref(1)
const q = ref('')
const search = refDebounced(q, 300)
async function load() {
  failed.value = false
  try {
    const result = await api.list<Omit<SentEmail, 'html' | 'text'>>('/settings/emails/sent', { page: page.value, per_page: 8, q: search.value || undefined }, { background: !!rows.value })
    rows.value = result.data
    meta.value = result.meta
  } catch {
    failed.value = true
  }
}
watch(search, () => ((page.value = 1), void load()))
watch(page, () => void load())
onMounted(load)
defineExpose({ reload: load })

const ICONS: Record<SentEmail['template'], string> = {
  signin_code: 'i-lucide-key-round',
  password_reset: 'i-lucide-rotate-ccw-key',
  invitation: 'i-lucide-user-plus',
  response_notification: 'i-lucide-inbox',
  response_receipt: 'i-lucide-receipt-text',
  notification: 'i-lucide-bell',
  daily_digest: 'i-lucide-mails',
}

const open = ref(false)
const shown = ref<SentEmail | null>(null)
const opening = ref<string | null>(null)
async function show(id: string) {
  if (opening.value) return
  opening.value = id
  try {
    shown.value = (await api.get<SentEmail>(`/settings/emails/sent/${id}`)).data
    open.value = true
  } catch (error) {
    useErrorHandler().handle(error)
  } finally {
    opening.value = null
  }
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <UInput v-model="q" icon="i-lucide-search" :placeholder="t('settings.emails.searchSent')" class="w-full sm:max-w-xs" />
    <AppEmpty v-if="failed && !rows" size="sm" icon="i-lucide-cloud-off" :title="t('settings.emails.sentFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
    <div v-else-if="!rows" class="flex flex-col gap-2"><USkeleton v-for="n in 4" :key="n" class="h-12" /></div>
    <AppEmpty v-else-if="!rows.length" size="sm" icon="i-lucide-mail" :title="q ? t('settings.emails.noMatch') : t('settings.emails.noneSent')" :description="q ? undefined : t('settings.emails.noneSentDesc')" />
    <ul v-else class="flex flex-col divide-y divide-default rounded-lg border border-default">
      <li v-for="row in rows" :key="row.id">
        <button type="button" class="flex w-full items-center gap-3 px-3 py-2.5 text-start transition-colors hover:bg-elevated/50 focus-visible:bg-elevated focus-visible:outline-none" :disabled="!!opening" @click="show(row.id)">
          <span class="flex size-8 shrink-0 items-center justify-center rounded-lg border border-default">
            <UIcon v-if="opening === row.id" name="i-lucide-loader-circle" class="size-4 animate-spin text-muted" />
            <UIcon v-else :name="ICONS[row.template]" class="size-4 text-muted" />
          </span>
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="truncate text-sm text-highlighted">{{ row.subject }}</span>
            <span class="truncate text-xs text-muted">{{ row.to }} · {{ t(`settings.emails.template.${row.template}`) }}<template v-if="row.reason === 'test'"> · {{ t('settings.emails.test') }}</template></span>
          </span>
          <UBadge :label="row.language.toUpperCase()" color="neutral" variant="outline" size="xs" class="hidden shrink-0 sm:inline-flex" />
          <UTooltip :text="dateTime(row.at)"><span class="shrink-0 text-xs whitespace-nowrap text-muted">{{ relative(row.at) }}</span></UTooltip>
        </button>
      </li>
    </ul>
    <div v-if="meta && meta.total_pages > 1" class="flex justify-end">
      <UPagination v-model:page="page" :total="meta.total" :items-per-page="8" size="sm" color="neutral" active-color="neutral" />
    </div>

    <AppModal v-model:open="open" :title="shown?.subject ?? ''" :description="shown ? t('settings.emails.sentTo', { to: shown.to, when: dateTime(shown.at) }) : undefined" :ui="{ content: 'sm:max-w-2xl' }">
      <template #body>
        <iframe v-if="shown" :srcdoc="shown.html" sandbox="" :title="shown.subject" class="h-[60vh] w-full rounded-lg border border-default bg-white" />
      </template>
    </AppModal>
  </div>
</template>
