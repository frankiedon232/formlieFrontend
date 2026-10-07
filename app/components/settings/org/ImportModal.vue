<!--
  Import entries (F14 M2): paste names (one per line) or pick a CSV / text file (the first column is
  used, a header row is skipped when it looks like one). A preview marks what will be added and what
  is skipped (already there, repeated, too long) before anything is created; then a summary.
-->
<script setup lang="ts">
import type { OrgImportResult, OrgKind } from '#shared/types/org'

const props = defineProps<{ kind: OrgKind; existing: string[] }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ imported: [result: OrgImportResult] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { number } = useFormat()

const text = ref('')
const file = ref<File | null>(null)
watch(open, value => value && ((text.value = ''), (file.value = null)))
watch(file, async picked => {
  if (!picked) return
  text.value = (await picked.text()).slice(0, 200_000)
})

/** Each line's first column, without quotes; a first line like "name" / "department" is a header. */
const rows = computed(() => {
  const lines = text.value.split(/\r?\n/).map(line => line.split(/[,;\t]/)[0]!.trim().replace(/^"|"$/g, '').trim()).filter(Boolean)
  if (lines.length && /^(name|names|title|department|departments|job title|team|location|cost centre|code)$/i.test(lines[0]!)) lines.shift()
  const seen = new Set(props.existing.map(name => name.toLowerCase()))
  return lines.slice(0, 1000).map(name => {
    const key = name.toLowerCase()
    const state = name.length > 80 ? 'too_long' : seen.has(key) ? 'duplicate' : 'new'
    seen.add(key)
    return { name, state }
  })
})
const adding = computed(() => rows.value.filter(row => row.state === 'new').length)

const saving = ref(false)
async function importNow() {
  if (!adding.value || saving.value) return
  saving.value = true
  try {
    const { data } = await api.post<OrgImportResult>(`/org/${props.kind}/import`, { names: rows.value.filter(row => row.state === 'new').map(row => row.name) })
    emit('imported', data)
    open.value = false
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="t(`settings.org.kind.${kind}.import`)" :description="t('settings.org.import.desc')" :ui="{ content: 'sm:max-w-xl' }">
    <template #body>
      <div class="flex flex-col gap-4">
        <UFileUpload v-model="file" accept=".csv,.txt,text/csv,text/plain" :label="t('settings.org.import.drop')" :description="t('settings.org.import.types')" icon="i-lucide-file-up" color="neutral" layout="list" class="w-full" />
        <UFormField :label="t('settings.org.import.paste')">
          <UTextarea v-model="text" :rows="5" class="w-full font-mono" :placeholder="t(`settings.org.kind.${kind}.examples`)" />
        </UFormField>
        <div v-if="rows.length" class="flex flex-col gap-2">
          <span class="text-xs text-muted">{{ t('settings.org.import.summary', { n: number(adding), total: number(rows.length) }) }}</span>
          <ul class="max-h-48 divide-y divide-default overflow-y-auto rounded-lg border border-default text-sm">
            <li v-for="(row, i) in rows" :key="i" class="flex items-center justify-between gap-3 px-3 py-1.5">
              <span class="truncate" :class="row.state === 'new' ? 'text-highlighted' : 'text-muted line-through'">{{ row.name }}</span>
              <UBadge :label="t(`settings.org.import.state.${row.state}`)" :color="row.state === 'new' ? 'success' : 'neutral'" variant="subtle" size="xs" class="shrink-0 rounded-md" />
            </li>
          </ul>
        </div>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
        <UButton :label="t('settings.org.import.action', { n: adding }, adding)" icon="i-lucide-file-up" color="neutral" :disabled="!adding" :loading="saving" @click="importNow" />
      </div>
    </template>
  </AppModal>
</template>
