<!--
  One form field as respondents see it (FRONTEND-SPEC §6: the same renderer serves the builder
  canvas, preview, public form and embed). Label · required mark · control · help · error.
  `builder` mode renders a faithful, non-interactive preview.
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'
import { isInputField } from '#shared/utils/forms/fields'

const props = withDefaults(defineProps<{ field: FormField; mode?: 'builder' | 'live'; error?: string }>(), {
  mode: 'live',
  error: undefined,
})
const value = defineModel<unknown>()
const { t } = useI18n()

const id = computed(() => `f-${props.field.id}`)
const showLabel = computed(() => isInputField(props.field.type) && props.field.type !== 'hidden')

const CONTROLS: Record<string, string> = {
  short_text: 'Text',
  long_text: 'Text',
  rich_text: 'Text',
  email: 'Text',
  phone: 'Text',
  url: 'Text',
  number: 'Text',
  currency: 'Text',
  calculated: 'Text',
  hidden: 'Text',
  date: 'DateTime',
  time: 'DateTime',
  datetime: 'DateTime',
  date_range: 'DateTime',
  dropdown: 'Choice',
  multi_select: 'Choice',
  radio: 'Choice',
  checkbox: 'Choice',
  toggle: 'Choice',
  ranking: 'Ranking',
  matrix: 'Matrix',
  rating: 'Rating',
  scale: 'Rating',
  slider: 'Rating',
  file_upload: 'Files',
  image_upload: 'Files',
  signature: 'Files',
  payment: 'Files',
  address: 'Address',
  country: 'Address',
  section: 'Layout',
  paragraph: 'Layout',
  divider: 'Layout',
  image: 'Layout',
}
const control = computed(() => CONTROLS[props.field.type] ?? 'Text')
</script>

<template>
  <div class="flex flex-col gap-1.5" :data-field-type="field.type">
    <label v-if="showLabel" :for="id" class="text-sm font-medium text-highlighted">
      {{ field.label || t('builder.untitled') }}
      <span v-if="field.required" class="text-error" aria-hidden="true">*</span>
      <span v-if="field.required" class="sr-only">({{ t('renderer.required') }})</span>
    </label>

    <FormsRendererText v-if="control === 'Text'" :id="id" v-model="value" :field="field" :mode="mode" />
    <FormsRendererDateTime
      v-else-if="control === 'DateTime'"
      :id="id"
      v-model="value"
      :field="field"
      :mode="mode"
    />
    <FormsRendererChoice
      v-else-if="control === 'Choice'"
      :id="id"
      v-model="value"
      :field="field"
      :mode="mode"
    />
    <FormsRendererRanking
      v-else-if="control === 'Ranking'"
      :id="id"
      v-model="value"
      :field="field"
      :mode="mode"
    />
    <FormsRendererMatrix
      v-else-if="control === 'Matrix'"
      :id="id"
      v-model="value"
      :field="field"
      :mode="mode"
    />
    <FormsRendererRating
      v-else-if="control === 'Rating'"
      :id="id"
      v-model="value"
      :field="field"
      :mode="mode"
    />
    <FormsRendererFiles
      v-else-if="control === 'Files'"
      :id="id"
      v-model="value"
      :field="field"
      :mode="mode"
    />
    <FormsRendererAddress
      v-else-if="control === 'Address'"
      :id="id"
      v-model="value"
      :field="field"
      :mode="mode"
    />
    <FormsRendererLayout v-else :field="field" :mode="mode" />

    <p v-if="field.help && showLabel" class="text-xs text-muted">{{ field.help }}</p>
    <p v-if="error" class="text-xs text-error" role="alert">{{ error }}</p>
  </div>
</template>
