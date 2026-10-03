<!--
  Live preview of the draft (or of a published version via `schema`): fill it in like a
  respondent, on desktop / tablet / phone widths. Nothing is sent.
-->
<script setup lang="ts">
import type { FormSchemaV1 } from '#shared/utils/forms/schema'

const props = defineProps<{ schema?: FormSchemaV1 | null; title?: string; formName?: string }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const builder = useBuilder()
const shown = computed(() => props.schema ?? builder.schema.value)

const device = ref<'desktop' | 'tablet' | 'phone'>('desktop')
const devices = computed(() => [
  { value: 'desktop', label: t('builder.preview.desktop'), icon: 'i-lucide-monitor' },
  { value: 'tablet', label: t('builder.preview.tablet'), icon: 'i-lucide-tablet' },
  { value: 'phone', label: t('builder.preview.phone'), icon: 'i-lucide-smartphone' },
])
// Desktop is the real thing: the whole screen, edge to edge (owner, 2026-10-03 — not a box).
// Tablet and phone show a device-sized frame in a panel that fits it.
const PANEL = { desktop: 'w-full sm:max-w-none', tablet: 'w-full sm:max-w-[52rem]', phone: 'w-full sm:max-w-lg' }
const FRAME = {
  desktop: 'h-full',
  tablet: 'max-w-[768px] min-h-full rounded-lg border border-default',
  phone: 'max-w-[390px] min-h-full rounded-lg border border-default',
}
// Remount on open so the preview always starts from page 1 with the latest draft.
const key = ref(0)
watch(open, value => {
  if (value) key.value++
})
</script>

<template>
  <USlideover
    v-model:open="open"
    :title="title ?? t('builder.preview.title')"
    :description="t('builder.preview.desc')"
    :ui="{
      content: `${PANEL[device]} transition-[max-width] duration-300`,
      body: device === 'desktop' ? 'p-0 sm:p-0' : 'bg-elevated/40 p-3 sm:p-4',
    }"
  >
    <template #actions>
      <UTabs
        v-model="device"
        :items="devices"
        :content="false"
        color="neutral"
        size="xs"
        :ui="{ ...SEGMENTED_UI, label: 'hidden md:inline' }"
        class="hidden sm:flex"
        :aria-label="t('builder.preview.device')"
      />
    </template>
    <template #body>
      <div class="mx-auto w-full overflow-hidden transition-[max-width] duration-300 @container" :class="FRAME[device]">
        <!-- The form page with its theme (background, header, footer), exactly as respondents see it. -->
        <FormsRendererPage v-if="shown" :key="key" :schema="shown" :title="formName ?? ''" preview />
      </div>
    </template>
  </USlideover>
</template>
