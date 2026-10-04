<!--
  Share → Short link (F10 M3): `forms.formalie.com/s/{code}` — five easy characters for posters, SMS
  and QR codes. It always leads to the form's current link, so a printed code keeps working when the
  custom link changes. Created / removed at once (POST / DELETE /forms/{id}/short-link, audited);
  shows how many times it was opened. Removing it makes the code stop working.
-->
<script setup lang="ts">
import type { FormShareSettings, FormSummary } from '#shared/types/forms'
import { publicHosts, shortLink } from '#shared/utils/urls/public'

const props = defineProps<{ settings: FormShareSettings; form: FormSummary }>()
const emit = defineEmits<{ changed: [settings: FormShareSettings] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const confirm = useConfirm()
const { handle } = useErrorHandler()
const config = useRuntimeConfig().public
const request = useRequestURL()
const { number, relative } = useFormat()

const url = computed(() => (props.settings.short_link ? shortLink(publicHosts(config, request.port), props.settings.short_link.code) : ''))
const qrOpen = ref(false)

const { busy, run } = useBusy()
async function create() {
  await run(async () => {
    try {
      const { data } = await api.post<FormShareSettings>(`/forms/${props.form.id}/short-link`)
      emit('changed', data)
      toast.add({ title: t('share.short.created'), icon: 'i-lucide-check', color: 'success' })
    } catch (error) {
      handle(error)
    }
  })
}
async function remove() {
  if (!(await confirm({ title: t('share.short.removeTitle'), description: t('share.short.removeDesc'), confirmLabel: t('share.short.remove'), danger: true }))) return
  await run(async () => {
    try {
      const { data } = await api.del<FormShareSettings>(`/forms/${props.form.id}/short-link`)
      emit('changed', data)
      toast.add({ title: t('share.short.removed'), icon: 'i-lucide-check', color: 'success' })
    } catch (error) {
      handle(error)
    }
  })
}
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'p-4 sm:p-5' }">
    <div class="mb-3 flex items-start justify-between gap-3">
      <div class="flex items-start gap-3">
        <UIcon name="i-lucide-scissors" class="mt-0.5 size-5 shrink-0 text-muted" />
        <div>
          <h2 class="text-sm font-semibold text-highlighted">{{ t('share.short.title') }}</h2>
          <p class="text-xs text-muted">{{ t('share.short.desc') }}</p>
        </div>
      </div>
      <UBadge v-if="settings.short_link" :label="t('share.short.clicks', { n: number(settings.short_link.clicks) }, settings.short_link.clicks)" color="neutral" variant="subtle" icon="i-lucide-mouse-pointer-click" class="shrink-0" />
    </div>

    <div v-if="settings.short_link" class="flex flex-col gap-3">
      <AppCopyField :label="t('share.short.label')" :value="url" monospace />
      <div class="flex flex-wrap items-center justify-between gap-2">
        <span class="text-xs text-muted">{{ t('share.short.since', { when: relative(settings.short_link.created_at) }) }}</span>
        <div class="flex gap-2">
          <UButton :label="t('forms.overview.qr')" icon="i-lucide-qr-code" color="neutral" variant="outline" size="xs" @click="qrOpen = true" />
          <UButton :label="t('share.short.remove')" icon="i-lucide-trash-2" color="neutral" variant="outline" size="xs" :loading="busy" @click="remove" />
        </div>
      </div>
      <FormsShareQrModal v-model:open="qrOpen" :url="url" :form-name="form.name" :live="form.status === 'published'" />
    </div>
    <div v-else class="flex flex-wrap items-center justify-between gap-3 rounded-md border border-dashed border-default p-3">
      <p class="text-xs text-muted">{{ t('share.short.none') }}</p>
      <UButton :label="t('share.short.create')" icon="i-lucide-plus" color="neutral" size="sm" :loading="busy" @click="create" />
    </div>
  </UCard>
</template>
