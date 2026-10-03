<!-- Type-specific settings: scale / slider / rating / currency / content / collapsible / image / formula. -->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ field: FormField }>()
const { t } = useI18n()
const builder = useBuilder()
const currencies = useCurrencyOptions()

const has = (control: InspectorControl) => hasControl(props.field.type, control)
const setProp = (patch: Record<string, unknown>, group?: string) => builder.updateProps(props.field.id, patch, group)
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
      has('address_parts') ||
      has('ip_version') ||
      has('name_parts') ||
      has('consent_text') ||
      has('rich_toolbar') ||
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
    <UFormField v-if="has('rich_toolbar')" :label="t('builder.inspector.toolbar')" :description="t('builder.inspector.toolbarHint')">
      <UTabs
        :model-value="String(p.toolbar ?? 'full')"
        :items="[
          { value: 'basic', label: t('builder.inspector.toolbarBasic') },
          { value: 'full', label: t('builder.inspector.toolbarFull') },
        ]"
        :content="false"
        color="neutral"
        size="xs"
        :ui="{ ...SEGMENTED_UI, trigger: `${SEGMENTED_UI.trigger} flex-1` }"
        class="w-full"
        @update:model-value="v => setProp({ toolbar: v })"
      />
    </UFormField>
    <UFormField v-if="has('ip_version')" :label="t('builder.inspector.ipVersion')">
      <UTabs
        :model-value="String(p.ip_version ?? 'any')"
        :items="[
          { value: 'any', label: t('builder.inspector.ipAny') },
          { value: 'v4', label: 'IPv4' },
          { value: 'v6', label: 'IPv6' },
        ]"
        :content="false"
        color="neutral"
        size="xs"
        :ui="{ ...SEGMENTED_UI, trigger: `${SEGMENTED_UI.trigger} flex-1` }"
        class="w-full"
        @update:model-value="v => setProp({ ip_version: v })"
      />
    </UFormField>
    <template v-if="has('name_parts')">
      <USwitch :model-value="!!p.show_title" :label="t('builder.inspector.nameTitle')" color="neutral" @update:model-value="v => setProp({ show_title: v })" />
      <USwitch :model-value="!!p.show_middle" :label="t('builder.inspector.nameMiddle')" color="neutral" @update:model-value="v => setProp({ show_middle: v })" />
      <p class="text-xs text-muted">{{ t('builder.inspector.nameHint') }}</p>
    </template>
    <template v-if="has('consent_text')">
      <UFormField :label="t('builder.inspector.consentText')" :description="t('builder.inspector.consentTextHint')">
        <UTextarea :model-value="String(p.text ?? '')" :rows="3" autoresize maxlength="1000" class="w-full" @update:model-value="v => setProp({ text: String(v) }, `consent:${field.id}:text`)" />
      </UFormField>
      <UFormField :label="t('builder.inspector.consentLink')" :error="p.link_href && !/^https:\/\/\S+$/i.test(String(p.link_href)) ? t('builder.blocks.linkInvalid') : undefined">
        <UInput :model-value="String(p.link_href ?? '')" type="url" placeholder="https://" icon="i-lucide-link" class="w-full" @update:model-value="v => setProp({ link_href: String(v) }, `consent:${field.id}:href`)" />
      </UFormField>
      <UFormField :label="t('builder.inspector.consentLinkLabel')">
        <UInput :model-value="String(p.link_label ?? '')" :placeholder="t('renderer.consent.link')" class="w-full" @update:model-value="v => setProp({ link_label: String(v) }, `consent:${field.id}:label`)" />
      </UFormField>
    </template>
    <template v-if="has('address_parts')">
      <p class="text-xs text-muted">{{ t('builder.inspector.addressParts') }}</p>
      <USwitch
        :model-value="p.require_postal_code !== false"
        :label="t('builder.inspector.requirePostal')"
        :description="t('builder.inspector.requirePostalHint')"
        color="neutral"
        @update:model-value="v => setProp({ require_postal_code: v })"
      />
      <USwitch
        :model-value="p.require_region === true"
        :label="t('builder.inspector.requireRegion')"
        color="neutral"
        @update:model-value="v => setProp({ require_region: v })"
      />
    </template>
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
    <!-- Internal results (risk level, loyalty group…) are worked out but not shown to respondents. -->
    <USwitch
      v-if="has('formula')"
      :model-value="!p.internal"
      :label="t('builder.inspector.showResult')"
      :description="p.internal ? t('builder.inspector.internalHint') : undefined"
      color="neutral"
      @update:model-value="v => setProp({ internal: !v })"
    />
  </section>

</template>
