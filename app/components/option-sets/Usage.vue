<!--
  Option list editor → Used in (F15 M1): the forms with fields filled from this list, each field marked
  up to date or changed since. "Update forms" copies the list (and its translations) into those drafts,
  all or one; published forms then show "unpublished changes" until someone publishes them.
-->
<script setup lang="ts">
import type { OptionListUsage } from '#shared/types/forms'

const props = defineProps<{ listId: string; dirty: boolean }>()
const emit = defineEmits<{ synced: [] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()

const usage = ref<OptionListUsage[] | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    usage.value = (await api.get<OptionListUsage[]>(`/option-lists/${props.listId}/usage`, undefined, { background: !!usage.value })).data
  } catch {
    failed.value = true
  }
}
onMounted(load)
defineExpose({ load })

const outdated = computed(() => (usage.value ?? []).filter(item => item.fields.some(field => !field.in_sync)))
const busy = ref<string | null>(null)
async function sync(formIds?: string[]) {
  if (busy.value) return
  busy.value = formIds?.[0] ?? 'all'
  try {
    const { data } = await api.post<{ forms: number; fields: number; published: number }>(`/option-lists/${props.listId}/sync`, formIds ? { form_ids: formIds } : {})
    toast.add({ title: t('optionSets.usage.synced', { n: data.forms }, data.forms), description: data.published ? t('optionSets.usage.publishHint', { n: data.published }, data.published) : undefined, color: 'success', icon: 'i-lucide-refresh-ccw' })
    await load()
    emit('synced')
  } catch (error) {
    handle(error)
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <AppEmpty v-if="failed && !usage" size="sm" icon="i-lucide-cloud-off" :title="t('optionSets.usage.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
  <div v-else-if="!usage" class="flex flex-col gap-2"><USkeleton v-for="n in 3" :key="n" class="h-14" /></div>
  <AppEmpty v-else-if="!usage.length" size="sm" icon="i-lucide-file-search" :title="t('optionSets.usage.none')" :description="t('optionSets.usage.noneDesc')" />
  <div v-else class="flex flex-col gap-3">
    <UAlert v-if="dirty" color="warning" variant="subtle" icon="i-lucide-save" :description="t('optionSets.usage.saveFirst')" />
    <div class="flex flex-wrap items-center justify-between gap-2">
      <p class="text-xs text-muted">{{ outdated.length ? t('optionSets.usage.outdated', { n: outdated.length }, outdated.length) : t('optionSets.usage.allSynced') }}</p>
      <UButton v-if="outdated.length" :label="t('optionSets.usage.updateAll')" icon="i-lucide-refresh-ccw" color="neutral" size="sm" :loading="busy === 'all'" :disabled="dirty || !!busy" @click="sync()" />
    </div>
    <ul class="flex flex-col divide-y divide-default rounded-lg border border-default">
      <li v-for="item in usage" :key="item.form.id" class="flex flex-wrap items-center gap-3 px-3 py-2.5" :class="busy === item.form.id ? 'opacity-60' : ''">
        <UIcon name="i-lucide-file-text" class="size-4 shrink-0 text-muted" />
        <span class="flex min-w-0 flex-1 flex-col">
          <NuxtLink :to="`/forms/${item.form.id}/build`" class="truncate text-sm font-medium text-highlighted underline-offset-2 hover:underline">{{ item.form.name }}</NuxtLink>
          <span class="flex flex-wrap gap-1 pt-1">
            <UBadge v-for="field in item.fields" :key="field.id" :label="field.label" :icon="field.in_sync ? 'i-lucide-check' : 'i-lucide-refresh-ccw'" :color="field.in_sync ? 'neutral' : 'warning'" variant="subtle" size="sm" />
          </span>
        </span>
        <DataStatusBadge :status="item.form.status" />
        <UButton v-if="item.fields.some(field => !field.in_sync)" :label="t('optionSets.usage.update')" icon="i-lucide-refresh-ccw" color="neutral" variant="outline" size="xs" :loading="busy === item.form.id" :disabled="dirty || !!busy" @click="sync([item.form.id])" />
      </li>
    </ul>
  </div>
</template>
