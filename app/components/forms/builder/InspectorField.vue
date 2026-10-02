<!-- Inspector for one field: basics · options · rules · type settings · default & prefill · advanced. -->
<script setup lang="ts">
import { keyFromLabel, type FormField } from '#shared/utils/forms/build'
import { FIELD_WIDTHS } from '#shared/utils/forms/fields'

const props = defineProps<{ field: FormField }>()
const { t } = useI18n()
const builder = useBuilder()
const currencies = useCurrencyOptions()

const has = (control: InspectorControl) => hasControl(props.field.type, control)
const set = (patch: Partial<FormField>) => builder.updateField(props.field.id, patch)
const setProp = (patch: Record<string, unknown>) => builder.updateProps(props.field.id, patch)
const p = computed(() => (props.field.props ?? {}) as Record<string, unknown>)
const num = (value: unknown) =>
  value === '' || value == null || Number.isNaN(Number(value)) ? undefined : Number(value)

const widths = computed(() =>
  FIELD_WIDTHS.map(width => ({ value: String(width), label: t(`builder.widthShort.${width}`) })),
)

// Field key: lower-case, unique; invalid input is shown, not saved.
const keyDraft = ref(props.field.key)
watch(
  () => props.field.key,
  key => (keyDraft.value = key),
)
const keyError = computed(() => {
  if (!/^[a-z][a-z0-9_]{0,63}$/.test(keyDraft.value)) return t('builder.inspector.keyInvalid')
  if (builder.fields.value.some(f => f.id !== props.field.id && f.key === keyDraft.value))
    return t('builder.inspector.keyTaken')
  return null
})
function saveKey() {
  if (!keyError.value) set({ key: keyDraft.value })
}
/** While drafting, the key follows the label ("Full name" → full_name) unless it was edited. */
function setLabel(label: string) {
  const others = builder.fields.value.filter(f => f.id !== props.field.id).map(f => f.key)
  const followsLabel =
    !builder.keysLocked.value && props.field.key === keyFromLabel(props.field.label, others)
  builder.updateField(
    props.field.id,
    followsLabel ? { label, key: keyFromLabel(label || props.field.type, others) } : { label },
    `field:${props.field.id}:label`,
  )
}
const prefillExample = computed(() => `?${String(p.value.prefill_param || props.field.key)}=…`)
</script>

<template>
  <div class="flex flex-col gap-6">
    <section class="flex flex-col gap-3">
      <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.inspector.basics') }}</h3>
      <UFormField
        v-if="has('label')"
        :label="field.type === 'section' ? t('builder.inspector.title') : t('builder.inspector.label')"
      >
        <UInput :model-value="field.label" class="w-full" @update:model-value="v => setLabel(String(v))" />
      </UFormField>
      <UFormField v-if="has('help')" :label="t('builder.inspector.help')">
        <UTextarea
          :model-value="field.help ?? ''"
          :rows="2"
          autoresize
          class="w-full"
          @update:model-value="v => set({ help: String(v) })"
        />
      </UFormField>
      <UFormField v-if="has('placeholder')" :label="t('builder.inspector.placeholder')">
        <UInput
          :model-value="field.placeholder ?? ''"
          class="w-full"
          @update:model-value="v => set({ placeholder: String(v) })"
        />
      </UFormField>
      <USwitch
        v-if="has('required')"
        :model-value="!!field.required"
        :label="t('builder.inspector.required')"
        color="neutral"
        @update:model-value="v => set({ required: v })"
      />
      <UFormField v-if="has('width')" :label="t('builder.inspector.width')">
        <UTabs
          :model-value="String(field.width ?? 12)"
          :items="widths"
          :content="false"
          color="neutral"
          size="xs"
          :ui="SEGMENTED_UI"
          class="w-full"
          @update:model-value="v => builder.setWidth([field.id], Number(v))"
        />
      </UFormField>
    </section>

    <FormsBuilderInspectorOptions v-if="has('options') || has('matrix_rows')" :field="field" />

    <FormsBuilderInspectorRules
      v-if="has('length') || has('range') || has('pattern') || has('files') || has('selection_count')"
      :field="field"
    />

    <section
      v-if="
        has('scale') ||
        has('rating') ||
        has('slider') ||
        has('currency') ||
        has('content') ||
        has('image') ||
        has('formula')
      "
      class="flex flex-col gap-3"
    >
      <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.inspector.settings') }}</h3>
      <div v-if="has('scale') || has('slider')" class="grid grid-cols-2 gap-2">
        <UFormField :label="t('builder.inspector.min')">
          <UInput
            type="number"
            :model-value="String(p.min ?? 0)"
            class="w-full"
            @update:model-value="v => setProp({ min: num(v) ?? 0 })"
          />
        </UFormField>
        <UFormField :label="t('builder.inspector.max')">
          <UInput
            type="number"
            :model-value="String(p.max ?? 10)"
            class="w-full"
            @update:model-value="v => setProp({ max: num(v) ?? 10 })"
          />
        </UFormField>
      </div>
      <template v-if="has('scale')">
        <UFormField :label="t('builder.inspector.minLabel')">
          <UInput
            :model-value="String(p.min_label ?? '')"
            class="w-full"
            @update:model-value="v => setProp({ min_label: String(v) })"
          />
        </UFormField>
        <UFormField :label="t('builder.inspector.maxLabel')">
          <UInput
            :model-value="String(p.max_label ?? '')"
            class="w-full"
            @update:model-value="v => setProp({ max_label: String(v) })"
          />
        </UFormField>
      </template>
      <UFormField v-if="has('slider')" :label="t('builder.inspector.step')">
        <UInput
          type="number"
          min="0"
          :model-value="String(p.step ?? 1)"
          class="w-full"
          @update:model-value="v => setProp({ step: num(v) ?? 1 })"
        />
      </UFormField>
      <UFormField v-if="has('rating')" :label="t('builder.inspector.stars')">
        <UInputNumber
          :model-value="Number(p.max ?? 5)"
          :min="3"
          :max="10"
          class="w-full"
          @update:model-value="v => setProp({ max: v ?? 5 })"
        />
      </UFormField>
      <UFormField v-if="has('currency')" :label="t('builder.inspector.currency')">
        <USelectMenu
          :model-value="String(p.currency ?? 'USD')"
          :items="currencies"
          value-key="value"
          :search-input="{ placeholder: t('common.search') }"
          class="w-full"
          @update:model-value="v => setProp({ currency: v })"
        />
      </UFormField>
      <UFormField
        v-if="has('content')"
        :label="field.type === 'paragraph' ? t('builder.inspector.text') : t('builder.inspector.description')"
      >
        <UTextarea
          :model-value="String((field.type === 'paragraph' ? p.text : p.description) ?? '')"
          :rows="4"
          autoresize
          class="w-full"
          @update:model-value="
            v => setProp(field.type === 'paragraph' ? { text: String(v) } : { description: String(v) })
          "
        />
      </UFormField>
      <template v-if="has('image')">
        <UFormField :label="t('builder.inspector.imageUrl')" :hint="t('builder.inspector.imageHint')">
          <UInput
            type="url"
            :model-value="String(p.src ?? '')"
            placeholder="https://"
            class="w-full"
            @update:model-value="v => setProp({ src: String(v) })"
          />
        </UFormField>
        <UFormField :label="t('builder.inspector.alt')" :description="t('builder.inspector.altHint')">
          <UInput
            :model-value="String(p.alt ?? '')"
            class="w-full"
            @update:model-value="v => setProp({ alt: String(v) })"
          />
        </UFormField>
      </template>
      <UFormField
        v-if="has('formula')"
        :label="t('builder.inspector.formula')"
        :description="t('builder.inspector.formulaHint')"
      >
        <UInput
          :model-value="String(p.formula ?? '')"
          class="w-full font-mono"
          placeholder="{quantity} * {price}"
          @update:model-value="v => setProp({ formula: String(v) })"
        />
      </UFormField>
    </section>

    <section
      v-if="has('default_text') || has('default_toggle') || has('prefill')"
      class="flex flex-col gap-3"
    >
      <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.inspector.defaults') }}</h3>
      <UFormField v-if="has('default_text')" :label="t('builder.inspector.default')">
        <UInput
          :model-value="String(field.default ?? '')"
          class="w-full"
          @update:model-value="v => set({ default: String(v) || null })"
        />
      </UFormField>
      <USwitch
        v-if="has('default_toggle')"
        :model-value="field.default === true"
        :label="t('builder.inspector.defaultOn')"
        color="neutral"
        @update:model-value="v => set({ default: v })"
      />
      <UFormField
        v-if="has('prefill')"
        :label="t('builder.inspector.prefill')"
        :description="t('builder.inspector.prefillHint', { example: prefillExample })"
      >
        <UInput
          :model-value="String(p.prefill_param ?? '')"
          :placeholder="field.key"
          class="w-full font-mono"
          @update:model-value="v => setProp({ prefill_param: String(v).replace(/[^a-zA-Z0-9_-]/g, '') })"
        />
      </UFormField>
    </section>

    <section class="flex flex-col gap-3">
      <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.inspector.advanced') }}</h3>
      <UFormField
        :label="t('builder.inspector.key')"
        :description="t('builder.inspector.keyHint')"
        :error="keyError ?? undefined"
      >
        <UInput v-model="keyDraft" class="w-full font-mono" @blur="saveKey" @keydown.enter="saveKey" />
      </UFormField>
    </section>
  </div>
</template>
