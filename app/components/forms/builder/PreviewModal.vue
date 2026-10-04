<!--
  Live preview of the draft (or of a published version via `schema`): fill it in like a
  respondent, on desktop / tablet / phone widths. Nothing is sent.
-->
<script setup lang="ts">
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { formLanguages, translateSchema } from '#shared/utils/forms/translations'

const props = defineProps<{ schema?: FormSchemaV1 | null; title?: string; formName?: string }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
// Outside the editor (read-only preview for "Can view" people) the schema comes in as a prop.
const builder = useBuilderIfAny()
// In the editor: the full preview page (device frames, live version), after saving the draft.
const session = injectBuilderSession()
const { busy: opening, run } = useBusy()
const openFull = () =>
  run(async () => {
    await session?.autosave.saveNow()
    await navigateTo(`/forms/${session?.formId}/preview?v=draft`)
  })
const base = computed(() => props.schema ?? builder?.schema.value ?? null)
// Forms in several languages (decision 99): the same switcher respondents get.
const languages = computed(() => formLanguages(base.value))
const language = ref('')
watch(languages, offered => !offered.includes(language.value) && (language.value = offered[0] ?? 'en'), { immediate: true })
const shown = computed(() => (base.value ? translateSchema(base.value, language.value) : null))

const device = ref<'desktop' | 'tablet' | 'phone'>('desktop')
const devices = computed(() => [
  { value: 'desktop', label: t('builder.preview.desktop'), icon: 'i-lucide-monitor' },
  { value: 'tablet', label: t('builder.preview.tablet'), icon: 'i-lucide-tablet' },
  { value: 'phone', label: t('builder.preview.phone'), icon: 'i-lucide-smartphone' },
])
// Desktop fills the side panel edge to edge, no frame, no padding (owner, 2026-10-03); the panel
// keeps its size. Tablet and phone show a device-sized frame in a panel that fits it.
const PANEL = { desktop: 'w-full sm:max-w-5xl', tablet: 'w-full sm:max-w-[52rem]', phone: 'w-full sm:max-w-lg' }
const FRAME = {
  // min-h (not h): the page grows and the panel scrolls, a fixed height clipped long forms.
  desktop: 'min-h-full',
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
    :ui="{
      content: `${PANEL[device]} transition-[max-width] duration-300`,
      body: device === 'desktop' ? 'p-0 sm:p-0' : 'bg-elevated/40 p-3 sm:p-4',
    }"
  >
    <template #actions>
      <!-- The note sits behind an icon so the header stays one slim line (owner, 2026-10-04). -->
      <UPopover :content="{ align: 'start' }">
        <UButton icon="i-lucide-info" color="neutral" variant="ghost" size="xs" square :aria-label="t('builder.preview.desc')" />
        <template #content>
          <p class="max-w-64 p-3 text-sm text-default">{{ t('builder.preview.desc') }}</p>
        </template>
      </UPopover>
      <UButton
        v-if="session && !schema"
        icon="i-lucide-maximize-2"
        :label="t('preview.full')"
        color="neutral"
        variant="outline"
        size="xs"
        :loading="opening"
        :ui="{ label: 'hidden md:inline' }"
        @click="openFull"
      />
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
        <FormsRendererPage v-if="shown" :key="key" :schema="shown" :title="formName ?? ''" preview framed :languages="languages" :language="language" @language="language = $event" />
      </div>
    </template>
  </USlideover>
</template>
