<!--
  Settings → Branding (F14 M1): the logo (and one for dark backgrounds), the browser tab icon, the
  brand colour, and the workspace sign-in page's picture and welcome, with a live preview of that
  page in light and dark. Pictures upload at once and count on Save. Saved branding shows on the
  sign-in page, in the browser tab and in the portal straight away.
-->
<script setup lang="ts">
import type { BrandingSaveRequest, BrandingSettings } from '#shared/types/settings'
import { brandingSchema } from '#shared/utils/settings/schemas'

definePageMeta({ breadcrumb: 'settings.nav.branding' })
const { t } = useI18n()
useHead({ title: () => t('settings.nav.branding') })
const tenant = useTenant()
const store = useWorkspaceSettings()

// Pictures: an upload id once replaced, null once removed, undefined while kept
const uploads = reactive<Record<'logo' | 'logo_dark' | 'favicon' | 'signin_image', string | null | undefined>>({ logo: undefined, logo_dark: undefined, favicon: undefined, signin_image: undefined })
const body = (draft: BrandingSettings): BrandingSaveRequest => ({
  ...(uploads.logo !== undefined ? { logo_upload_id: uploads.logo } : {}),
  ...(uploads.logo_dark !== undefined ? { logo_dark_upload_id: uploads.logo_dark } : {}),
  ...(uploads.favicon !== undefined ? { favicon_upload_id: uploads.favicon } : {}),
  ...(uploads.signin_image !== undefined ? { signin_image_upload_id: uploads.signin_image } : {}),
  brand_color: draft.brand_color,
  signin_message: draft.signin_message,
})
const form = useSettingsForm('branding', { schema: brandingSchema.pick({ brand_color: true, signin_message: true }), body })
const { draft, errorOf } = form
watch(form.dirty, dirty => {
  if (dirty) return
  for (const key of Object.keys(uploads) as (keyof typeof uploads)[]) uploads[key] = undefined
})
// The sign-in page, tab icon and portal follow at once after saving
watch(() => store.settings.value?.branding, branding => {
  if (branding) tenant.updateProfile({ logo_url: branding.logo_url, logo_dark_url: branding.logo_dark_url, favicon_url: branding.favicon_url, signin_image_url: branding.signin_image_url, signin_message: branding.signin_message, colors: { primary: branding.brand_color } })
})

const PRESETS = ['#18181B', '#2563EB', '#0F766E', '#16A34A', '#CA8A04', '#EA580C', '#DC2626', '#DB2777', '#7C3AED']
const colorModel = computed({
  get: () => draft.value?.brand_color ?? '#18181B',
  set: value => draft.value && (draft.value.brand_color = value.toUpperCase()),
})
const name = computed(() => store.settings.value?.company.display_name ?? tenant.profile.value?.name ?? '')
</script>

<template>
  <SettingsPage id="settings-branding" :title="t('settings.nav.branding')" :subtitle="t('settings.desc.branding')" icon="i-lucide-badge-check" :form="{ dirty: form.dirty.value, saving: form.saving.value, updated: form.updated.value }" @save="form.save" @discard="form.discard">
    <AppEmpty v-if="form.failed.value && !draft" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => form.reload() }]" />
    <div v-else-if="!draft" class="flex flex-col gap-6"><USkeleton v-for="n in 3" :key="n" class="h-40 rounded-lg" /></div>
    <div v-else class="grid gap-8 2xl:grid-cols-[minmax(0,1fr)_24rem]">
      <div class="flex min-w-0 flex-col gap-6">
        <SettingsBlock :title="t('settings.branding.logos')" :description="t('settings.branding.logosHint')" icon="i-lucide-image">
          <div class="grid gap-4 sm:grid-cols-2">
            <SettingsPicture v-model:url="draft.logo_url" v-model:upload-id="uploads.logo" :label="t('settings.branding.logo')" :hint="t('settings.branding.logoHint')" purpose="logo" :max-mb="2" />
            <SettingsPicture v-model:url="draft.logo_dark_url" v-model:upload-id="uploads.logo_dark" :label="t('settings.branding.logoDark')" :hint="t('settings.branding.logoDarkHint')" purpose="logo" :max-mb="2" dark />
          </div>
          <SettingsPicture v-model:url="draft.favicon_url" v-model:upload-id="uploads.favicon" :label="t('settings.branding.favicon')" :hint="t('settings.branding.faviconHint')" purpose="logo" :max-mb="2" shape="icon" />
        </SettingsBlock>

        <SettingsBlock :title="t('onboarding.branding.colour')" :description="t('settings.branding.colourHint')" icon="i-lucide-paintbrush">
          <div class="flex flex-wrap items-center gap-2" role="radiogroup" :aria-label="t('onboarding.branding.colour')">
            <UButton v-for="color in PRESETS" :key="color" role="radio" :aria-checked="draft.brand_color === color" :aria-label="color" color="neutral" variant="outline" square class="size-9 justify-center rounded-full p-0" :class="draft.brand_color === color ? 'ring-2 ring-offset-2 ring-(--ui-border-inverted) ring-offset-(--ui-bg)' : ''" @click="draft.brand_color = color">
              <span class="size-6 rounded-full" :style="{ backgroundColor: color }" />
            </UButton>
            <UPopover>
              <UButton :label="t('onboarding.branding.custom')" icon="i-lucide-pipette" color="neutral" variant="outline" size="sm" class="ms-1" />
              <template #content>
                <div class="flex flex-col gap-3 p-3">
                  <UColorPicker v-model="colorModel" />
                  <UInput v-model="colorModel" class="font-mono" size="sm" :aria-label="t('onboarding.branding.hex')" />
                </div>
              </template>
            </UPopover>
            <UButton v-if="draft.brand_color" :label="t('onboarding.branding.reset')" color="neutral" variant="link" size="sm" @click="draft.brand_color = null" />
          </div>
          <p v-if="errorOf('brand_color')" class="text-xs text-error">{{ errorOf('brand_color') }}</p>
        </SettingsBlock>

        <SettingsBlock :title="t('settings.branding.signin')" :description="t('settings.branding.signinHint')" icon="i-lucide-log-in">
          <SettingsPicture v-model:url="draft.signin_image_url" v-model:upload-id="uploads.signin_image" :label="t('settings.branding.signinImage')" :hint="t('settings.branding.signinImageHint')" purpose="share_image" :max-mb="5" shape="wide" />
          <UFormField :label="t('settings.branding.signinMessage')" :description="t('settings.branding.signinMessageHint')" :error="errorOf('signin_message')">
            <UTextarea :model-value="draft.signin_message ?? ''" :rows="2" autoresize maxlength="160" class="w-full" :placeholder="t('authLayout.headline')" @update:model-value="(value: string) => draft && (draft.signin_message = value || null)" />
            <template #hint><span class="text-xs text-muted tabular-nums">{{ (draft.signin_message ?? '').length }}/160</span></template>
          </UFormField>
        </SettingsBlock>
      </div>
      <aside class="order-first max-w-xl 2xl:sticky 2xl:top-0 2xl:order-none 2xl:max-w-none 2xl:self-start">
        <SettingsSigninPreview :name="name" :logo="draft.logo_url" :logo-dark="draft.logo_dark_url" :image="draft.signin_image_url" :message="draft.signin_message" :color="draft.brand_color" :favicon="draft.favicon_url" :methods="store.settings.value?.signin.methods" />
      </aside>
    </div>
  </SettingsPage>
</template>
