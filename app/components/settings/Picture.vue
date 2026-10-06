<!--
  One branding picture (F14 M1): the current picture on the background it is meant for, Replace and
  Remove; or a drop zone. A new file uploads at once (pre-signed URL, real progress) and the page
  keeps its upload id until Save. PNG / JPEG / WebP only (no SVG: it can carry scripts).
-->
<script setup lang="ts">
import type { UploadPurpose } from '#shared/types/onboarding'

const props = defineProps<{ label: string; hint: string; purpose: UploadPurpose; maxMb: number; shape?: 'square' | 'wide' | 'icon'; dark?: boolean }>()
/** The preview address (saved file or the picked file) and what to send: an upload id, null to remove, undefined to keep. */
const url = defineModel<string | null>('url', { required: true })
const uploadId = defineModel<string | null | undefined>('uploadId', { required: true })
const { t } = useI18n()
const { handle } = useErrorHandler()
const { upload, progress, uploading, cancel } = useUpload()
const ACCEPT = ['image/png', 'image/jpeg', 'image/webp']

const file = ref<File | null>(null)
const picker = useTemplateRef<HTMLInputElement>('picker')
const error = ref<string | null>(null)
const objectUrls: string[] = []
watch(file, async picked => {
  error.value = null
  if (!picked) return
  if (!ACCEPT.includes(picked.type)) return (error.value = t('settings.picture.badType'))
  if (picked.size > props.maxMb * 1024 * 1024) return (error.value = t('settings.picture.tooBig', { n: props.maxMb }))
  try {
    const uploaded = await upload(picked, props.purpose)
    const local = URL.createObjectURL(picked)
    objectUrls.push(local)
    url.value = local
    uploadId.value = uploaded.id
  } catch (failure) {
    const normalised = handle(failure, { silent: true })
    if (!normalised.aborted) error.value = t('settings.picture.failed')
  } finally {
    file.value = null
    if (picker.value) picker.value.value = ''
  }
})
onBeforeUnmount(() => objectUrls.forEach(item => URL.revokeObjectURL(item)))
function remove() {
  cancel()
  url.value = null
  uploadId.value = null
}
const box = computed(() => (props.shape === 'wide' ? 'h-20 w-36' : props.shape === 'icon' ? 'size-12' : 'size-16'))
</script>

<template>
  <UFormField :label="label" :description="hint" :error="error ?? undefined">
    <div v-if="url && !uploading" class="flex items-center gap-4 rounded-lg border border-default p-3">
      <span class="flex shrink-0 items-center justify-center overflow-hidden rounded-md border border-default p-1.5" :class="[box, dark ? 'bg-neutral-950' : 'bg-elevated']">
        <img :src="url" :alt="label" class="max-h-full max-w-full" :class="shape === 'wide' ? 'size-full rounded object-cover' : 'object-contain'">
      </span>
      <div class="flex min-w-0 flex-1 flex-wrap justify-end gap-2">
        <input ref="picker" type="file" :accept="ACCEPT.join(',')" class="sr-only" tabindex="-1" aria-hidden="true" @change="event => (file = (event.target as HTMLInputElement).files?.[0] ?? null)">
        <UButton :label="t('settings.picture.replace')" icon="i-lucide-refresh-cw" color="neutral" variant="outline" size="sm" @click="picker?.click()" />
        <UButton :label="t('settings.picture.remove')" icon="i-lucide-trash-2" color="neutral" variant="ghost" size="sm" @click="remove" />
      </div>
    </div>
    <UFileUpload v-else v-model="file" :accept="ACCEPT.join(',')" :label="t('settings.picture.drop')" :description="t('settings.picture.types', { n: maxMb })" icon="i-lucide-image-up" color="neutral" layout="list" :disabled="uploading" class="min-h-28 w-full" />
    <div v-if="uploading" class="mt-3 flex items-center gap-3" aria-live="polite">
      <UProgress :model-value="progress" color="neutral" size="sm" class="flex-1" />
      <span class="w-10 text-end text-xs text-muted tabular-nums">{{ progress }}%</span>
      <UButton :label="t('common.cancel')" color="neutral" variant="link" size="xs" @click="cancel" />
    </div>
  </UFormField>
</template>
