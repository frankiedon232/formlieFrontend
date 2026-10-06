<!--
  A secret right after it is made or rotated (F13 M6: webhook signing secrets, API keys): shown once
  with Copy and how to use it. Formalie keeps only what it needs, so it can not be shown again;
  losing it means rotating (webhooks) or making a new key.
-->
<script setup lang="ts">
const props = defineProps<{ title: string; secret: string | null; label: string; usage: string; hint?: string }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const { copy } = useClipboard({ legacy: true })
const toast = useToast()
function copyUsage() {
  void copy(props.usage)
  toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
}
</script>

<template>
  <AppModal v-model:open="open" :title="title" :dismissible="false" :ui="{ content: 'sm:max-w-xl' }">
    <template #body>
      <div class="flex flex-col gap-4">
        <UAlert icon="i-lucide-triangle-alert" color="warning" variant="subtle" :title="t('apiService.tokens.once.title')" :description="t('integrations.onceDesc')" />
        <AppCopyField v-if="secret" :value="secret" :label="label" monospace />
        <div class="flex flex-col gap-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="text-xs font-medium text-muted">{{ t('apiService.tokens.howToUse') }}</span>
            <UButton icon="i-lucide-copy" color="neutral" variant="ghost" size="xs" square :aria-label="t('common.copy')" @click="copyUsage" />
          </div>
          <pre class="max-h-72 overflow-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-highlighted" dir="ltr">{{ usage }}</pre>
          <p v-if="hint" class="text-xs text-muted">{{ hint }}</p>
        </div>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full justify-end">
        <UButton :label="t('apiService.tokens.copiedDone')" color="neutral" @click="open = false" />
      </div>
    </template>
  </AppModal>
</template>
