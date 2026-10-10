<!--
  Settings → Appearance (F14 M6, owner 2026-10-05): the workspace's own look of the whole portal.
  Presets to start from; colours (primary incl. the brand colour with a readability check, neutrals,
  background); light and dark (default mode, other colours in dark mode); shape and type (corners, font, text size); sidebar (rail, menu, count badges); header
  (breadcrumbs, search) and footer; page (width, density). Every change shows on the real portal at
  once (the page is the preview, plus a small picture); Discard or leaving puts it back. Reset to Formalie.
-->
<script setup lang="ts">
import { APPEARANCE_FONTS, APPEARANCE_NEUTRALS, APPEARANCE_PRESETS, APPEARANCE_PRIMARIES, APPEARANCE_RADII, FORMALIE_APPEARANCE, type AppearanceSettings } from '#shared/types/appearance'
import { appearanceSchema } from '#shared/utils/settings/schemas'

definePageMeta({ breadcrumb: 'settings.nav.appearance' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.appearance') })
const form = useSettingsForm('appearance', { schema: appearanceSchema })
const { draft } = form
const store = useWorkspaceSettings()
const appearance = useAppearance()

// The portal is the preview: the draft applies everywhere while this page is open
watch(draft, value => (appearance.preview.value = value ? structuredClone(toRaw(value)) : null), { deep: true, immediate: true })
watch(form.saved, value => value && appearance.put(structuredClone(toRaw(value))))
onBeforeUnmount(() => (appearance.preview.value = null))

const brand = computed(() => store.settings.value?.branding.brand_color ?? appearance.brand.value)
const name = computed(() => store.settings.value?.company.display_name ?? '')
/** Marks the look as changed by hand once a single choice moves away from the preset. */
const set = <K extends keyof AppearanceSettings>(key: K, value: AppearanceSettings[K]) => draft.value && ((draft.value[key] = value), (draft.value.preset = 'custom'))
function usePreset(key: string) {
  if (!draft.value) return
  Object.assign(draft.value, structuredClone(FORMALIE_APPEARANCE), structuredClone(APPEARANCE_PRESETS[key] ?? {}), { preset: key })
}
const reset = () => usePreset('formalie')

// Swatches (class names written out so Tailwind keeps them)
const PRIMARY_CLASS: Record<string, string> = {
  mono: 'bg-[linear-gradient(135deg,#0a0a0a_50%,#fafafa_50%)]',
  indigo: 'bg-indigo-500', blue: 'bg-blue-500', sky: 'bg-sky-500', teal: 'bg-teal-500', emerald: 'bg-emerald-500', green: 'bg-green-500', amber: 'bg-amber-500',
  orange: 'bg-orange-500', red: 'bg-red-500', rose: 'bg-rose-500', pink: 'bg-pink-500', violet: 'bg-violet-500', purple: 'bg-purple-500',
}
const NEUTRAL_CLASS: Record<string, string> = { zinc: 'bg-zinc-500', slate: 'bg-slate-500', gray: 'bg-gray-500', neutral: 'bg-neutral-500', stone: 'bg-stone-500' }
const primaries = computed(() => APPEARANCE_PRIMARIES.filter(key => key !== 'brand' || brand.value).map(key => ({ value: key, label: t(`settings.appearance.color.${key}`), class: PRIMARY_CLASS[key], style: key === 'brand' ? { backgroundColor: brand.value! } : undefined })))
const neutrals = computed(() => APPEARANCE_NEUTRALS.map(key => ({ value: key, label: t(`settings.appearance.neutral.${key}`), class: NEUTRAL_CLASS[key] })))
const brandContrast = computed(() => (draft.value?.primary === 'brand' && brand.value ? contrastWithWhite(brand.value) : null))

const option = (keys: readonly string[], group: string, icons?: Record<string, string>) => keys.map(value => ({ value, label: t(`settings.appearance.${group}.${value}`), icon: icons?.[value] }))
const radii = computed(() => option(APPEARANCE_RADII, 'radius'))
const fonts = computed(() => option(APPEARANCE_FONTS, 'font'))
const PRESET_SWATCH: Record<string, string> = { formalie: PRIMARY_CLASS.mono!, midnight: 'bg-slate-900', ocean: 'bg-blue-500', forest: 'bg-emerald-500', sunset: 'bg-orange-500', classic: 'bg-indigo-500', brand: '' }
const presets = computed(() => Object.keys(APPEARANCE_PRESETS).filter(key => key !== 'brand' || brand.value))
</script>

<template>
  <SettingsPage id="settings-appearance" :title="t('settings.nav.appearance')" :subtitle="t('settings.desc.appearance')" icon="i-lucide-palette" :form="{ dirty: form.dirty.value, saving: form.saving.value, updated: form.updated.value }" @save="form.save" @discard="form.discard">
    <template #actions>
      <UButton :label="t('settings.appearance.reset')" icon="i-lucide-rotate-ccw" color="neutral" variant="outline" class="hidden sm:inline-flex" :disabled="draft?.preset === 'formalie'" @click="reset" />
    </template>
    <AppEmpty v-if="form.failed.value && !draft" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => form.reload() }]" />
    <div v-else-if="!draft" class="flex flex-col gap-6"><USkeleton v-for="n in 4" :key="n" class="h-32 rounded-lg" /></div>
    <div v-else class="grid gap-8 2xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div class="flex min-w-0 flex-col gap-6">
        <SettingsBlock :title="t('settings.appearance.presets')" :description="t('settings.appearance.presetsHint')" icon="i-lucide-sparkles">
          <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <button v-for="key in presets" :key="key" type="button" class="flex items-center gap-2 rounded-lg border p-2.5 text-start text-sm transition-colors focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)" :class="draft.preset === key ? 'border-inverted bg-elevated/60' : 'border-default hover:border-accented'" @click="usePreset(key)">
              <span class="size-5 shrink-0 rounded-full ring-1 ring-black/10 dark:ring-white/15" :class="PRESET_SWATCH[key]" :style="key === 'brand' && brand ? { backgroundColor: brand } : undefined" />
              <span class="truncate font-medium text-highlighted">{{ t(`settings.appearance.preset.${key}`) }}</span>
            </button>
          </div>
          <p class="flex items-start gap-1.5 text-xs text-muted"><UIcon name="i-lucide-eye" class="mt-0.5 size-3.5 shrink-0" />{{ t('settings.appearance.live') }}</p>
        </SettingsBlock>

        <SettingsBlock :title="t('settings.appearance.colours')" :description="t('settings.appearance.coloursHint')" icon="i-lucide-paintbrush">
          <UFormField :label="t('settings.appearance.primary')" :help="t('settings.appearance.primaryHelp')">
            <SettingsAppearanceSwatches :model-value="draft.primary" :items="primaries" :label="t('settings.appearance.primary')" @update:model-value="value => set('primary', value as AppearanceSettings['primary'])" />
          </UFormField>
          <UAlert v-if="brandContrast !== null && brandContrast < 4.5" color="warning" variant="subtle" icon="i-lucide-contrast" :title="t('settings.appearance.lowContrast')" :description="t('settings.appearance.lowContrastDesc', { ratio: brandContrast.toFixed(1) })" />
          <UFormField :label="t('settings.appearance.neutrals')" :help="t('settings.appearance.neutralsHelp')">
            <SettingsAppearanceSwatches :model-value="draft.neutral" :items="neutrals" :label="t('settings.appearance.neutrals')" @update:model-value="value => set('neutral', value as AppearanceSettings['neutral'])" />
          </UFormField>
          <UFormField :label="t('settings.appearance.background')">
            <UTabs :model-value="draft.background" :items="option(['plain', 'tinted'], 'bg')" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="w-fit" @update:model-value="value => set('background', value as AppearanceSettings['background'])" />
          </UFormField>
        </SettingsBlock>

        <SettingsAppearanceModes :draft="draft" :primaries="primaries" :neutrals="neutrals" @change="patch => draft && Object.assign(draft, patch, { preset: 'custom' })" />

        <SettingsBlock :title="t('settings.appearance.shape')" :description="t('settings.appearance.shapeHint')" icon="i-lucide-type">
          <UFormField :label="t('settings.appearance.corners')">
            <UTabs :model-value="draft.radius" :items="radii" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="w-fit max-w-full overflow-x-auto" @update:model-value="value => set('radius', value as AppearanceSettings['radius'])" />
          </UFormField>
          <div class="grid gap-4 sm:grid-cols-2">
            <UFormField :label="t('settings.appearance.fontLabel')">
              <USelect :model-value="draft.font" :items="fonts" class="w-full" @update:model-value="value => set('font', value as AppearanceSettings['font'])" />
            </UFormField>
            <UFormField :label="t('settings.appearance.textSize')">
              <UTabs :model-value="draft.text_size" :items="option(['sm', 'md', 'lg'], 'size')" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="w-fit" @update:model-value="value => set('text_size', value as AppearanceSettings['text_size'])" />
            </UFormField>
          </div>
        </SettingsBlock>

        <SettingsBlock :title="t('settings.appearance.sidebar')" :description="t('settings.appearance.sidebarHint')" icon="i-lucide-panel-left">
          <div class="grid gap-4 sm:grid-cols-2">
            <UFormField :label="t('settings.appearance.rail')">
              <UTabs :model-value="draft.rail" :items="option(['light', 'dark'], 'tone', { light: 'i-lucide-sun', dark: 'i-lucide-moon' })" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="w-fit" @update:model-value="value => set('rail', value as AppearanceSettings['rail'])" />
            </UFormField>
            <UFormField :label="t('settings.appearance.menu')">
              <UTabs :model-value="draft.menu" :items="option(['light', 'dark'], 'tone', { light: 'i-lucide-sun', dark: 'i-lucide-moon' })" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="w-fit" @update:model-value="value => set('menu', value as AppearanceSettings['menu'])" />
            </UFormField>
          </div>
          <USwitch :model-value="draft.menu_badges" :label="t('settings.appearance.badges')" :description="t('settings.appearance.badgesHint')" color="neutral" @update:model-value="value => set('menu_badges', !!value)" />
        </SettingsBlock>

        <SettingsBlock :title="t('settings.appearance.headerFooter')" :description="t('settings.appearance.headerFooterHint')" icon="i-lucide-panel-top">
          <div class="flex flex-col gap-3">
            <USwitch :model-value="draft.header.breadcrumbs" :label="t('settings.appearance.breadcrumbs')" color="neutral" @update:model-value="value => draft && ((draft.header.breadcrumbs = !!value), (draft.preset = 'custom'))" />
            <USwitch :model-value="draft.header.search" :label="t('settings.appearance.search')" :description="t('settings.appearance.searchHint')" color="neutral" @update:model-value="value => draft && ((draft.header.search = !!value), (draft.preset = 'custom'))" />
            <USwitch :model-value="draft.footer" :label="t('settings.appearance.footer')" color="neutral" @update:model-value="value => set('footer', !!value)" />
          </div>
        </SettingsBlock>

        <SettingsBlock :title="t('settings.appearance.page')" :description="t('settings.appearance.pageHint')" icon="i-lucide-layout-panel-left">
          <div class="grid gap-4 sm:grid-cols-2">
            <UFormField :label="t('settings.appearance.width')">
              <UTabs :model-value="draft.content_width" :items="option(['full', 'centred'], 'widthOption', { full: 'i-lucide-move-horizontal', centred: 'i-lucide-align-center-horizontal' })" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="w-fit" @update:model-value="value => set('content_width', value as AppearanceSettings['content_width'])" />
            </UFormField>
            <UFormField :label="t('settings.appearance.density')">
              <UTabs :model-value="draft.density" :items="option(['comfortable', 'compact'], 'densityOption')" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="w-fit" @update:model-value="value => set('density', value as AppearanceSettings['density'])" />
            </UFormField>
          </div>
        </SettingsBlock>
      </div>

      <aside class="w-full max-w-xl 2xl:sticky 2xl:top-0 2xl:max-w-none 2xl:self-start">
        <div class="flex flex-col gap-3 rounded-xl border border-default bg-elevated/30 p-4">
          <span class="text-[11px] font-medium tracking-wide text-muted uppercase">{{ t('settings.appearance.preview') }}</span>
          <div class="grid gap-3 sm:grid-cols-2 2xl:grid-cols-1">
            <div class="flex flex-col gap-1.5">
              <span class="flex items-center gap-1 text-[11px] text-muted"><UIcon name="i-lucide-sun" class="size-3" />{{ t('settings.appearance.mode.light') }}</span>
              <SettingsAppearancePreview :look="draft" :name="name" class="light" />
            </div>
            <div class="flex flex-col gap-1.5">
              <span class="flex items-center gap-1 text-[11px] text-muted"><UIcon name="i-lucide-moon" class="size-3" />{{ t('settings.appearance.mode.dark') }}</span>
              <SettingsAppearancePreview :look="draft" :name="name" class="dark" />
            </div>
          </div>
          <p class="text-xs text-muted">{{ t('settings.appearance.previewHint') }}</p>
          <UButton :label="t('settings.appearance.reset')" icon="i-lucide-rotate-ccw" color="neutral" variant="outline" size="sm" class="w-fit sm:hidden" :disabled="draft.preset === 'formalie'" @click="reset" />
        </div>
      </aside>
    </div>
  </SettingsPage>
</template>
