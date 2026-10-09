<!--
  My profile → Language and region (F16 M5): the app's language for this person, their time zone and
  short date format. "The workspace's" keeps Settings → Language and region; dates everywhere follow
  their choice once saved.
-->
<script setup lang="ts">
import { DATE_FORMATS, type DateFormat } from '#shared/types/onboarding'
import type { MyProfile } from '#shared/types/profile'

const props = defineProps<{ profile: MyProfile; saving: string | null }>()
const emit = defineEmits<{ save: [part: string, values: Partial<MyProfile>] }>()
const { t } = useI18n()
const { locales, changeLocale } = useAppLocale()

const WORKSPACE = 'workspace'
const state = reactive({ language: props.profile.language ?? WORKSPACE, time_zone: props.profile.time_zone ?? WORKSPACE, date_format: (props.profile.date_format ?? WORKSPACE) as string })
const now = new Date()
const languages = computed(() => [{ value: WORKSPACE, label: t('profile.prefs.workspace') }, ...locales.map(item => ({ value: item.code, label: item.name, description: item.englishName, icon: item.flag }))])
const zones = computed(() => [{ value: WORKSPACE, label: t('profile.prefs.workspace') }, ...timezoneOptions(now).map(item => ({ value: item.value, label: item.label }))])
const formats = computed(() => [{ value: WORKSPACE, label: t('profile.prefs.workspace') }, ...DATE_FORMATS.map(value => ({ value, label: formatDatePattern(now, value), description: value }))])
const pick = (value: string) => (value === WORKSPACE ? null : value)
const dirty = computed(() => pick(state.language) !== props.profile.language || pick(state.time_zone) !== props.profile.time_zone || pick(state.date_format) !== props.profile.date_format)

function save() {
  const language = pick(state.language)
  emit('save', 'prefs', { language, time_zone: pick(state.time_zone), date_format: pick(state.date_format) as DateFormat | null })
  if (language) void changeLocale(language)
}
</script>

<template>
  <SettingsBlock :title="t('profile.prefs.title')" :description="t('profile.prefs.desc')" icon="i-lucide-languages">
    <div class="grid gap-4 sm:grid-cols-3">
      <UFormField :label="t('profile.prefs.language')">
        <USelectMenu v-model="state.language" :items="languages" value-key="value" class="w-full" />
      </UFormField>
      <UFormField :label="t('profile.prefs.timeZone')">
        <USelectMenu v-model="state.time_zone" :items="zones" value-key="value" :virtualize="true" class="w-full" />
      </UFormField>
      <UFormField :label="t('profile.prefs.dateFormat')">
        <USelect v-model="state.date_format" :items="formats" value-key="value" class="w-full" />
      </UFormField>
    </div>
    <div><UButton :label="t('common.save')" icon="i-lucide-check" color="neutral" :loading="saving === 'prefs'" :disabled="!dirty" @click="save" /></div>
  </SettingsBlock>
</template>
