<!--
  Share settings (F10 M3) — the form editor's Share tab: who can open the form (anyone with the
  link / password), its custom link, response limit and availability; on the side the live link
  with copy, QR code and embed code. Changes are kept as a draft on the page and saved together
  (PUT /forms/{id}/share) from the bar at the bottom; they apply at once, also to published forms
  (no re-publish). Availability saves on its own (existing window).
-->
<script setup lang="ts">
import type { FormShareSettings, FormSummary, ShareDraft } from '#shared/types/forms'

const props = defineProps<{ session: BuilderSession }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { form, rowVersion } = props.session

const settings = ref<FormShareSettings | null>(null)
const loading = ref(true)
const failed = ref(false)

const draft = reactive<ShareDraft>({ access: 'public', password: '', limitOn: false, limit: 100, link: '' })
/** The custom link can be saved (empty, unchanged or checked as free). */
const linkOk = ref(true)

function reset(from: FormShareSettings) {
  Object.assign(draft, {
    access: from.access,
    password: '',
    limitOn: from.response_limit != null,
    // Starts at 10 (owner); a form that already has 10 or more responses starts 10 above its count.
    limit: from.response_limit ?? (from.responses_count < 10 ? 10 : from.responses_count + 10),
    link: from.custom_link ?? '',
  })
}
async function load() {
  loading.value = true
  failed.value = false
  try {
    const { data } = await api.get<FormShareSettings>(`/forms/${props.session.formId}/share`)
    settings.value = data
    reset(data)
  } catch (error) {
    failed.value = true
    handle(error)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const dirty = computed(() => {
  const s = settings.value
  if (!s) return false
  return (
    draft.access !== s.access ||
    !!draft.password ||
    (draft.limitOn ? draft.limit : null) !== s.response_limit ||
    (draft.link.trim() || null) !== s.custom_link
  )
})
const passwordMissing = computed(() => draft.access === 'password' && !settings.value?.has_password && draft.password.length < 8)
const canSave = computed(() => dirty.value && linkOk.value && !passwordMissing.value && (!draft.password || draft.password.length >= 8))

/** Keeps the rest of the editor in step: the form's version and what the overview / links show. */
function applyToSession(next: FormShareSettings) {
  rowVersion.value = next.row_version
  if (form.value)
    form.value = { ...form.value, access: next.access, custom_link: next.custom_link, response_limit: next.response_limit, opens_at: next.opens_at, closes_at: next.closes_at, row_version: next.row_version, short_code: next.short_link?.code ?? null }
}

const { busy, run } = useBusy()
async function save() {
  if (!settings.value || !canSave.value) return
  await run(async () => {
    try {
      const { data } = await api.put<FormShareSettings>(`/forms/${props.session.formId}/share`, {
        row_version: rowVersion.value,
        // The password first, so "password" access can be switched on in the same save.
        ...(draft.password ? { password: draft.password } : {}),
        access: draft.access,
        response_limit: draft.limitOn ? draft.limit : null,
        custom_link: draft.link.trim() || null,
      })
      settings.value = data
      reset(data)
      applyToSession(data)
      toast.add({ title: t('share.saved'), icon: 'i-lucide-check', color: 'success' })
    } catch (error) {
      const failure = handle(error, { silent: true })
      if (failure.code === 'FRM-GEN-1009') toast.add({ title: t('share.conflict'), color: 'warning', icon: 'i-lucide-users', actions: [{ label: t('builder.save.reload'), color: 'neutral', variant: 'outline', onClick: () => void props.session.load() }] })
      else handle(error)
    }
  })
}

/** The short link saves on its own (unsaved changes on the page stay as they are). */
function shortChanged(next: FormShareSettings) {
  settings.value = next
  applyToSession(next)
}

// Availability has its own window (also used from the forms list).
const availabilityOpen = ref(false)
function availabilitySaved(updated: FormSummary) {
  if (!settings.value) return
  settings.value = { ...settings.value, opens_at: updated.opens_at, closes_at: updated.closes_at, row_version: updated.row_version }
  applyToSession(settings.value)
}

onBeforeRouteLeave(async () => (dirty.value ? await useConfirm()({ title: t('share.leaveTitle'), description: t('share.leaveDesc'), confirmLabel: t('share.leave'), danger: true }) : true))
</script>

<template>
  <div v-if="loading" class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]" :aria-label="t('common.loading')">
    <div class="flex flex-col gap-4">
      <USkeleton v-for="n in 3" :key="n" class="h-48 w-full rounded-lg" />
    </div>
    <USkeleton class="h-72 w-full rounded-lg" />
  </div>
  <UEmpty
    v-else-if="failed || !settings || !form"
    icon="i-lucide-cloud-off"
    :title="t('dataView.errorTitle')"
    :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', icon: 'i-lucide-rotate-cw', onClick: load }]"
    variant="outline"
  />
  <div v-else class="flex flex-col gap-4 pb-20">
    <div class="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div class="flex min-w-0 flex-col gap-4">
        <FormsShareAccessCard v-model:draft="draft" :settings="settings" />
        <FormsShareLinkCard v-model:draft="draft" v-model:ok="linkOk" :settings="settings" :form="form" />
        <FormsShareShortLinkCard :settings="settings" :form="form" @changed="shortChanged" />
        <FormsShareLimitsCard v-model:draft="draft" :settings="settings" @availability="availabilityOpen = true" />
      </div>
      <FormsOverviewShare :form="form" class="lg:sticky lg:top-4" />
    </div>

    <!-- Unsaved changes: one bar for the whole page. -->
    <Transition enter-from-class="translate-y-4 opacity-0" leave-to-class="translate-y-4 opacity-0" enter-active-class="transition" leave-active-class="transition">
      <div v-if="dirty" class="sticky bottom-3 z-10 mx-auto flex w-full max-w-2xl flex-wrap items-center justify-between gap-2 rounded-lg border border-default bg-default/95 px-3 py-2 shadow-lg backdrop-blur" role="status">
        <span class="flex items-center gap-2 text-sm text-highlighted">
          <UIcon name="i-lucide-circle-dot" class="size-4 text-warning" />{{ passwordMissing ? t('share.needPassword') : t('share.unsaved') }}
        </span>
        <div class="flex gap-2">
          <UButton :label="t('share.discard')" color="neutral" variant="outline" size="sm" :disabled="busy" @click="reset(settings)" />
          <UButton :label="t('share.save')" icon="i-lucide-check" color="neutral" size="sm" :loading="busy" :disabled="!canSave" @click="save" />
        </div>
      </div>
    </Transition>
    <FormsListAvailabilityModal v-model:open="availabilityOpen" :form="form" @saved="availabilitySaved" />
  </div>
</template>
