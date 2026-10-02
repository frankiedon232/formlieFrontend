<!-- Step 1 — company details. Submitted by the wizard footer (form="onboarding-step"). -->
<script setup lang="ts">
import { z } from 'zod'
import { COMPANY_SIZES, INDUSTRIES, type OnboardingCompany } from '#shared/types/onboarding'

const company = defineModel<OnboardingCompany>({ required: true })
const emit = defineEmits<{ submit: [] }>()
const { t } = useI18n()
const countries = useCountryOptions()

const schema = z.object({
  name: z.string().trim().min(2, t('onboarding.company.nameRequired')).max(120),
  website: z
    .string()
    .trim()
    .max(200)
    .refine(value => !value || z.url().safeParse(value).success, t('onboarding.company.websiteInvalid'))
    .nullable(),
})

const industries = computed(() =>
  INDUSTRIES.map(value => ({ value, label: t(`onboarding.industry.${value}`) })),
)
const sizes = computed(() =>
  COMPANY_SIZES.map(value => ({ value, label: t('onboarding.company.people', { range: value }) })),
)

/** "example.com" → "https://example.com" so people don't have to type the scheme. */
function normaliseWebsite() {
  const value = company.value.website?.trim() ?? ''
  company.value.website = !value ? null : /^https?:\/\//i.test(value) ? value : `https://${value}`
}
</script>

<template>
  <UForm
    id="onboarding-step"
    :schema="schema"
    :state="company"
    class="flex flex-col gap-5"
    @submit="emit('submit')"
  >
    <UFormField
      name="name"
      :label="t('onboarding.company.name')"
      :hint="t('onboarding.company.nameHint')"
      required
    >
      <UInput v-model="company.name" autocomplete="organization" class="w-full" size="lg" autofocus />
    </UFormField>

    <div class="grid gap-5 sm:grid-cols-2">
      <UFormField name="industry" :label="t('onboarding.company.industry')">
        <USelectMenu
          :model-value="company.industry ?? undefined"
          :items="industries"
          value-key="value"
          :placeholder="t('onboarding.choose')"
          :search-input="{ placeholder: t('common.search') }"
          class="w-full"
          size="lg"
          @update:model-value="value => (company.industry = value ?? null)"
        />
      </UFormField>
      <UFormField name="country" :label="t('onboarding.company.country')">
        <USelectMenu
          :model-value="company.country ?? undefined"
          :items="countries"
          value-key="value"
          :placeholder="t('onboarding.choose')"
          :search-input="{ placeholder: t('common.search') }"
          :icon="company.country ? `i-circle-flags-${company.country.toLowerCase()}` : 'i-lucide-globe'"
          class="w-full"
          size="lg"
          @update:model-value="value => (company.country = value ?? null)"
        />
      </UFormField>
    </div>

    <UFormField name="size" :label="t('onboarding.company.size')">
      <URadioGroup
        :model-value="company.size ?? undefined"
        :items="sizes"
        variant="card"
        orientation="horizontal"
        color="neutral"
        :ui="{ fieldset: 'grid grid-cols-2 gap-2 sm:grid-cols-5', item: 'justify-center' }"
        @update:model-value="value => (company.size = value ?? null)"
      />
    </UFormField>

    <UFormField name="website" :label="t('onboarding.company.website')" :hint="t('onboarding.optional')">
      <UInput
        :model-value="company.website ?? ''"
        type="url"
        inputmode="url"
        autocomplete="url"
        placeholder="https://example.com"
        icon="i-lucide-link"
        class="w-full"
        size="lg"
        @update:model-value="value => (company.website = String(value) || null)"
        @blur="normaliseWebsite"
      />
    </UFormField>
  </UForm>
</template>
