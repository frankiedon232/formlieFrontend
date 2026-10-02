<!--
  Image token (cover, background, split image, logo): upload (PNG, JPG, WebP, GIF, SVG · 5 MB,
  with progress) or an https link; thumbnail with Replace / Remove.
-->
<script setup lang="ts">
defineProps<{ label: string; modelValue: string | null; hint?: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string | null] }>()
const { t } = useI18n()
const toast = useToast()
const { handle } = useErrorHandler()
const { upload, progress, uploading } = useUpload()

const TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/gif', 'image/svg+xml']
const picker = useTemplateRef<HTMLInputElement>('picker')
const link = ref('')
const linkError = computed(() => (link.value && !/^https:\/\/\S+$/i.test(link.value) ? t('builder.blocks.linkInvalid') : ''))

async function take(file: File | undefined) {
  if (!file) return
  if (!TYPES.includes(file.type)) return toast.add({ title: t('builder.blocks.imageType'), color: 'error', icon: 'i-lucide-image-off' })
  if (file.size > 5 * 1024 * 1024) return toast.add({ title: t('builder.blocks.imageSize', { mb: 5 }), color: 'error', icon: 'i-lucide-image-off' })
  try {
    emit('update:modelValue', (await upload(file, 'form_image')).url)
  } catch (error) {
    handle(error)
  } finally {
    if (picker.value) picker.value.value = ''
  }
}
function useLink() {
  if (!link.value || linkError.value) return
  emit('update:modelValue', link.value)
  link.value = ''
}
</script>

<template>
  <UFormField :label="label" :description="hint">
    <div class="flex flex-col gap-2">
      <div v-if="modelValue" class="flex items-center gap-2">
        <img :src="modelValue" alt="" class="h-12 w-20 shrink-0 rounded-md border border-default object-cover" >
        <UButton :label="t('builder.blocks.replace')" icon="i-lucide-replace" color="neutral" variant="outline" size="xs" :loading="uploading" @click="picker?.click()" />
        <UButton icon="i-lucide-trash-2" color="neutral" variant="ghost" size="xs" square :aria-label="t('builder.blocks.removeImage')" @click="emit('update:modelValue', null)" />
      </div>
      <template v-else>
        <UButton
          :label="t('designer.upload')"
          icon="i-lucide-image-up"
          color="neutral"
          variant="outline"
          size="sm"
          block
          :loading="uploading"
          @click="picker?.click()"
        />
        <UFormField :error="linkError || undefined">
          <UInput v-model="link" size="sm" icon="i-lucide-link" :placeholder="t('builder.blocks.imageLink')" class="w-full" @keydown.enter.prevent="useLink">
            <template #trailing>
              <UButton :label="t('builder.blocks.useLink')" color="neutral" variant="link" size="xs" :disabled="!link || !!linkError" @click="useLink" />
            </template>
          </UInput>
        </UFormField>
      </template>
      <UProgress v-if="uploading" :model-value="progress" color="neutral" size="xs" />
      <input ref="picker" type="file" :accept="TYPES.join(',')" class="hidden" @change="take(($event.target as HTMLInputElement).files?.[0])">
    </div>
  </UFormField>
</template>
