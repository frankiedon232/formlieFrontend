<!-- Address (street, city, region, postal code, country — international) and country picker. -->
<script setup lang="ts">
import { isLocked, type FormField } from '#shared/utils/forms/build'
import { requiredAddressParts, type AddressPart } from '#shared/utils/forms/validate'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live'; errorParts?: string[] }>()
const value = defineModel<unknown>()
const { t } = useI18n()
// Size and style follow the form theme (F8); plain defaults elsewhere.
const control = useControlStyle()
const countries = useCountryOptions()

type AddressValue = {
  line1?: string
  line2?: string
  city?: string
  region?: string
  postal_code?: string
  country?: string
}
const address = computed(() =>
  value.value && typeof value.value === 'object' ? (value.value as AddressValue) : {},
)
const set = (key: keyof AddressValue, next: unknown) =>
  (value.value = { ...address.value, [key]: next == null ? '' : String(next) })
const country = computed({
  get: () => (typeof value.value === 'string' ? value.value : undefined),
  set: next => (value.value = next),
})
// Read-only and disabled both block changes here (Nuxt UI choice controls have no read-only state).
const readonly = computed(() => isLocked(props.field))
// Missing parts after a failed submit are highlighted; parts that aren't asked for say "(optional)".
const bad = (part: string) => !!props.errorParts?.includes(part)
const state = (part: string) => (bad(part) ? { color: 'error' as const, highlight: true, 'aria-invalid': true } : {})
const asked = computed(() => requiredAddressParts(props.field))
const optional = (part: AddressPart, label: string) =>
  asked.value.includes(part) ? label : t('renderer.address.optional', { part: label })
const flag = (code?: string) => (code ? `i-circle-flags-${code.toLowerCase()}` : 'i-lucide-globe')
</script>

<template>
  <USelectMenu
    v-if="field.type === 'country'"
    v-bind="control"
    :id="id"
    v-model="country"
    :items="countries"
    value-key="value"
    :icon="flag(country)"
    :placeholder="field.placeholder || t('renderer.chooseCountry')"
    :search-input="{ placeholder: t('common.search') }"
    :disabled="readonly"
    class="w-full"
  />
  <div v-else :id="id" class="grid gap-2 sm:grid-cols-2">
    <UInput
      v-bind="{ ...control, ...state('line1') }"
      :model-value="address.line1 ?? ''"
      :placeholder="t('renderer.address.line1')"
      autocomplete="address-line1"
      :readonly="readonly"
      class="w-full sm:col-span-2"
      @update:model-value="v => set('line1', v)"
    />
    <UInput
      v-bind="control"
      :model-value="address.line2 ?? ''"
      :placeholder="t('renderer.address.line2')"
      autocomplete="address-line2"
      :readonly="readonly"
      class="w-full sm:col-span-2"
      @update:model-value="v => set('line2', v)"
    />
    <UInput
      v-bind="{ ...control, ...state('city') }"
      :model-value="address.city ?? ''"
      :placeholder="t('renderer.address.city')"
      autocomplete="address-level2"
      :readonly="readonly"
      class="w-full"
      @update:model-value="v => set('city', v)"
    />
    <UInput
      v-bind="{ ...control, ...state('region') }"
      :model-value="address.region ?? ''"
      :placeholder="optional('region', t('renderer.address.region'))"
      autocomplete="address-level1"
      :readonly="readonly"
      class="w-full"
      @update:model-value="v => set('region', v)"
    />
    <UInput
      v-bind="{ ...control, ...state('postal_code') }"
      :model-value="address.postal_code ?? ''"
      :placeholder="optional('postal_code', t('renderer.address.postalCode'))"
      autocomplete="postal-code"
      :readonly="readonly"
      class="w-full"
      @update:model-value="v => set('postal_code', v)"
    />
    <USelectMenu
      v-bind="{ ...control, ...state('country') }"
      :model-value="address.country"
      :items="countries"
      value-key="value"
      :icon="flag(address.country)"
      :placeholder="t('renderer.address.country')"
      :search-input="{ placeholder: t('common.search') }"
      :disabled="readonly"
      class="w-full"
      @update:model-value="v => set('country', v)"
    />
  </div>
</template>
