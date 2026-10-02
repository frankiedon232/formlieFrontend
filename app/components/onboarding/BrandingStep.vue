<!--
  Step 2 — logo + brand colour. The logo uploads as soon as it is chosen (pre-signed URL, real
  progress); the step saves the upload id and colour. PNG / JPEG / WebP up to 2 MB (no SVG: scripts).
-->
<script setup lang="ts">
const branding = defineModel<OnboardingBrandingDraft>({ required: true })
const emit = defineEmits<{ submit: [] }>()
const { t } = useI18n()
const { handle } = useErrorHandler()
const { upload, progress, uploading, cancel } = useUpload()

const ACCEPT = ['image/png', 'image/jpeg', 'image/webp']
const MAX_BYTES = 2 * 1024 * 1024
const PRESETS = [
  '#18181B',
  '#2563EB',
  '#0F766E',
  '#16A34A',
  '#CA8A04',
  '#EA580C',
  '#DC2626',
  '#DB2777',
  '#7C3AED',
]

const file = ref<File | null>(null)
const fileError = ref<string | null>(null)
let objectUrl: string | null = null

watch(file, async picked => {
  fileError.value = null
  if (!picked) return
  if (!ACCEPT.includes(picked.type)) return (fileError.value = t('onboarding.branding.badType'))
  if (picked.size > MAX_BYTES) return (fileError.value = t('onboarding.branding.tooBig'))
  try {
    const uploaded = await upload(picked, 'logo')
    if (objectUrl) URL.revokeObjectURL(objectUrl)
    objectUrl = URL.createObjectURL(picked)
    branding.value.logo_url = objectUrl
    branding.value.logo_upload_id = uploaded.id
  } catch (error) {
    const normalised = handle(error, { silent: true })
    if (!normalised.aborted) fileError.value = t('onboarding.branding.uploadFailed')
    file.value = null
  }
})
onBeforeUnmount(() => {
  // Keep the preview URL alive only while it is the saved draft logo.
  if (objectUrl && branding.value.logo_url !== objectUrl) URL.revokeObjectURL(objectUrl)
})

function removeLogo() {
  cancel()
  file.value = null
  branding.value.logo_upload_id = null
  branding.value.logo_url = null
}

const colorModel = computed({
  get: () => branding.value.brand_color ?? '#18181B',
  set: value => (branding.value.brand_color = value.toUpperCase()),
})
</script>

<template>
  <UForm id="onboarding-step" :state="branding" class="flex flex-col gap-6" @submit="emit('submit')">
    <UFormField
      name="logo"
      :label="t('onboarding.branding.logo')"
      :description="t('onboarding.branding.logoHint')"
      :error="fileError ?? undefined"
    >
      <div
        v-if="branding.logo_url && !uploading"
        class="flex items-center gap-4 rounded-lg border border-default p-3"
      >
        <img
          :src="branding.logo_url"
          :alt="t('onboarding.branding.logoAlt')"
          class="size-14 rounded-md border border-default bg-elevated object-contain p-1"
        >
        <p class="min-w-0 flex-1 truncate text-sm text-default">
          {{ file?.name ?? t('onboarding.branding.current') }}
        </p>
        <UButton
          :label="t('onboarding.branding.remove')"
          icon="i-lucide-trash-2"
          color="neutral"
          variant="ghost"
          size="sm"
          @click="removeLogo"
        />
      </div>
      <UFileUpload
        v-else
        v-model="file"
        :accept="ACCEPT.join(',')"
        :label="t('onboarding.branding.drop')"
        :description="t('onboarding.branding.types')"
        icon="i-lucide-image-up"
        color="neutral"
        layout="list"
        :disabled="uploading"
        class="min-h-36 w-full"
      />
      <div v-if="uploading" class="mt-3 flex items-center gap-3" aria-live="polite">
        <UProgress :model-value="progress" color="neutral" size="sm" class="flex-1" />
        <span class="w-10 text-end text-xs text-muted tabular-nums">{{ progress }}%</span>
        <UButton :label="t('common.cancel')" color="neutral" variant="link" size="xs" @click="removeLogo" />
      </div>
    </UFormField>

    <UFormField
      name="brand_color"
      :label="t('onboarding.branding.colour')"
      :description="t('onboarding.branding.colourHint')"
    >
      <div
        class="flex flex-wrap items-center gap-2"
        role="radiogroup"
        :aria-label="t('onboarding.branding.colour')"
      >
        <UButton
          v-for="color in PRESETS"
          :key="color"
          role="radio"
          :aria-checked="branding.brand_color === color"
          :aria-label="color"
          color="neutral"
          variant="outline"
          square
          class="size-9 justify-center rounded-full p-0"
          :class="
            branding.brand_color === color
              ? 'ring-2 ring-offset-2 ring-(--ui-border-inverted) ring-offset-(--ui-bg)'
              : ''
          "
          @click="branding.brand_color = color"
        >
          <span class="size-6 rounded-full" :style="{ backgroundColor: color }" />
        </UButton>
        <UPopover>
          <UButton
            :label="t('onboarding.branding.custom')"
            icon="i-lucide-pipette"
            color="neutral"
            variant="outline"
            size="sm"
            class="ms-1"
          />
          <template #content>
            <div class="flex flex-col gap-3 p-3">
              <UColorPicker v-model="colorModel" />
              <UInput
                v-model="colorModel"
                class="font-mono"
                size="sm"
                :aria-label="t('onboarding.branding.hex')"
              />
            </div>
          </template>
        </UPopover>
        <UButton
          v-if="branding.brand_color"
          :label="t('onboarding.branding.reset')"
          color="neutral"
          variant="link"
          size="sm"
          @click="branding.brand_color = null"
        />
      </div>
    </UFormField>
  </UForm>
</template>
