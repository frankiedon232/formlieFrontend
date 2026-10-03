<!--
  Global field types: full name (title · first · middle · last), consent (checkbox + text + link),
  colour (picker + hex), duration (hours + minutes), language / time zone / currency (searchable,
  names in the respondent's language). All Nuxt UI; size and style follow the form theme.
-->
<script setup lang="ts">
import { isLocked, type FormField } from '#shared/utils/forms/build'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()
const { t, locale } = useI18n()
const control = useControlStyle()

const locked = computed(() => isLocked(props.field))
const p = computed(() => (props.field.props ?? {}) as Record<string, unknown>)
const obj = computed(() => (value.value && typeof value.value === 'object' ? (value.value as Record<string, unknown>) : {}))
const setPart = (key: string, next: unknown) => (value.value = { ...obj.value, [key]: next === '' ? undefined : next })

// Pick lists, built once per language.
const items = computed(() =>
  props.field.type === 'language'
    ? languageItems(locale.value)
    : props.field.type === 'timezone'
      ? timeZoneItems()
      : props.field.type === 'currency_code'
        ? currencyItems(locale.value)
        : [],
)
const pick = computed({
  get: () => (typeof value.value === 'string' ? value.value : undefined),
  set: next => (value.value = next ?? null),
})

// Colour
const hex = computed(() => (typeof value.value === 'string' && /^#[0-9a-f]{6}$/i.test(value.value) ? value.value : ''))
const safeHref = computed(() => (typeof p.value.link_href === 'string' && /^https:\/\//i.test(p.value.link_href) ? p.value.link_href : ''))
</script>

<template>
  <!-- Full name -->
  <div v-if="field.type === 'full_name'" :id="id" class="grid gap-2" :class="p.show_title ? '@sm:grid-cols-[6rem_minmax(0,1fr)_minmax(0,1fr)]' : '@sm:grid-cols-2'">
    <UInput v-if="p.show_title" v-bind="control" :model-value="String(obj.title ?? '')" :placeholder="t('renderer.name.title')" autocomplete="honorific-prefix" :disabled="locked" class="w-full" @update:model-value="v => setPart('title', v)" />
    <UInput v-bind="control" :model-value="String(obj.first ?? '')" :placeholder="t('renderer.name.first')" autocomplete="given-name" :disabled="locked" class="w-full" @update:model-value="v => setPart('first', v)" />
    <UInput v-if="p.show_middle" v-bind="control" :model-value="String(obj.middle ?? '')" :placeholder="t('renderer.name.middle')" autocomplete="additional-name" :disabled="locked" class="w-full" @update:model-value="v => setPart('middle', v)" />
    <UInput v-bind="control" :model-value="String(obj.last ?? '')" :placeholder="t('renderer.name.last')" autocomplete="family-name" :disabled="locked" class="w-full" @update:model-value="v => setPart('last', v)" />
  </div>

  <!-- Consent -->
  <div v-else-if="field.type === 'consent'" :id="id" class="flex items-start gap-2.5">
    <UCheckbox :model-value="value === true" color="primary" :disabled="locked" :aria-label="field.label" @update:model-value="v => (value = v === true)" />
    <p class="text-sm text-default">
      {{ String(p.text || '') || t('renderer.consent.default') }}
      <a v-if="safeHref" :href="safeHref" target="_blank" rel="noopener noreferrer" class="font-medium text-highlighted underline underline-offset-2">
        {{ String(p.link_label || '') || t('renderer.consent.link') }}
      </a>
    </p>
  </div>

  <!-- Colour -->
  <div v-else-if="field.type === 'color'" :id="id" class="flex items-center gap-2">
    <UPopover :disabled="locked">
      <UButton color="neutral" variant="outline" square class="size-9 shrink-0 p-1" :disabled="locked" :aria-label="t('renderer.color.pick')">
        <span class="size-full rounded-sm border border-default" :style="{ background: hex || 'transparent' }" />
      </UButton>
      <template #content>
        <UColorPicker :model-value="hex || '#000000'" format="hex" class="p-2" @update:model-value="v => v && (value = v.toLowerCase())" />
      </template>
    </UPopover>
    <UInput v-bind="control" :model-value="typeof value === 'string' ? value : ''" placeholder="#1a2b3c" maxlength="7" :disabled="locked" class="w-36 font-mono" :aria-label="field.label" @update:model-value="v => (value = String(v).trim() || null)" />
  </div>

  <!-- Duration -->
  <div v-else-if="field.type === 'duration'" :id="id" class="flex items-center gap-2">
    <!-- Plain number inputs: they report every keystroke, so a fixed error clears while typing. -->
    <UInput
      v-bind="control"
      type="number"
      inputmode="numeric"
      :model-value="obj.hours == null ? '' : String(obj.hours)"
      min="0"
      max="9999"
      :disabled="locked"
      class="w-28"
      :aria-label="t('renderer.duration.hours')"
      @update:model-value="v => setPart('hours', v === '' ? undefined : Number(v))"
    />
    <span class="text-sm text-muted">{{ t('renderer.duration.h') }}</span>
    <UInput
      v-bind="control"
      type="number"
      inputmode="numeric"
      :model-value="obj.minutes == null ? '' : String(obj.minutes)"
      min="0"
      max="59"
      :disabled="locked"
      class="w-24"
      :aria-label="t('renderer.duration.minutes')"
      @update:model-value="v => setPart('minutes', v === '' ? undefined : Number(v))"
    />
    <span class="text-sm text-muted">{{ t('renderer.duration.m') }}</span>
  </div>

  <!-- Language / time zone / currency -->
  <USelectMenu
    v-else
    v-bind="control"
    :id="id"
    v-model="pick"
    :items="items"
    value-key="value"
    :placeholder="field.placeholder || t(`renderer.pick.${field.type}`)"
    :search-input="{ placeholder: t('common.search') }"
    :icon="field.type === 'language' ? 'i-lucide-languages' : field.type === 'timezone' ? 'i-lucide-clock-4' : 'i-lucide-coins'"
    :disabled="locked"
    virtualize
    class="w-full"
  />
</template>
