<!--
  Embed code (F10 M2): the ready `<iframe>` to paste into a website — auto height (the frame grows
  and shrinks with the form; recommended) or a fixed height. Code from shared/utils/urls/embed.ts.
  Live preview tab: the real embed, sized like on a website. Allowed websites: Share tab → Embed.
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

// Live preview (F10 M3): the real embed in a frame, sized by the same messages the embed code uses.
const view = ref<'code' | 'preview'>('code')
const views = computed(() => [
  { value: 'code', label: t('forms.embed.code'), icon: 'i-lucide-code-xml' },
  { value: 'preview', label: t('forms.embed.preview'), icon: 'i-lucide-eye' },
])
const frame = useTemplateRef<HTMLIFrameElement>('frame')
const previewHeight = ref(480)
const previewLoading = ref(true)
const origin = computed(() => {
  try {
    return new URL(props.url).origin
  } catch {
    return ''
  }
})
useEventListener(import.meta.client ? window : null, 'message', (event: MessageEvent) => {
  const data = event.data as { type?: string; height?: number } | null
  if (event.origin !== origin.value || data?.type !== 'formalie:resize' || event.source !== frame.value?.contentWindow) return
  if (mode.value === 'auto' && typeof data.height === 'number') previewHeight.value = Math.ceil(data.height)
})
watch(open, value => value && ((view.value = 'code'), (previewLoading.value = true)))
watch(view, value => value === 'preview' && (previewLoading.value = true))

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
        <UTabs v-model="view" :items="views" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="w-full" :aria-label="t('forms.embed.title')" />
        <div v-if="view === 'preview'" class="flex flex-col gap-1.5">
          <p class="flex items-start gap-1.5 text-xs text-muted"><UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" />{{ t('forms.embed.previewNote') }}</p>
          <div class="relative max-h-[28rem] overflow-auto rounded-md border border-default bg-elevated/40 p-2">
            <div v-if="previewLoading" class="absolute inset-2 flex items-center justify-center"><USkeleton class="h-64 w-full" /></div>
            <iframe
              ref="frame"
              :src="url"
              :title="formName"
              class="w-full rounded border-0 bg-default"
              :style="{ height: `${mode === 'auto' ? previewHeight : clampEmbedHeight(height)}px` }"
              loading="lazy"
              @load="previewLoading = false"
            />
          </div>
        </div>
        <div v-else class="flex flex-col gap-1.5">
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
