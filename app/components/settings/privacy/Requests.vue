<!--
  Settings → Privacy and data (F14 M5): a person asks what you hold about them, or to be forgotten.
  Find their responses by email across every form, export them (JSON file) or delete them all for good
  (typing the address again to confirm). Both are in the audit trail with the address masked.
-->
<script setup lang="ts">
import type { DataRequestMatch } from '#shared/types/privacy'

const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { relative, number } = useFormat()
const { busy, run } = useBusy()

const email = ref('')
const match = ref<DataRequestMatch | null>(null)
const valid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()))
const find = () => valid.value && run(async () => (match.value = (await api.post<DataRequestMatch>('/privacy/requests/search', { email: email.value.trim() })).data))
watch(email, () => (match.value = null))

const exporting = ref(false)
async function exportAll() {
  if (!match.value || exporting.value) return
  exporting.value = true
  try {
    const { data } = await api.post<unknown>('/privacy/requests/export', { email: match.value.email })
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
    const link = Object.assign(document.createElement('a'), { href: url, download: `data-${match.value.email.replace(/[^a-z0-9]+/gi, '-')}.json` })
    link.click()
    URL.revokeObjectURL(url)
    toast.add({ title: t('settings.privacy.exported'), color: 'success', icon: 'i-lucide-file-down' })
  } catch (error) {
    useErrorHandler().handle(error)
  } finally {
    exporting.value = false
  }
}

const deleteOpen = ref(false)
const typed = ref('')
const deleting = ref(false)
async function deleteAll() {
  if (!match.value || deleting.value || typed.value.trim().toLowerCase() !== match.value.email) return
  deleting.value = true
  try {
    const { data } = await api.post<{ responses: number }>('/privacy/requests/delete', { email: match.value.email, confirm: typed.value })
    toast.add({ title: t('settings.privacy.deleted', { n: data.responses }, data.responses), color: 'success', icon: 'i-lucide-user-x' })
    deleteOpen.value = false
    typed.value = ''
    await find()
  } catch (error) {
    useErrorHandler().handle(error)
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <form class="flex flex-col gap-2 sm:flex-row" @submit.prevent="find">
    <UInput v-model="email" type="email" icon="i-lucide-at-sign" :placeholder="t('settings.privacy.requestPlaceholder')" class="w-full sm:max-w-sm" :aria-label="t('settings.privacy.requestEmail')" />
    <UButton type="submit" :label="t('settings.privacy.find')" icon="i-lucide-search" color="neutral" variant="outline" :loading="busy" :disabled="!valid" />
  </form>

  <div v-if="match" class="flex flex-col rounded-lg border border-default" :class="busy ? 'opacity-60' : ''">
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-default px-3 py-2.5">
      <span class="text-sm text-highlighted">{{ t('settings.privacy.found', { n: number(match.total), email: match.email }, match.total) }}</span>
      <div v-if="match.total" class="flex gap-2">
        <UButton :label="t('settings.privacy.export')" icon="i-lucide-file-down" color="neutral" variant="outline" size="sm" :loading="exporting" @click="exportAll" />
        <UButton :label="t('settings.privacy.deleteAll')" icon="i-lucide-trash-2" color="error" variant="outline" size="sm" @click="deleteOpen = true" />
      </div>
    </div>
    <AppEmpty v-if="!match.total" size="xs" icon="i-lucide-user-search" :title="t('settings.privacy.none')" :description="t('settings.privacy.noneDesc')" />
    <ul v-else class="flex max-h-64 flex-col divide-y divide-default overflow-y-auto">
      <li v-for="form in match.forms" :key="form.id" class="flex items-center gap-3 px-3 py-2">
        <UIcon name="i-lucide-file-text" class="size-4 shrink-0 text-muted" />
        <span class="min-w-0 flex-1 truncate text-sm text-highlighted">{{ form.name }}</span>
        <span class="shrink-0 text-xs text-muted tabular-nums">{{ t('settings.privacy.responses', { n: number(form.count) }, form.count) }} · {{ relative(form.latest) }}</span>
      </li>
    </ul>
  </div>

  <AppModal v-model:open="deleteOpen" :title="t('settings.privacy.deleteTitle')" :description="t('settings.privacy.deleteDesc', { n: match?.total ?? 0, forms: match?.forms.length ?? 0 }, match?.total ?? 0)" keep-open>
    <template #body>
      <UFormField :label="t('settings.privacy.typeEmail', { email: match?.email ?? '' })">
        <UInput v-model="typed" autocomplete="off" autofocus class="w-full" @keydown.enter="deleteAll" />
      </UFormField>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="deleteOpen = false" />
        <UButton :label="t('settings.privacy.deleteAll')" icon="i-lucide-trash-2" color="error" :loading="deleting" :disabled="typed.trim().toLowerCase() !== match?.email" @click="deleteAll" />
      </div>
    </template>
  </AppModal>
</template>
