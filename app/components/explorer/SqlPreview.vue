<!-- The statements a structure change will run (F12 M3), exactly as the server runs them, with Copy. -->
<script setup lang="ts">
const props = defineProps<{ statements: string[] }>()
const { t } = useI18n()
const toast = useToast()
const { copy } = useClipboard({ legacy: true })
function copyAll() {
  void copy(props.statements.join('\n'))
  toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
}
</script>

<template>
  <section class="flex flex-col gap-1.5">
    <div class="flex items-center justify-between gap-2">
      <h3 class="text-xs font-medium text-muted">{{ t('explorer.ddl.willRun') }}</h3>
      <UButton :label="t('common.copy')" icon="i-lucide-copy" color="neutral" variant="ghost" size="xs" :disabled="!statements.length" @click="copyAll" />
    </div>
    <pre class="max-h-56 overflow-auto rounded-md border border-default bg-elevated/50 px-3 py-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap text-default" dir="ltr" tabindex="0">{{ statements.length ? statements.join('\n') : '–' }}</pre>
  </section>
</template>
