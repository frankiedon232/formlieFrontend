<!-- Text-like fields: short / long text, IP address, domain, MAC address, IBAN, BIC, percentage, email, phone, URL, number, currency, calculated, hidden. -->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'
import { maskIp, maskMac, type IpVersion } from '#shared/utils/forms/masks'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()
const { t } = useI18n()
// Size and style follow the form theme (F8); plain defaults elsewhere.
const control = useControlStyle()
const { current } = useAppLocale()

const props_ = computed(() => (props.field.props ?? {}) as Record<string, unknown>)
/** Typing masks for technical fields (shared/utils/forms/masks.ts); the validator still decides. */
function masked(next: string) {
  if (props.field.type === 'ip_address') return maskIp(next, (props_.value.ip_version as IpVersion | undefined) ?? 'any')
  if (props.field.type === 'mac_address') return maskMac(next)
  return next
}
const input = useTemplateRef<{ inputRef?: HTMLInputElement | null }>('input')
const text = computed({
  get: () => (value.value == null ? '' : String(value.value)),
  set: next => {
    const raw = String(next ?? '')
    const out = masked(raw)
    value.value = out
    // A stripped character leaves the model unchanged, so put the cleaned text back in the box.
    if (out !== raw)
      nextTick(() => {
        const el = input.value?.inputRef
        if (el && el.value !== out) el.value = out
      })
  },
})
const INPUT_TYPES: Record<string, string> = {
  email: 'email',
  phone: 'tel',
  url: 'url',
  number: 'number',
  currency: 'number',
  percentage: 'number',
}
const MODES: Record<string, 'email' | 'tel' | 'url' | 'decimal'> = {
  email: 'email',
  phone: 'tel',
  url: 'url',
  number: 'decimal',
  currency: 'decimal',
  percentage: 'decimal',
}
/** The box icon (Form settings → Field icons; every type its own, owner 2026-10-06). */
const icon = useFieldIcon(() => props.field)
/** Codes are written in capitals and without spell-checking (IBAN, BIC, MAC). */
const CODE_TYPES = ['iban', 'bic', 'mac_address', 'ip_address', 'domain']

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
const readonly = computed(() => !!props.field.readonly || props.field.type === 'calculated')
const disabled = computed(() => !!props.field.disabled)
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
    v-else-if="field.type === 'long_text'"
    v-bind="control"
    :id="id"
    v-model="text"
    :rows="Number(props_.rows ?? 4)"
    :placeholder="field.placeholder"
    :required="field.required"
    :maxlength="(field.validation?.max_length as number | undefined) ?? undefined"
    :readonly="readonly"
    :disabled="disabled"
    autoresize
    :icon="icon"
    class="w-full"
  />
  <UInput
    v-else
    v-bind="control"
    :id="id"
    ref="input"
    v-model="text"
    :type="INPUT_TYPES[field.type] ?? 'text'"
    :inputmode="MODES[field.type]"
    :placeholder="field.type === 'calculated' ? t('renderer.calculated') : field.placeholder"
    :required="field.required"
    :readonly="readonly"
    :disabled="disabled"
    :icon="icon"
    :autocomplete="field.type === 'email' ? 'email' : field.type === 'phone' ? 'tel' : CODE_TYPES.includes(field.type) ? 'off' : undefined"
    :spellcheck="CODE_TYPES.includes(field.type) ? false : undefined"
    :autocapitalize="['iban', 'bic', 'mac_address'].includes(field.type) ? 'characters' : CODE_TYPES.includes(field.type) ? 'none' : undefined"
    :class="['iban', 'bic', 'mac_address'].includes(field.type) ? 'font-mono uppercase' : ''"
    class="w-full"
  >
    <template v-if="field.type === 'percentage'" #trailing>
      <span class="text-sm text-muted">%</span>
    </template>
    <template v-if="field.type === 'currency'" #leading>
      <span class="text-sm text-muted">{{ currencySymbol }}</span>
    </template>
  </UInput>
</template>
