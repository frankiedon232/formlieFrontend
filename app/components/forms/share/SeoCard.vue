<!--
  Share → Search & link preview (F10 M3, decision 95): the title, description and image people see
  when the link is shared (WhatsApp, LinkedIn, email…) and in search results, and whether search
  engines may list the form. Empty fields use the form's own title and intro (shown as the
  placeholder). The image uploads at once (pre-signed, with progress); the rest saves with the page.
-->
<script setup lang="ts">
import type { FormShareSettings, FormSummary, ShareDraft } from '#shared/types/forms'
import { formLink, publicHosts } from '#shared/utils/urls/public'

const props = defineProps<{ settings: FormShareSettings; form: FormSummary }>()
const draft = defineModel<ShareDraft>('draft', { required: true })
const { t } = useI18n()
const toast = useToast()
const { handle } = useErrorHandler()
const config = useRuntimeConfig().public
const request = useRequestURL()
const tenant = useTenant()

const TITLE_MAX = 70
const DESCRIPTION_MAX = 200
const url = computed(() => formLink(publicHosts(config, request.port), props.form.custom_link || props.form.public_key, 'fill', tenant.profile.value?.subdomain ?? null))
const shownTitle = computed(() => draft.value.seoTitle.trim() || props.settings.seo.default_title)
const shownDescription = computed(() => draft.value.seoDescription.trim() || props.settings.seo.default_description)

// Image: PNG / JPEG / WebP up to 5 MB, straight to storage.
const { upload, progress, uploading, cancel } = useUpload()
const picker = useTemplateRef<HTMLInputElement>('picker')
async function picked(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) {
    toast.add({ title: t('share.seo.imageRule'), color: 'warning', icon: 'i-lucide-image-off' })
    return
  }
  try {
    const uploaded = await upload(file, 'share_image')
    draft.value.seoImage = { id: uploaded.id, url: uploaded.url }
  } catch (error) {
    handle(error)
  }
}
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'p-4 sm:p-5' }">
    <div class="mb-4 flex items-start gap-3">
      <UIcon name="i-lucide-megaphone" class="mt-0.5 size-5 shrink-0 text-muted" />
      <div>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('share.seo.title') }}</h2>
        <p class="text-xs text-muted">{{ t('share.seo.desc') }}</p>
      </div>
    </div>

    <div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,18rem)]">
      <div class="flex min-w-0 flex-col gap-4">
        <UFormField :label="t('share.seo.titleLabel')" :hint="`${draft.seoTitle.length}/${TITLE_MAX}`" :description="t('share.seo.emptyUsesForm')">
          <UInput v-model="draft.seoTitle" :maxlength="TITLE_MAX" :placeholder="settings.seo.default_title" class="w-full" />
        </UFormField>
        <UFormField :label="t('share.seo.descriptionLabel')" :hint="`${draft.seoDescription.length}/${DESCRIPTION_MAX}`">
          <UTextarea v-model="draft.seoDescription" :maxlength="DESCRIPTION_MAX" :rows="3" autoresize :placeholder="settings.seo.default_description || t('share.seo.descriptionPlaceholder')" class="w-full" />
        </UFormField>

        <UFormField :label="t('share.seo.image')" :description="t('share.seo.imageHint')">
          <div class="flex flex-wrap items-center gap-3">
            <div class="relative aspect-[1.91/1] w-40 shrink-0 overflow-hidden rounded-md border border-default bg-elevated">
              <img v-if="draft.seoImage" :src="draft.seoImage.url" alt="" class="size-full object-cover">
              <UIcon v-else name="i-lucide-image" class="absolute inset-0 m-auto size-6 text-muted" />
              <div v-if="uploading" class="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-default/80 px-3">
                <span class="text-xs font-semibold tabular-nums text-highlighted">{{ progress }}%</span>
                <UProgress :model-value="progress" color="neutral" size="xs" class="w-full" />
              </div>
            </div>
            <div class="flex flex-wrap gap-2">
              <UButton
                :label="draft.seoImage ? t('share.seo.replace') : t('share.seo.upload')"
                icon="i-lucide-upload"
                color="neutral"
                variant="outline"
                size="xs"
                :loading="uploading"
                @click="picker?.click()"
              />
              <UButton v-if="uploading" :label="t('common.cancel')" color="neutral" variant="ghost" size="xs" @click="cancel" />
              <UButton v-else-if="draft.seoImage" :label="t('share.seo.removeImage')" icon="i-lucide-x" color="neutral" variant="ghost" size="xs" @click="draft.seoImage = null" />
            </div>
            <input ref="picker" type="file" accept="image/png,image/jpeg,image/webp" class="hidden" @change="picked">
          </div>
        </UFormField>

        <USwitch v-model="draft.noindex" :label="t('share.seo.noindex')" :description="t('share.seo.noindexDesc')" color="neutral" />
      </div>

      <FormsShareSeoPreview
        :title="shownTitle"
        :description="shownDescription"
        :image="draft.seoImage?.url ?? null"
        :url="url"
        :site-name="tenant.profile.value?.name || form.name"
        :noindex="draft.noindex"
      />
    </div>
  </UCard>
</template>
