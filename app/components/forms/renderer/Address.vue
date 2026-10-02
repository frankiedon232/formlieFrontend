<!-- Address (street, city, region, postal code, country — international) and country picker. -->
<script setup lang="ts">
import { isLocked, type FormField } from '#shared/utils/forms/build'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()
const { t } = useI18n()
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
const flag = (code?: string) => (code ? `i-circle-flags-${code.toLowerCase()}` : 'i-lucide-globe')
</script>

<template>
  <USelectMenu
    v-if="field.type === 'country'"
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
      :model-value="address.line1 ?? ''"
      :placeholder="t('renderer.address.line1')"
      autocomplete="address-line1"
      :readonly="readonly"
      class="w-full sm:col-span-2"
      @update:model-value="v => set('line1', v)"
    />
    <UInput
      :model-value="address.line2 ?? ''"
      :placeholder="t('renderer.address.line2')"
      autocomplete="address-line2"
      :readonly="readonly"
      class="w-full sm:col-span-2"
      @update:model-value="v => set('line2', v)"
    />
    <UInput
      :model-value="address.city ?? ''"
      :placeholder="t('renderer.address.city')"
      autocomplete="address-level2"
      :readonly="readonly"
      class="w-full"
      @update:model-value="v => set('city', v)"
    />
    <UInput
      :model-value="address.region ?? ''"
      :placeholder="t('renderer.address.region')"
      autocomplete="address-level1"
      :readonly="readonly"
      class="w-full"
      @update:model-value="v => set('region', v)"
    />
    <UInput
      :model-value="address.postal_code ?? ''"
      :placeholder="t('renderer.address.postalCode')"
      autocomplete="postal-code"
      :readonly="readonly"
      class="w-full"
      @update:model-value="v => set('postal_code', v)"
    />
    <USelectMenu
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
