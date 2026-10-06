<!--
  Settings → Company (F14 M1): the names (shown and legal), about the organisation, registration,
  the support contact and the address, with a live card of where they appear (emails, receipts,
  public pages). Onboarding fills the same record.
-->
<script setup lang="ts">
import { COMPANY_SIZES, INDUSTRIES } from '#shared/types/onboarding'
import { companySchema } from '#shared/utils/settings/schemas'

definePageMeta({ breadcrumb: 'settings.nav.company' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.company') })
const form = useSettingsForm('company', { schema: companySchema })
const { draft, errorOf } = form
const countries = useCountryOptions()
const industries = computed(() => INDUSTRIES.map(value => ({ value, label: t(`onboarding.industry.${value}`) })))
const sizes = computed(() => COMPANY_SIZES.map(value => ({ value, label: t('onboarding.company.people', { range: value }) })))
const countryName = computed(() => countries.value.find(item => item.value === draft.value?.address.country)?.label ?? '')
const addressLines = computed(() => {
  const a = draft.value?.address
  if (!a) return []
  return [a.line1, a.line2, [a.postal_code, a.city].filter(Boolean).join(' '), a.region, countryName.value].filter(Boolean) as string[]
})
</script>

<template>
  <SettingsPage id="settings-company" :title="t('settings.nav.company')" :subtitle="t('settings.desc.company')" icon="i-lucide-building-2" :form="{ dirty: form.dirty.value, saving: form.saving.value, updated: form.updated.value }" @save="form.save" @discard="form.discard">
    <AppEmpty v-if="form.failed.value && !draft" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => form.reload() }]" />
    <div v-else-if="!draft" class="flex flex-col gap-6"><USkeleton v-for="n in 4" :key="n" class="h-32 rounded-lg" /></div>
    <div v-else class="grid gap-8 2xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div class="flex min-w-0 flex-col gap-6">
        <SettingsBlock :title="t('settings.company.names')" :description="t('settings.company.namesHint')" icon="i-lucide-signature">
          <div class="grid gap-4 sm:grid-cols-2">
            <UFormField :label="t('settings.company.displayName')" :description="t('settings.company.displayNameHint')" :error="errorOf('display_name')" required>
              <UInput v-model="draft.display_name" maxlength="80" class="w-full" />
            </UFormField>
            <UFormField :label="t('settings.company.legalName')" :description="t('settings.company.legalNameHint')" :error="errorOf('legal_name')" required>
              <UInput v-model="draft.legal_name" maxlength="160" class="w-full" />
            </UFormField>
          </div>
        </SettingsBlock>

        <SettingsBlock :title="t('settings.company.about')" :description="t('settings.company.aboutHint')" icon="i-lucide-info">
          <div class="grid gap-4 sm:grid-cols-2">
            <UFormField :label="t('onboarding.company.industry')">
              <USelectMenu :model-value="draft.industry ?? undefined" :items="industries" value-key="value" :placeholder="t('onboarding.choose')" class="w-full" @update:model-value="value => draft && (draft.industry = value ?? null)" />
            </UFormField>
            <UFormField :label="t('onboarding.company.size')">
              <USelect :model-value="draft.size ?? undefined" :items="sizes" :placeholder="t('onboarding.choose')" class="w-full" @update:model-value="value => draft && (draft.size = value ?? null)" />
            </UFormField>
          </div>
          <UFormField :label="t('onboarding.company.website')" :error="errorOf('website')">
            <SettingsText v-model="draft.website" type="url" placeholder="https://example.com" icon="i-lucide-globe" class="w-full" dir="ltr" />
          </UFormField>
        </SettingsBlock>

        <SettingsBlock :title="t('settings.company.registration')" :description="t('settings.company.registrationHint')" icon="i-lucide-landmark">
          <div class="grid gap-4 sm:grid-cols-2">
            <UFormField :label="t('settings.company.registrationNumber')" :error="errorOf('registration_number')">
              <SettingsText v-model="draft.registration_number" maxlength="60" class="w-full" dir="ltr" />
            </UFormField>
            <UFormField :label="t('settings.company.taxNumber')" :error="errorOf('tax_number')">
              <SettingsText v-model="draft.tax_number" maxlength="60" class="w-full" dir="ltr" />
            </UFormField>
          </div>
        </SettingsBlock>

        <SettingsBlock :title="t('settings.company.support')" :description="t('settings.company.supportHint')" icon="i-lucide-life-buoy">
          <div class="grid gap-4 sm:grid-cols-2">
            <UFormField :label="t('settings.company.supportEmail')" :error="errorOf('support_email')">
              <SettingsText v-model="draft.support_email" type="email" icon="i-lucide-mail" placeholder="help@example.com" class="w-full" dir="ltr" />
            </UFormField>
            <UFormField :label="t('settings.company.supportPhone')" :error="errorOf('support_phone')">
              <SettingsText v-model="draft.support_phone" type="tel" icon="i-lucide-phone" placeholder="+44 7700 900123" class="w-full" dir="ltr" />
            </UFormField>
          </div>
        </SettingsBlock>

        <SettingsBlock :title="t('settings.company.address')" :description="t('settings.company.addressHint')" icon="i-lucide-map-pin">
          <UFormField :label="t('settings.company.line1')" :error="errorOf('address.line1')">
            <SettingsText v-model="draft.address.line1" maxlength="160" class="w-full" />
          </UFormField>
          <UFormField :label="t('settings.company.line2')" :error="errorOf('address.line2')">
            <SettingsText v-model="draft.address.line2" maxlength="160" class="w-full" />
          </UFormField>
          <div class="grid gap-4 sm:grid-cols-2">
            <UFormField :label="t('settings.company.city')"><SettingsText v-model="draft.address.city" maxlength="100" class="w-full" /></UFormField>
            <UFormField :label="t('settings.company.region')"><SettingsText v-model="draft.address.region" maxlength="100" class="w-full" /></UFormField>
            <UFormField :label="t('settings.company.postalCode')"><SettingsText v-model="draft.address.postal_code" maxlength="20" class="w-full" dir="ltr" /></UFormField>
            <UFormField :label="t('onboarding.company.country')" :error="errorOf('address.country')">
              <USelectMenu :model-value="draft.address.country ?? undefined" :items="countries" value-key="value" :icon="countries.find(item => item.value === draft?.address.country)?.icon" :placeholder="t('onboarding.choose')" :search-input="{ placeholder: t('common.search') }" class="w-full" @update:model-value="(value: string | undefined) => draft && (draft.address.country = value ?? null)" />
            </UFormField>
          </div>
        </SettingsBlock>
      </div>

      <!-- Where it shows: a receipt-style footer, kept in view while editing -->
      <aside class="2xl:sticky 2xl:top-0 2xl:self-start">
        <div class="flex flex-col gap-3 rounded-xl border border-default bg-elevated/30 p-4">
          <span class="text-[11px] font-medium tracking-wide text-muted uppercase">{{ t('settings.company.previewTitle') }}</span>
          <div class="flex flex-col gap-3 rounded-lg border border-default bg-default p-4">
            <p class="text-sm text-muted">{{ t('settings.company.previewBody') }}</p>
            <USeparator />
            <div class="flex flex-col gap-0.5 text-xs text-muted">
              <span class="font-semibold text-highlighted">{{ draft.display_name || t('settings.company.displayName') }}</span>
              <span v-if="draft.legal_name && draft.legal_name !== draft.display_name">{{ draft.legal_name }}</span>
              <span v-for="line in addressLines" :key="line">{{ line }}</span>
              <span v-if="draft.registration_number" dir="ltr">{{ t('settings.company.registrationShort', { n: draft.registration_number }) }}</span>
              <span v-if="draft.support_email || draft.support_phone" class="pt-1" dir="ltr">{{ [draft.support_email, draft.support_phone].filter(Boolean).join(' · ') }}</span>
            </div>
          </div>
          <p class="text-xs text-muted">{{ t('settings.company.previewHint') }}</p>
        </div>
      </aside>
    </div>
  </SettingsPage>
</template>
