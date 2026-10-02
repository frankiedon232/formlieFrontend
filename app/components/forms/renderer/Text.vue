<!-- Text-like fields: short / long / rich text, email, phone, URL, number, currency, calculated, hidden. -->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()
const { t } = useI18n()
const { current } = useAppLocale()

const text = computed({
  get: () => (value.value == null ? '' : String(value.value)),
  set: next => (value.value = next),
})
const props_ = computed(() => (props.field.props ?? {}) as Record<string, unknown>)
const INPUT_TYPES: Record<string, string> = {
  email: 'email',
  phone: 'tel',
  url: 'url',
  number: 'number',
  currency: 'number',
}
const MODES: Record<string, 'email' | 'tel' | 'url' | 'decimal'> = {
  email: 'email',
  phone: 'tel',
  url: 'url',
  number: 'decimal',
  currency: 'decimal',
}
const ICONS: Record<string, string> = {
  email: 'i-lucide-mail',
  phone: 'i-lucide-phone',
  url: 'i-lucide-link',
}

const currencySymbol = computed(() => {
  const code = String(props_.value.currency ?? 'USD')
  try {
    return (
      new Intl.NumberFormat(current.value.language, {
        style: 'currency',
        currency: code,
        currencyDisplay: 'narrowSymbol',
      })
        .formatToParts(0)
        .find(part => part.type === 'currency')?.value ?? code
    )
  } catch {
    return code
  }
})
const readonly = computed(() => props.mode === 'builder' || props.field.type === 'calculated')
</script>

<template>
  <div
    v-if="field.type === 'hidden'"
    class="flex items-center gap-2 rounded-md border border-dashed border-default px-3 py-2 text-xs text-muted"
  >
    <UIcon name="i-lucide-eye-off" class="size-3.5" />
    {{ t('renderer.hidden', { key: field.key }) }}
  </div>
  <UTextarea
    v-else-if="field.type === 'long_text' || field.type === 'rich_text'"
    :id="id"
    v-model="text"
    :rows="Number(props_.rows ?? 4)"
    :placeholder="field.placeholder"
    :required="field.required"
    :maxlength="(field.validation?.max_length as number | undefined) ?? undefined"
    :readonly="readonly"
    autoresize
    class="w-full"
  />
  <UInput
    v-else
    :id="id"
    v-model="text"
    :type="INPUT_TYPES[field.type] ?? 'text'"
    :inputmode="MODES[field.type]"
    :placeholder="field.type === 'calculated' ? t('renderer.calculated') : field.placeholder"
    :required="field.required"
    :readonly="readonly"
    :icon="field.type === 'calculated' ? 'i-lucide-calculator' : ICONS[field.type]"
    :autocomplete="field.type === 'email' ? 'email' : field.type === 'phone' ? 'tel' : undefined"
    class="w-full"
  >
    <template v-if="field.type === 'currency'" #leading>
      <span class="text-sm text-muted">{{ currencySymbol }}</span>
    </template>
  </UInput>
</template>
