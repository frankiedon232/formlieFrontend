<!-- Validation rules: length, number range, pattern (+ message), file type / size / count, how many choices. -->
<script setup lang="ts">
import { nonPictureTypes } from '#shared/utils/forms/file-types'
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ field: FormField }>()
const { t } = useI18n()
const builder = useBuilder()
const has = (control: InspectorControl) => hasControl(props.field.type, control)

const v = computed(() => (props.field.validation ?? {}) as Record<string, unknown>)
const p = computed(() => (props.field.props ?? {}) as Record<string, unknown>)
const num = (value: unknown) =>
  value === '' || value == null || Number.isNaN(Number(value)) ? null : Number(value)
const setRule = (patch: Record<string, unknown>) =>
  builder.updateField(
    props.field.id,
    { validation: { ...v.value, ...patch } },
    `rules:${props.field.id}:${Object.keys(patch)[0]}`,
  )
const setProp = (patch: Record<string, unknown>) => builder.updateProps(props.field.id, patch)

const patternError = computed(() => {
  const pattern = String(v.value.pattern ?? '')
  if (!pattern) return null
  try {
    new RegExp(pattern)
    return null
  } catch {
    return t('builder.inspector.patternInvalid')
  }
})
const range = (min: unknown, max: unknown) =>
  num(min) !== null && num(max) !== null && Number(min) > Number(max)
    ? t('builder.inspector.minAboveMax')
    : undefined
</script>

<template>
  <section class="flex flex-col gap-3">
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.inspector.rules') }}</h3>

    <div v-if="has('length')" class="grid grid-cols-2 gap-2">
      <UFormField :label="t('builder.inspector.minLength')" :error="range(v.min_length, v.max_length)">
        <UInput
          type="number"
          min="0"
          :model-value="String(v.min_length ?? '')"
          class="w-full"
          @update:model-value="x => setRule({ min_length: num(x) })"
        />
      </UFormField>
      <UFormField :label="t('builder.inspector.maxLength')">
        <UInput
          type="number"
          min="1"
          :model-value="String(v.max_length ?? '')"
          class="w-full"
          @update:model-value="x => setRule({ max_length: num(x) })"
        />
      </UFormField>
    </div>

    <div v-if="has('range')" class="grid grid-cols-2 gap-2">
      <UFormField :label="t('builder.inspector.minValue')" :error="range(v.min, v.max)">
        <UInput
          type="number"
          :model-value="String(v.min ?? '')"
          class="w-full"
          @update:model-value="x => setRule({ min: num(x) })"
        />
      </UFormField>
      <UFormField :label="t('builder.inspector.maxValue')">
        <UInput
          type="number"
          :model-value="String(v.max ?? '')"
          class="w-full"
          @update:model-value="x => setRule({ max: num(x) })"
        />
      </UFormField>
    </div>

    <template v-if="has('pattern')">
      <UFormField
        :label="t('builder.inspector.pattern')"
        :description="t('builder.inspector.patternHint')"
        :error="patternError ?? undefined"
      >
        <UInput
          :model-value="String(v.pattern ?? '')"
          class="w-full font-mono"
          placeholder="^[A-Z]{2}\d{6}$"
          @update:model-value="x => setRule({ pattern: String(x) || null })"
        />
      </UFormField>
      <UFormField v-if="v.pattern" :label="t('builder.inspector.patternMessage')">
        <UInput
          :model-value="String(v.pattern_message ?? '')"
          class="w-full"
          @update:model-value="x => setRule({ pattern_message: String(x) || null })"
        />
      </UFormField>
    </template>

    <div v-if="has('selection_count')" class="grid grid-cols-2 gap-2">
      <UFormField :label="t('builder.inspector.minChoices')" :error="range(v.min_selected, v.max_selected)">
        <UInput
          type="number"
          min="0"
          :model-value="String(v.min_selected ?? '')"
          class="w-full"
          @update:model-value="x => setRule({ min_selected: num(x) })"
        />
      </UFormField>
      <UFormField :label="t('builder.inspector.maxChoices')">
        <UInput
          type="number"
          min="1"
          :model-value="String(v.max_selected ?? '')"
          class="w-full"
          @update:model-value="x => setRule({ max_selected: num(x) })"
        />
      </UFormField>
    </div>

    <template v-if="has('files')">
      <!-- Image questions take pictures only (owner, 2026-10-04): a PDF set here would always be refused. -->
      <UAlert
        v-if="field.type === 'image_upload' && nonPictureTypes(String(p.accept ?? '')).length"
        icon="i-lucide-file-warning"
        color="warning"
        variant="subtle"
        :title="t('builder.files.notPictures', { types: nonPictureTypes(String(p.accept ?? '')).join(', ') })"
        :description="t('builder.files.notPicturesDesc')"
        :actions="[{ label: t('builder.files.toFileUpload'), color: 'neutral', variant: 'outline', icon: 'i-lucide-file-up', onClick: () => builder.updateField(field.id, { type: 'file_upload' }) }]"
      />
      <FormsBuilderInspectorFileTypes :accept="String(p.accept ?? '')" :pictures-only="field.type === 'image_upload'" @update="accept => setProp({ accept })" />
      <div class="grid grid-cols-2 gap-2">
        <UFormField :label="t('builder.inspector.maxFiles')">
          <UInputNumber
            :model-value="Number(p.max_files ?? 1)"
            :min="1"
            :max="20"
            class="w-full"
            @update:model-value="x => setProp({ max_files: x ?? 1 })"
          />
        </UFormField>
        <UFormField :label="t('builder.inspector.maxSize')">
          <UInputNumber
            :model-value="Number(p.max_mb ?? 10)"
            :min="1"
            :max="25"
            class="w-full"
            @update:model-value="x => setProp({ max_mb: x ?? 10 })"
          />
        </UFormField>
      </div>
    </template>
  </section>
</template>
