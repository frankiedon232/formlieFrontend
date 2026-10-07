<!--
  Settings → Form defaults (F14 M5): what every new blank or template form starts with: progress bar,
  save and resume, field icons, label position, a theme, the thank-you text, team members who get new
  responses by email, and the websites allowed to embed it. Existing forms keep their own settings;
  everything can still be changed per form.
-->
<script setup lang="ts">
import type { SavedTheme } from '#shared/types/forms'
import { formDefaultsSchema, isEmbedDomain } from '#shared/utils/settings/schemas'

definePageMeta({ breadcrumb: 'settings.nav.formDefaults' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.formDefaults') })
const api = useApi()
const form = useSettingsForm('form_defaults', { schema: formDefaultsSchema })
const { draft } = form

// Themes to start from, and people for response emails
const themes = ref<SavedTheme[]>([])
const people = ref<{ value: string; label: string; description: string }[]>([])
onMounted(async () => {
  const [themeList, directory] = await Promise.allSettled([api.list<SavedTheme>('/themes', { per_page: 100 }, { background: true }), api.get<{ users: { id: string; name: string; detail: string }[] }>('/directory', undefined, { background: true })])
  if (themeList.status === 'fulfilled') themes.value = themeList.value.data
  if (directory.status === 'fulfilled') people.value = directory.value.data.users.map(user => ({ value: user.id, label: user.name, description: user.detail }))
})
const NONE = '__workspace'
const themeName = (theme: SavedTheme) => (theme.name_key ? t(theme.name_key) : theme.name)
const themeItems = computed(() => [{ value: NONE, label: t('settings.formDefaults.workspaceLook'), icon: 'i-lucide-building-2' }, ...themes.value.map(theme => ({ value: theme.id, label: themeName(theme), icon: theme.source === 'system' ? 'i-lucide-sparkles' : 'i-lucide-swatch-book' }))])
const themeId = computed({ get: () => draft.value?.theme_id ?? NONE, set: value => draft.value && (draft.value.theme_id = value === NONE ? null : value) })
// A picture of the chosen theme (owner, 2026-10-07: people shouldn't choose blind); the workspace look without one
const tenant = useTenant()
const chosenTheme = computed(() => themes.value.find(theme => theme.id === draft.value?.theme_id) ?? null)
const thumbTokens = computed(() => (chosenTheme.value?.tokens ?? defaultTheme({ logo_url: tenant.profile.value?.logo_url ?? null, primary: tenant.profile.value?.colors.primary ?? null })) as unknown as Record<string, unknown>)
const thumbLabels = computed(() => [t('themes.previewName'), t('themes.previewEmail'), t('themes.previewMessage')])
const missingTheme = computed(() => !!draft.value?.theme_id && themes.value.length > 0 && !themes.value.some(theme => theme.id === draft.value?.theme_id))

const positions = computed(() => [
  { value: 'top', label: t('settings.formDefaults.labelTop'), icon: 'i-lucide-panel-top' },
  { value: 'left', label: t('settings.formDefaults.labelLeft'), icon: 'i-lucide-panel-left' },
])
const SWITCHES = ['progress_bar', 'save_resume', 'field_icons'] as const

const domains = computed({
  get: () => draft.value?.embed_domains ?? [],
  set: list => draft.value && (draft.value.embed_domains = [...new Set(list.map(item => item.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/\/.*$/, '')).filter(Boolean))]),
})
const badDomains = computed(() => domains.value.filter(item => !isEmbedDomain(item)))
</script>

<template>
  <SettingsPage id="settings-form-defaults" :title="t('settings.nav.formDefaults')" :subtitle="t('settings.desc.formDefaults')" icon="i-lucide-file-cog" :form="{ dirty: form.dirty.value, saving: form.saving.value, updated: form.updated.value }" @save="form.save" @discard="form.discard">
    <AppEmpty v-if="form.failed.value && !draft" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => form.reload() }]" />
    <div v-else-if="!draft" class="flex flex-col gap-6"><USkeleton v-for="n in 3" :key="n" class="h-36 rounded-lg" /></div>
    <div v-else class="flex flex-col gap-6">
      <UAlert color="neutral" variant="subtle" icon="i-lucide-info" :description="t('settings.formDefaults.note')" />

      <SettingsBlock :title="t('settings.formDefaults.experience')" :description="t('settings.formDefaults.experienceHint')" icon="i-lucide-sliders-horizontal">
        <div class="flex flex-col divide-y divide-default rounded-lg border border-default">
          <div v-for="key in SWITCHES" :key="key" class="flex items-center gap-3 px-3 py-2.5">
            <span class="flex min-w-0 flex-1 flex-col"><span class="text-sm text-highlighted">{{ t(`settings.formDefaults.${key}`) }}</span><span class="text-xs text-muted">{{ t(`settings.formDefaults.${key}Hint`) }}</span></span>
            <USwitch v-model="draft.settings[key]" color="neutral" :aria-label="t(`settings.formDefaults.${key}`)" />
          </div>
        </div>
        <UFormField :label="t('settings.formDefaults.labels')">
          <UTabs v-model="draft.settings.label_position" :items="positions" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="w-fit" />
        </UFormField>
      </SettingsBlock>

      <SettingsBlock :title="t('settings.formDefaults.design')" :description="t('settings.formDefaults.designHint')" icon="i-lucide-palette">
        <UFormField :label="t('settings.formDefaults.theme')" :help="t('settings.formDefaults.themeHelp')">
          <USelectMenu v-model="themeId" :items="themeItems" value-key="value" :search-input="{ placeholder: t('common.search') }" class="w-full sm:max-w-sm" />
        </UFormField>
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
          <span class="w-full max-w-xs shrink-0 overflow-hidden rounded-lg border border-default bg-elevated shadow-sm sm:w-56" aria-hidden="true">
            <TemplatesThumb :key="draft.theme_id ?? 'workspace'" :theme="thumbTokens" :title="chosenTheme ? themeName(chosenTheme) : t('settings.formDefaults.workspaceLook')" :labels="thumbLabels" tile />
          </span>
          <p class="text-xs text-muted">{{ chosenTheme ? t('settings.formDefaults.themeShown', { name: themeName(chosenTheme) }) : t('settings.formDefaults.workspaceShown') }}</p>
        </div>
        <UAlert v-if="missingTheme" color="warning" variant="subtle" icon="i-lucide-triangle-alert" :description="t('settings.formDefaults.themeGone')" />
      </SettingsBlock>

      <SettingsBlock :title="t('settings.formDefaults.thankYou')" :description="t('settings.formDefaults.thankYouHint')" icon="i-lucide-party-popper">
        <UFormField :label="t('settings.formDefaults.thankYouTitle')">
          <SettingsText v-model="draft.thank_you.title" :placeholder="t('renderer.thanks')" class="w-full" />
        </UFormField>
        <UFormField :label="t('settings.formDefaults.thankYouMessage')">
          <UTextarea :model-value="draft.thank_you.message ?? ''" :rows="3" autoresize class="w-full" @update:model-value="value => draft && (draft.thank_you.message = String(value) || null)" />
        </UFormField>
      </SettingsBlock>

      <SettingsBlock :title="t('settings.formDefaults.sharing')" :description="t('settings.formDefaults.sharingHint')" icon="i-lucide-share-2">
        <UFormField :label="t('settings.formDefaults.team')" :help="t('settings.formDefaults.teamHelp')">
          <USelectMenu v-model="draft.team_emails" :items="people" value-key="value" multiple icon="i-lucide-users-round" :placeholder="t('builder.emails.nobody')" :search-input="{ placeholder: t('common.search') }" class="w-full sm:max-w-sm" />
        </UFormField>
        <UFormField :label="t('settings.formDefaults.embed')" :help="domains.length ? undefined : t('settings.formDefaults.embedAny')" :error="badDomains.length ? t('settings.signin.badDomain', { list: badDomains.join(', ') }) : undefined">
          <UInputTags v-model="domains" :placeholder="t('settings.formDefaults.embedPlaceholder')" icon="i-lucide-globe" :add-on-blur="true" :add-on-paste="true" class="w-full" />
        </UFormField>
      </SettingsBlock>
    </div>
  </SettingsPage>
</template>
