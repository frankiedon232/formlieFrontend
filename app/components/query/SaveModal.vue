<!--
  Save a statement (F12 M4 part 2), or change a saved one's name, description and sharing: a name,
  an optional description, and whether everyone in the workspace may see and run it (only you can
  change or delete it). An outside click doesn't close it.
-->
<script setup lang="ts">
import type { SavedQuery } from '#shared/types/query'

const props = defineProps<{ sql: string; connection: string; existing?: SavedQuery | null; suggestedName?: string }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ save: [values: { name: string; description: string | null; shared: boolean }] }>()
const { t } = useI18n()
const name = ref('')
const description = ref('')
const shared = ref(false)
const error = ref<string | null>(null)
const busy = defineModel<boolean>('busy', { default: false })

watch(open, isOpen => {
  if (!isOpen) return
  name.value = props.existing?.name ?? props.suggestedName ?? ''
  description.value = props.existing?.description ?? ''
  shared.value = props.existing?.shared ?? false
  error.value = null
})
function submit() {
  if (!name.value.trim()) return void (error.value = t('query.saved.nameRequired'))
  emit('save', { name: name.value.trim(), description: description.value.trim() || null, shared: shared.value })
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="existing ? t('query.saved.editTitle') : t('query.saved.saveTitle')" :description="connection" :dismissible="!busy" :ui="{ content: 'sm:max-w-lg' }">
    <template #body>
      <form id="save-query" class="flex flex-col gap-4" novalidate @submit.prevent="submit">
        <UFormField :label="t('query.saved.name')" :error="error ?? undefined" required>
          <UInput v-model="name" autofocus class="w-full" maxlength="120" :placeholder="t('query.saved.namePlaceholder')" />
        </UFormField>
        <UFormField :label="t('query.saved.description')" :hint="t('explorer.ddl.optional')">
          <UTextarea v-model="description" :rows="2" autoresize :maxrows="5" maxlength="500" class="w-full" :placeholder="t('query.saved.descriptionPlaceholder')" />
        </UFormField>
        <USwitch v-model="shared" :label="t('query.saved.shareLabel')" :description="t('query.saved.shareDesc')" />
        <pre v-if="!existing" class="max-h-40 overflow-auto rounded-md border border-default bg-elevated/50 px-3 py-2 font-mono text-[11px] whitespace-pre-wrap text-default" dir="ltr">{{ sql }}</pre>
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" :disabled="busy" @click="open = false" />
        <UButton type="submit" form="save-query" :label="existing ? t('common.save') : t('query.saved.saveButton')" icon="i-lucide-bookmark" color="neutral" :loading="busy" />
      </div>
    </template>
  </AppModal>
</template>
