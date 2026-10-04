<!--
  Embed code (F10 M2): the ready `<iframe>` to paste into a website — auto height (the frame grows
  and shrinks with the form; recommended) or a fixed height. Code from shared/utils/urls/embed.ts.
  Allowed websites and a live preview come with the Share settings (M3).
-->
<script setup lang="ts">
import { clampEmbedHeight, embedCode } from '#shared/utils/urls/embed'

const props = defineProps<{ url: string; formName: string; live: boolean }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const toast = useToast()

const mode = ref<'auto' | 'fixed'>('auto')
const height = ref(700)
const modes = computed(() => [
  { value: 'auto', label: t('forms.embed.auto'), description: t('forms.embed.autoDesc') },
  { value: 'fixed', label: t('forms.embed.fixed'), description: t('forms.embed.fixedDesc') },
])
const code = computed(() =>
  embedCode({ url: props.url, title: props.formName, height: mode.value === 'auto' ? 'auto' : clampEmbedHeight(height.value) }),
)

const { copy } = useClipboard({ legacy: true })
function copyCode() {
  copy(code.value)
  toast.add({ title: t('forms.embed.copied'), icon: 'i-lucide-check', color: 'success' })
}
</script>

<template>
  <AppModal v-model:open="open" :title="t('forms.embed.title')" :description="t('forms.embed.desc')" :ui="{ content: 'sm:max-w-2xl' }">
    <template #body>
      <div class="flex flex-col gap-4">
        <UAlert v-if="!live" icon="i-lucide-circle-dashed" color="neutral" variant="subtle" :title="t('forms.embed.notLive')" />
        <URadioGroup v-model="mode" :items="modes" variant="card" orientation="horizontal" color="neutral" :legend="t('forms.embed.height')" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2', item: 'w-full' }" />
        <UFormField v-if="mode === 'fixed'" :label="t('forms.embed.pixels')" :hint="t('forms.embed.pixelsHint')">
          <UInputNumber v-model="height" :min="240" :max="4000" :step="50" class="w-40" />
        </UFormField>
        <div class="flex flex-col gap-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm font-medium text-highlighted">{{ t('forms.embed.code') }}</span>
            <UButton :label="t('forms.embed.copy')" icon="i-lucide-copy" color="neutral" variant="outline" size="xs" @click="copyCode" />
          </div>
          <pre class="max-h-56 overflow-auto rounded-md border border-default bg-elevated/60 p-3 text-xs leading-relaxed whitespace-pre-wrap break-all text-highlighted" dir="ltr"><code>{{ code }}</code></pre>
          <p class="text-xs text-muted">{{ t('forms.embed.where') }}</p>
        </div>
        <AppCopyField :label="t('forms.overview.embed')" :value="url" monospace />
      </div>
    </template>
    <template #footer>
      <div class="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <UButton :label="t('common.close')" color="neutral" variant="outline" class="justify-center" @click="open = false" />
        <UButton :label="t('forms.embed.copy')" icon="i-lucide-copy" color="neutral" class="justify-center" @click="copyCode" />
      </div>
    </template>
  </AppModal>
</template>
