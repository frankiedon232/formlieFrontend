<!-- Step 3 — workspace language, timezone, currency, date / number format, first day of the week. -->
<script setup lang="ts">
import {
  DATE_FORMATS,
  NUMBER_FORMATS,
  type OnboardingLocalisation,
  type WeekStart,
} from '#shared/types/onboarding'

const localisation = defineModel<OnboardingLocalisation>({ required: true })
const emit = defineEmits<{ submit: [] }>()
const { t } = useI18n()
const { locales } = useAppLocale()
const currencies = useCurrencyOptions()
const timezones = useTimezoneOptions()

const today = new Date()
const languages = computed(() =>
  locales.map(item => ({ value: item.code, label: `${item.name} · ${item.englishName}`, icon: item.flag })),
)
const dateFormats = computed(() =>
  DATE_FORMATS.map(value => ({
    value,
    label: formatDatePattern(today, value, localisation.value.timezone),
    description: value,
  })),
)
const numberFormats = computed(() =>
  NUMBER_FORMATS.map(value => ({ value, label: formatNumberPattern(1234567.89, value) })),
)
const weekStarts = computed(() =>
  (['monday', 'sunday', 'saturday'] as WeekStart[]).map(value => ({
    value,
    label: t(`onboarding.localisation.week.${value}`),
  })),
)
</script>

<template>
  <UForm id="onboarding-step" :state="localisation" class="flex flex-col gap-5" @submit="emit('submit')">
    <div class="grid gap-5 sm:grid-cols-2">
      <UFormField
        name="language"
        :label="t('onboarding.localisation.language')"
        :description="t('onboarding.localisation.languageHint')"
      >
        <USelectMenu
          v-model="localisation.language"
          :items="languages"
          value-key="value"
          :icon="languages.find(item => item.value === localisation.language)?.icon"
          :search-input="{ placeholder: t('common.search') }"
          class="w-full"
          size="lg"
        />
      </UFormField>
      <UFormField
        name="currency"
        :label="t('onboarding.localisation.currency')"
        :description="t('onboarding.localisation.currencyHint')"
      >
        <USelectMenu
          v-model="localisation.currency"
          :items="currencies"
          value-key="value"
          :search-input="{ placeholder: t('common.search') }"
          class="w-full"
          size="lg"
        />
      </UFormField>
    </div>

    <UFormField
      name="timezone"
      :label="t('onboarding.localisation.timezone')"
      :description="t('onboarding.localisation.timezoneHint')"
    >
      <USelectMenu
        v-model="localisation.timezone"
        :items="timezones"
        value-key="value"
        icon="i-lucide-clock"
        :search-input="{ placeholder: t('common.search') }"
        virtualize
        class="w-full"
        size="lg"
      />
    </UFormField>

    <UFormField name="date_format" :label="t('onboarding.localisation.dateFormat')">
      <URadioGroup
        v-model="localisation.date_format"
        :items="dateFormats"
        variant="card"
        color="neutral"
        :ui="{ fieldset: 'grid grid-cols-2 gap-2 sm:grid-cols-4', label: 'tabular-nums' }"
      />
    </UFormField>

    <div class="grid gap-5 sm:grid-cols-2">
      <UFormField name="number_format" :label="t('onboarding.localisation.numberFormat')">
        <URadioGroup
          v-model="localisation.number_format"
          :items="numberFormats"
          variant="card"
          color="neutral"
          :ui="{ fieldset: 'grid grid-cols-2 gap-2', label: 'tabular-nums' }"
        />
      </UFormField>
      <UFormField name="week_start" :label="t('onboarding.localisation.weekStart')">
        <URadioGroup
          v-model="localisation.week_start"
          :items="weekStarts"
          variant="card"
          color="neutral"
          :ui="{ fieldset: 'grid gap-2' }"
        />
      </UFormField>
    </div>
  </UForm>
</template>
