<!--
  One call as code in five languages (F13 M5): curl, JavaScript, Python, PHP, C#, with Copy. The
  choice is remembered and shared by every snippet on the page. `dark` for the docs' code panel.
-->
<script setup lang="ts">
import { snippetFor, type SnippetCall, type SnippetLanguage } from '#shared/utils/apiService/snippets'

const props = defineProps<{ call: SnippetCall; dark?: boolean }>()
const { t } = useI18n()
const { copy } = useClipboard({ legacy: true })
const toast = useToast()
const language = useLocalStorage<SnippetLanguage>('formalie:api-docs-language', 'curl')
const languages: { value: SnippetLanguage; label: string }[] = [
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
      <div class="flex min-w-0 gap-1 overflow-x-auto [scrollbar-width:none]" role="tablist" :aria-label="t('apiService.docs.language')">
        <button
          v-for="item in languages"
          :key="item.value"
          type="button"
          role="tab"
          :aria-selected="language === item.value"
          class="shrink-0 rounded-md px-2 py-1 text-xs font-medium transition-colors focus-visible:outline-2"
          :class="dark ? (language === item.value ? 'bg-neutral-800 text-white focus-visible:outline-neutral-400' : 'text-neutral-400 hover:text-neutral-200 focus-visible:outline-neutral-400') : language === item.value ? 'bg-elevated text-highlighted focus-visible:outline-(--ui-border-inverted)' : 'text-muted hover:text-highlighted focus-visible:outline-(--ui-border-inverted)'"
          @click="language = item.value"
        >
          {{ item.label }}
        </button>
      </div>
      <UButton icon="i-lucide-copy" :color="dark ? 'neutral' : 'neutral'" variant="ghost" size="xs" square :class="dark ? 'text-neutral-300 hover:bg-neutral-800 hover:text-white' : ''" :aria-label="t('common.copy')" @click="copyCode" />
    </div>
    <pre class="max-h-80 overflow-auto rounded-lg p-3 font-mono text-xs leading-relaxed" :class="dark ? 'bg-neutral-900 text-neutral-100' : 'border border-default bg-elevated/50 text-highlighted'" dir="ltr">{{ code }}</pre>
  </div>
</template>
