<!-- One call as code in five languages (F13 M5): curl, JavaScript, Python, PHP, C#, each with Copy. The choice is remembered. -->
<script setup lang="ts">
import { snippetFor, type SnippetCall, type SnippetLanguage } from '#shared/utils/apiService/snippets'

const props = defineProps<{ call: SnippetCall }>()
const { t } = useI18n()
const { copy } = useClipboard({ legacy: true })
const toast = useToast()
const language = useLocalStorage<SnippetLanguage>('formalie:api-docs-language', 'curl')
const languages = [
  { value: 'curl', label: 'curl' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'python', label: 'Python' },
  { value: 'php', label: 'PHP' },
  { value: 'csharp', label: 'C#' },
]
const code = computed(() => snippetFor(language.value, props.call))
function copyCode() {
  void copy(code.value)
  toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
}
</script>

<template>
  <div class="flex min-w-0 flex-col gap-2">
    <div class="flex items-center justify-between gap-2">
      <UTabs v-model="language" :items="languages" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" class="min-w-0 overflow-x-auto" :aria-label="t('apiService.docs.language')" />
      <UButton icon="i-lucide-copy" color="neutral" variant="ghost" size="xs" square :aria-label="t('common.copy')" @click="copyCode" />
    </div>
    <pre class="max-h-80 overflow-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-highlighted" dir="ltr">{{ code }}</pre>
  </div>
</template>
