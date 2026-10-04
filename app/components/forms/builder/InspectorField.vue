<!-- Inspector for one field: basics · options · rules · type settings · default & prefill · advanced. -->
<script setup lang="ts">
import { cannotBeRequired, isLocked, type FormField } from '#shared/utils/forms/build'
import { FIELD_WIDTHS } from '#shared/utils/forms/fields'

const props = defineProps<{ field: FormField }>()
const { t } = useI18n()
const builder = useBuilder()

const has = (control: InspectorControl) => hasControl(props.field.type, control)
const set = (patch: Partial<FormField>) => builder.updateField(props.field.id, patch)
const setProp = (patch: Record<string, unknown>) => builder.updateProps(props.field.id, patch)
const p = computed(() => (props.field.props ?? {}) as Record<string, unknown>)

const widths = computed(() =>
  FIELD_WIDTHS.map(width => ({ value: String(width), label: t(`builder.widthShort.${width}`) })),
)

const setLabel = (label: string) => builder.renameField(props.field.id, label)

// Answer access: editable · read-only (shown + submitted) · disabled (greyed, not submitted).
// Locked fields can never be required, turning one on switches "required" off.
const access = computed(() => (props.field.disabled ? 'disabled' : props.field.readonly ? 'readonly' : 'editable'))
const accessItems = computed(() => [
  { value: 'editable', label: t('builder.access.editable') },
  { value: 'readonly', label: t('builder.access.readonly') },
  { value: 'disabled', label: t('builder.access.disabled') },
])
const locked = computed(() => isLocked(props.field))
/** Locked or restricted to some people: "required" is off and can't be switched on. */
const noRequired = computed(() => cannotBeRequired(props.field))
const noRequiredHint = computed(() =>
  // Restricted fields: the reason is shown once, in the Field access section below.
  locked.value ? t('builder.access.noRequired') : undefined,
)
function setAccess(next: string | number) {
  set({ readonly: next === 'readonly', disabled: next === 'disabled', ...(next !== 'editable' ? { required: false } : {}) })
}
const hasAccess = computed(() => has('required') && props.field.type !== 'calculated')
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
      <UFormField v-if="hasAccess" :label="t('builder.access.label')" :description="t(`builder.access.${access}Hint`)">
        <UTabs
          :model-value="access"
          :items="accessItems"
          :content="false"
          color="neutral"
          size="xs"
          :ui="{ ...SEGMENTED_UI, trigger: `${SEGMENTED_UI.trigger} flex-1 px-1.5` }"
          class="w-full"
          @update:model-value="setAccess"
        />
      </UFormField>
      <USwitch
        v-if="has('required')"
        :model-value="!!field.required && !noRequired"
        :disabled="noRequired"
        :label="t('builder.inspector.required')"
        :description="noRequiredHint"
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

    <FormsBuilderInspectorAudience v-if="hasAccess" :field="field" />

    <FormsBuilderInspectorOptions v-if="has('options') || has('matrix_rows')" :field="field" />

    <FormsBuilderInspectorRules
      v-if="has('length') || has('range') || has('pattern') || has('files') || has('selection_count')"
      :field="field"
    />

    <FormsBuilderInspectorSettings :field="field" />
    <FormsBuilderInspectorBlocks :field="field" />

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
      <AppCopyField :label="t('builder.inspector.key')" :value="field.key" monospace />
      <p class="-mt-1 text-xs text-muted">{{ t('builder.inspector.keyHint') }}</p>
    </section>
  </div>
</template>
