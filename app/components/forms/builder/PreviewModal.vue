<!--
  Live preview of the draft (or of a published version via `schema`): fill it in like a
  respondent, on desktop / tablet / phone widths. Nothing is sent.
-->
<script setup lang="ts">
import type { FormSchemaV1 } from '#shared/utils/forms/schema'

const props = defineProps<{ schema?: FormSchemaV1 | null; title?: string }>()
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
const WIDTH = { desktop: 'max-w-3xl', tablet: 'max-w-[768px]', phone: 'max-w-[390px]' }
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
    :ui="{ content: 'w-full sm:max-w-5xl', body: 'bg-elevated/40' }"
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
      <div class="mx-auto w-full transition-[max-width] duration-300" :class="WIDTH[device]">
        <UCard :ui="{ body: 'p-4 sm:p-8' }">
          <FormsRendererForm v-if="shown" :key="key" :schema="shown" preview />
        </UCard>
      </div>
    </template>
  </USlideover>
</template>
