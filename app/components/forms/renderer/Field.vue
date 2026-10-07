<!--
  One form field as respondents see it (FRONTEND-SPEC §6: the same renderer serves the builder
  canvas, preview, public form and embed). Label · required mark · info icon (help text in a
  popover) · control · error. Labels sit on top or, with `label-position="left"`, beside the
  control, right next to it: every label has the same width (the form's `--form-label-w`, from its
  longest label, max 30 %) and is end-aligned, so labels hug their inputs and all inputs line up, decided by the width of the whole form (`@container/form`), so half-width fields
  keep their label beside too; a phone-width form stacks. In `builder` mode the
  control works for trying it out; the canvas never stores what you type. `#label` lets the
  builder swap the label for an inline editor.
-->
<script setup lang="ts">
import { isRestricted, type FormField } from '#shared/utils/forms/build'
import { isInputField } from '#shared/utils/forms/fields'

const props = withDefaults(
  defineProps<{
    field: FormField
    mode?: 'builder' | 'live'
    error?: string
    /** Address: the parts to highlight. */
    errorParts?: string[]
    labelPosition?: 'top' | 'left'
  }>(),
  { mode: 'live', error: undefined, errorParts: undefined, labelPosition: 'top' },
)
const value = defineModel<unknown>()
const { t } = useI18n()

const id = computed(() => `f-${props.field.id}`)
const showLabel = computed(() => isInputField(props.field.type) && props.field.type !== 'hidden')

const CONTROLS: Record<string, string> = {
  short_text: 'Text',
  long_text: 'Text',
  rich_text: 'RichText',
  email: 'Text',
  phone: 'Text',
  url: 'Text',
  number: 'Text',
  currency: 'Text',
  calculated: 'Text',
  hidden: 'Text',
  percentage: 'Text',
  ip_address: 'Text',
  domain: 'Text',
  mac_address: 'Text',
  iban: 'Text',
  bic: 'Text',
  full_name: 'Extra',
  consent: 'Extra',
  color: 'Extra',
  duration: 'Extra',
  language: 'Extra',
  timezone: 'Extra',
  currency_code: 'Extra',
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
/** Yes / No: switch and label on one line (switch first, label right after, like a checkbox). */
const inline = computed(() => props.field.type === 'toggle')
const left = computed(() => props.labelPosition === 'left' && showLabel.value && !inline.value)
// In "beside the field" forms the switch lines up with the other inputs (label column + gap).
</script>

<template>
  <div
    class="flex flex-col gap-1"
    :class="
      inline
        ? [
            'flex-row flex-wrap items-center gap-x-2.5',
            labelPosition === 'left' ? '@md/form:ps-[calc(min(var(--form-label-w,10rem),30%)_+_0.75rem)]' : '',
          ]
        : left
          ? '@md/form:flex-row @md/form:items-start @md/form:gap-3'
          : ''
    "
    :data-field-type="field.type"
  >
    <div
      v-if="showLabel"
      class="flex min-w-0 items-center gap-1"
      :class="
        inline
          ? 'order-2 min-h-6'
          : left
          ? '@md/form:min-h-8 @md/form:w-[min(var(--form-label-w,10rem),30%)] @md/form:shrink-0 @md/form:justify-end @md/form:text-end'
          : ''
      "
    >
      <slot name="label">
        <label :for="id" class="min-w-0 text-sm font-medium text-highlighted">
          {{ field.label || t('builder.untitled') }}
          <span v-if="field.required" class="text-error" aria-hidden="true">*</span>
          <span v-if="field.required" class="sr-only">({{ t('renderer.required') }})</span>
        </label>
      </slot>
      <!-- Field access: only some departments, roles or people (public respondents never see it, F10). -->
      <UTooltip v-if="isRestricted(field)" :text="t('renderer.restricted')">
        <UIcon name="i-lucide-lock" class="size-3.5 shrink-0 text-muted" role="img" :aria-label="t('renderer.restricted')" />
      </UTooltip>
      <UPopover v-if="field.help" :content="{ side: 'top', align: 'start' }" arrow>
        <UButton
          icon="i-lucide-info"
          color="neutral"
          variant="link"
          size="xs"
          class="shrink-0 p-0.5 text-muted"
          :aria-label="t('renderer.moreInfo', { field: field.label || t('builder.untitled') })"
          @click.stop
        />
        <template #content>
          <p class="max-w-72 p-3 text-xs whitespace-pre-line text-default">{{ field.help }}</p>
        </template>
      </UPopover>
    </div>

    <div class="flex min-w-0 flex-col gap-1" :class="inline ? 'order-1 flex-none' : 'flex-1'">
    <FormsRendererText v-if="control === 'Text'" :id="id" v-model="value" :field="field" :mode="mode" />
    <FormsRendererRichText v-else-if="control === 'RichText'" :id="id" v-model="value" :field="field" :mode="mode" />
    <FormsRendererExtra v-else-if="control === 'Extra'" :id="id" v-model="value" :field="field" :mode="mode" />
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
      :error-parts="errorParts"
    />
    <FormsRendererLayout v-else :field="field" :mode="mode">
      <template v-if="$slots.label" #label><slot name="label" /></template>
      <template v-if="$slots.description" #description><slot name="description" /></template>
    </FormsRendererLayout>

    <p v-if="error && !inline" class="text-xs text-error" role="alert">{{ error }}</p>
    </div>
    <p v-if="error && inline" class="order-3 basis-full text-xs text-error" role="alert">{{ error }}</p>
  </div>
</template>
