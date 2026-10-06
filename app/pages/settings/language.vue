<!--
  Settings → Language and region (F14 M1): the workspace language, time zone and currency, the date
  and number formats and the first day of the week, and the languages forms may use; a live card
  shows how dates, times, numbers and money will look. Saving applies it across the portal at once.
-->
<script setup lang="ts">
import { DATE_FORMATS, NUMBER_FORMATS, type WeekStart } from '#shared/types/onboarding'
import { APP_LOCALES } from '#shared/utils/i18n/locales'
import { localisationSchema } from '#shared/utils/settings/schemas'

definePageMeta({ breadcrumb: 'settings.nav.language' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.language') })
const form = useSettingsForm('localisation', { schema: localisationSchema })
const { draft, errorOf } = form
const workspace = useWorkspaceLocale()
const store = useWorkspaceSettings()
watch(() => store.settings.value?.localisation, value => value && workspace.set(value))

const currencies = useCurrencyOptions()
const timezones = useTimezoneOptions()
const now = useNow()
const languages = computed(() => APP_LOCALES.map(item => ({ value: item.code, label: `${item.name} · ${item.englishName}`, icon: item.flag })))
const dateFormats = computed(() => DATE_FORMATS.map(value => ({ value, label: formatDatePattern(now.value, value, draft.value?.timezone), description: value })))
const numberFormats = computed(() => NUMBER_FORMATS.map(value => ({ value, label: formatNumberPattern(1234567.89, value) })))
const weekStarts = computed(() => (['monday', 'sunday', 'saturday'] as WeekStart[]).map(value => ({ value, label: t(`onboarding.localisation.week.${value}`) })))

// Languages for forms: every app language, chosen with checkboxes, at least one
const allLanguages = computed(() => draft.value?.form_languages.length === APP_LOCALES.length)
const toggleLanguage = (code: string, on: boolean) => draft.value && (draft.value.form_languages = on ? APP_LOCALES.map(item => item.code).filter(item => item === code || draft.value!.form_languages.includes(item)) : draft.value.form_languages.filter(item => item !== code))
const setAll = (on: boolean) => draft.value && (draft.value.form_languages = on ? APP_LOCALES.map(item => item.code) : [draft.value.language])

// The live card, drawn from the draft
const sample = computed(() => {
  const d = draft.value
  if (!d) return null
  const signs = NUMBER_SIGNS[d.number_format]
  const swap = (text: Intl.NumberFormatPart[]) => text.map(part => (part.type === 'group' ? signs.group : part.type === 'decimal' ? signs.decimal : part.value)).join('')
  const lang = APP_LOCALES.find(item => item.code === d.language)?.language ?? 'en'
  const days = Array.from({ length: 7 }, (_, i) => {
    const start = { monday: 1, sunday: 0, saturday: 6 }[d.week_start]
    return new Intl.DateTimeFormat(lang, { weekday: 'short' }).format(new Date(Date.UTC(2026, 0, 4 + ((start + i) % 7))))
  })
  return {
    short: formatDatePattern(now.value, d.date_format, d.timezone),
    long: new Intl.DateTimeFormat(lang, { dateStyle: 'full', timeZone: d.timezone }).format(now.value),
    time: new Intl.DateTimeFormat(lang, { timeStyle: 'short', timeZone: d.timezone }).format(now.value),
    number: swap(new Intl.NumberFormat(lang, { maximumFractionDigits: 2 }).formatToParts(1234567.89)),
    money: swap(new Intl.NumberFormat(lang, { style: 'currency', currency: d.currency }).formatToParts(1249.5)),
    days,
  }
})
</script>

<template>
  <SettingsPage id="settings-language" :title="t('settings.nav.language')" :subtitle="t('settings.desc.language')" icon="i-lucide-languages" :form="{ dirty: form.dirty.value, saving: form.saving.value, updated: form.updated.value }" @save="form.save" @discard="form.discard">
    <AppEmpty v-if="form.failed.value && !draft" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => form.reload() }]" />
    <div v-else-if="!draft" class="flex flex-col gap-6"><USkeleton v-for="n in 3" :key="n" class="h-36 rounded-lg" /></div>
    <div v-else class="grid gap-8 2xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div class="flex min-w-0 flex-col gap-6">
        <SettingsBlock :title="t('settings.language.language')" :description="t('onboarding.localisation.languageHint')" icon="i-lucide-languages">
          <UFormField :label="t('onboarding.localisation.language')">
            <USelectMenu v-model="draft.language" :items="languages" value-key="value" :icon="languages.find(item => item.value === draft?.language)?.icon" :search-input="{ placeholder: t('common.search') }" class="w-full sm:max-w-sm" />
          </UFormField>
        </SettingsBlock>

        <SettingsBlock :title="t('settings.language.region')" :description="t('settings.language.regionHint')" icon="i-lucide-globe">
          <div class="grid gap-4 sm:grid-cols-2">
            <UFormField :label="t('onboarding.localisation.timezone')" :description="t('onboarding.localisation.timezoneHint')" :error="errorOf('timezone')">
              <USelectMenu v-model="draft.timezone" :items="timezones" value-key="value" :search-input="{ placeholder: t('common.search') }" class="w-full" />
            </UFormField>
            <UFormField :label="t('onboarding.localisation.currency')" :description="t('onboarding.localisation.currencyHint')" :error="errorOf('currency')">
              <USelectMenu v-model="draft.currency" :items="currencies" value-key="value" :search-input="{ placeholder: t('common.search') }" class="w-full" />
            </UFormField>
          </div>
        </SettingsBlock>

        <SettingsBlock :title="t('settings.language.formats')" :description="t('settings.language.formatsHint')" icon="i-lucide-calendar-cog">
          <div class="grid gap-4 sm:grid-cols-3">
            <UFormField :label="t('onboarding.localisation.dateFormat')">
              <USelect v-model="draft.date_format" :items="dateFormats" class="w-full" />
            </UFormField>
            <UFormField :label="t('onboarding.localisation.numberFormat')">
              <USelect v-model="draft.number_format" :items="numberFormats" class="w-full" :ui="{ base: 'tabular-nums' }" />
            </UFormField>
            <UFormField :label="t('onboarding.localisation.weekStart')">
              <USelect v-model="draft.week_start" :items="weekStarts" class="w-full" />
            </UFormField>
          </div>
        </SettingsBlock>

        <SettingsBlock :title="t('settings.language.forms')" :description="t('settings.language.formsHint')" icon="i-lucide-file-text">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="text-xs text-muted">{{ t('settings.language.formsCount', { n: draft.form_languages.length, total: APP_LOCALES.length }) }}</span>
            <UButton :label="allLanguages ? t('settings.language.onlyMain') : t('settings.language.all')" color="neutral" variant="link" size="xs" @click="setAll(!allLanguages)" />
          </div>
          <div class="grid gap-x-4 gap-y-2 rounded-lg border border-default p-3 sm:grid-cols-2 lg:grid-cols-3">
            <UCheckbox v-for="item in APP_LOCALES" :key="item.code" :model-value="draft.form_languages.includes(item.code)" color="neutral" @update:model-value="value => toggleLanguage(item.code, !!value)">
              <template #label><span class="inline-flex items-center gap-1.5"><UIcon :name="item.flag" class="size-4 shrink-0" />{{ item.name }}</span></template>
            </UCheckbox>
          </div>
          <p v-if="errorOf('form_languages')" class="text-xs text-error">{{ errorOf('form_languages') }}</p>
        </SettingsBlock>
      </div>

      <aside class="2xl:sticky 2xl:top-0 2xl:self-start">
        <div v-if="sample" class="flex flex-col gap-3 rounded-xl border border-default bg-elevated/30 p-4">
          <span class="text-[11px] font-medium tracking-wide text-muted uppercase">{{ t('settings.language.previewTitle') }}</span>
          <div class="flex flex-col divide-y divide-default rounded-lg border border-default bg-default text-sm">
            <div v-for="row in [{ k: 'short', v: sample.short }, { k: 'long', v: sample.long }, { k: 'time', v: sample.time }, { k: 'number', v: sample.number }, { k: 'money', v: sample.money }]" :key="row.k" class="flex items-baseline justify-between gap-3 px-3 py-2">
              <span class="text-xs text-muted">{{ t(`settings.language.sample.${row.k}`) }}</span>
              <span class="truncate font-medium text-highlighted tabular-nums">{{ row.v }}</span>
            </div>
          </div>
          <div class="grid grid-cols-7 gap-1 text-center text-[10px] text-muted">
            <span v-for="(day, i) in sample.days" :key="day" class="rounded py-1" :class="i === 0 ? 'bg-inverted font-semibold text-inverted' : 'bg-elevated'">{{ day }}</span>
          </div>
          <p class="text-xs text-muted">{{ t('settings.language.previewHint') }}</p>
        </div>
      </aside>
    </div>
  </SettingsPage>
</template>
