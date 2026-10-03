<!--
  Live template preview (F9): the real form page in the template's design, on desktop / tablet /
  phone widths, questions or thank-you page. Try it out — nothing is saved or sent.
-->
<script setup lang="ts">
import type { FormSchemaV1 } from '#shared/utils/forms/schema'

defineProps<{ schema: FormSchemaV1; title: string }>()
const { t } = useI18n()

const device = ref<'desktop' | 'tablet' | 'phone'>('desktop')
const devices = computed(() => [
  { value: 'desktop', label: t('builder.preview.desktop'), icon: 'i-lucide-monitor' },
  { value: 'tablet', label: t('builder.preview.tablet'), icon: 'i-lucide-tablet' },
  { value: 'phone', label: t('builder.preview.phone'), icon: 'i-lucide-smartphone' },
])
const WIDTH = { desktop: 'max-w-full', tablet: 'max-w-[768px]', phone: 'max-w-[390px]' }
const screen = ref<'questions' | 'thanks'>('questions')
const screens = computed(() => [
  { value: 'questions', label: t('designer.screen.form') },
  { value: 'thanks', label: t('designer.screen.thanks') },
])
</script>

<template>
  <section class="flex min-w-0 flex-col gap-3 rounded-lg border border-default bg-elevated/40 p-2 sm:p-3" :aria-label="t('templates.preview')">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <UTabs
        v-model="screen"
        :items="screens"
        :content="false"
        color="neutral"
        size="xs"
        :ui="SEGMENTED_UI"
        :aria-label="t('templates.preview')"
      />
      <UTabs
        v-model="device"
        :items="devices"
        :content="false"
        color="neutral"
        size="xs"
        :ui="{ ...SEGMENTED_UI, label: 'hidden sm:inline' }"
        class="hidden sm:flex"
        :aria-label="t('builder.preview.device')"
      />
    </div>
    <div class="mx-auto h-[70vh] min-h-96 w-full overflow-y-auto rounded-md border border-default transition-[max-width] duration-300 @container" :class="WIDTH[device]">
      <FormsRendererPage :schema="schema" :title="title" preview :show-thank-you="screen === 'thanks'" />
    </div>
  </section>
</template>
