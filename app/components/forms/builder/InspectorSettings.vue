<!-- Type-specific settings: scale / slider / rating / currency / content / collapsible / image / formula. -->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ field: FormField }>()
const { t } = useI18n()
const builder = useBuilder()
const currencies = useCurrencyOptions()

const has = (control: InspectorControl) => hasControl(props.field.type, control)
const setProp = (patch: Record<string, unknown>) => builder.updateProps(props.field.id, patch)
const p = computed(() => (props.field.props ?? {}) as Record<string, unknown>)
const num = (value: unknown) =>
  value === '' || value == null || Number.isNaN(Number(value)) ? undefined : Number(value)
</script>

<template>
  <section
    v-if="
      has('scale') ||
      has('rating') ||
      has('slider') ||
      has('currency') ||
      has('content') ||
      has('collapsible') ||
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
    <template v-if="has('collapsible')">
      <USwitch
        :model-value="!!p.collapsible"
        :label="t('builder.inspector.collapsible')"
        :description="t('builder.inspector.collapsibleHint')"
        color="neutral"
        @update:model-value="v => setProp({ collapsible: v, ...(v ? {} : { collapsed: false }) })"
      />
      <USwitch
        v-if="p.collapsible"
        :model-value="!!p.collapsed"
        :label="t('builder.inspector.startCollapsed')"
        color="neutral"
        @update:model-value="v => setProp({ collapsed: v })"
      />
    </template>
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

</template>
