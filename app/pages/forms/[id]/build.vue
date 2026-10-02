<!--
  Form builder (FRONTEND-SPEC §6, PROGRESS F7). Header: inline name · status + "Saved just now"
  (design meta line) · undo / redo · Preview · Publish. Body: palette | canvas | inspector on
  large screens; below that the canvas with palette / inspector in slide-overs (tablet) or
  bottom drawers (phone). Autosaves the draft; the published version stays live until Publish.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { FormSummary } from '#shared/types/forms'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { publishIssues } from '#shared/utils/forms/build'

definePageMeta({ breadcrumb: 'builder.crumb' })

const { t } = useI18n()
const route = useRoute()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { setLabel } = useBreadcrumbs()
const { relative } = useFormat()
const counts = useNavCounts()
const formId = String(route.params.id)

const builder = useFormBuilder()
provideFormBuilder(builder)

const form = ref<FormSummary | null>(null)
const rowVersion = ref(0)
const loading = ref(true)
const failed = ref<string | null>(null)
useHead({ title: () => (form.value ? `${form.value.name} · ${t('builder.crumb')}` : t('builder.crumb')) })

const autosave = useBuilderAutosave(formId, builder.schema, rowVersion, saved => {
  if (form.value)
    Object.assign(form.value, {
      has_unpublished_changes: saved.has_unpublished_changes,
      updated_at: saved.updated_at,
    })
})

async function load() {
  loading.value = true
  failed.value = null
  try {
    const { data } = await api.get<{
      form: FormSummary
      schema: FormSchemaV1
      published_version: number | null
    }>(`/forms/${formId}/builder`)
    form.value = data.form
    rowVersion.value = data.form.row_version
    builder.load(data.schema)
    builder.keysLocked.value = data.form.status !== 'draft' || data.published_version !== null
    setLabel(`/forms/${formId}`, data.form.name)
    autosave.start()
  } catch (error) {
    failed.value = handle(error, { silent: true }).code
  } finally {
    loading.value = false
  }
}
onMounted(load)

// ── Name (inline, saved after autosave settles so versions never race) ────────────────
const nameDraft = ref('')
watch(form, value => (nameDraft.value = value?.name ?? ''), { immediate: true })
async function saveName() {
  const name = nameDraft.value.trim()
  if (!form.value || !name || name === form.value.name) return (nameDraft.value = form.value?.name ?? '')
  await until(autosave.state).not.toBe('saving')
  try {
    const { data } = await api.patch<FormSummary>(`/forms/${formId}`, { row_version: rowVersion.value, name })
    form.value = { ...form.value, ...data }
    rowVersion.value = data.row_version
    setLabel(`/forms/${formId}`, data.name)
  } catch (error) {
    handle(error)
    nameDraft.value = form.value.name
  }
}

// ── Publish ──────────────────────────────────────────────────────────────────────
const publishOpen = ref(false)
const previewOpen = ref(false)
const { busy: publishing, run } = useBusy()
async function publish(summary: string | null) {
  await autosave.saveNow()
  const result = await run(() =>
    api.post<{ form: FormSummary; version: { number: number } }>(`/forms/${formId}/publish`, {
      row_version: rowVersion.value,
      change_summary: summary,
    }),
  )
  if (!result) return
  form.value = result.data.form
  rowVersion.value = result.data.form.row_version
  builder.keysLocked.value = true
  publishOpen.value = false
  counts.refresh(true)
  toast.add({
    title: t('builder.publish.done', { n: result.data.version.number }),
    icon: 'i-lucide-globe',
    color: 'success',
  })
}
const issues = computed(() =>
  Object.fromEntries(
    (builder.schema.value ? publishIssues(builder.schema.value) : [])
      .filter(issue => issue.field_id)
      .map(issue => [issue.field_id!, t(`builder.issue.${issue.code}`)]),
  ),
)

const phoneMenu = computed<DropdownMenuItem[][]>(() => [
  [
    {
      label: t('builder.undo'),
      icon: 'i-lucide-undo-2',
      disabled: !builder.history.canUndo.value,
      onSelect: () => {
        builder.history.undo()
      },
    },
    {
      label: t('builder.redo'),
      icon: 'i-lucide-redo-2',
      disabled: !builder.history.canRedo.value,
      onSelect: () => {
        builder.history.redo()
      },
    },
  ],
  [
    {
      label: t('builder.preview.button'),
      icon: 'i-lucide-eye',
      onSelect: () => {
        previewOpen.value = true
      },
    },
  ],
])

// ── Small screens: palette / inspector in panels ─────────────────────────────────────
const large = useMediaQuery('(min-width: 1024px)')
const tablet = useMediaQuery('(min-width: 768px)')
const paletteOpen = ref(false)
const inspectorOpen = ref(false)

// "Saved 2 minutes ago" stays current without re-rendering every second.
const now = ref(Date.now())
useIntervalFn(() => (now.value = Date.now()), 15_000)
const statusText = computed(() => {
  const s = autosave.state.value
  if (s === 'saving' || s === 'pending') return t('builder.save.saving')
  if (s === 'error') return t('builder.save.error')
  if (s === 'conflict') return t('builder.save.conflict')
  return autosave.savedAt.value
    ? t('builder.save.saved', { time: relative(autosave.savedAt.value, now.value) })
    : t('builder.save.upToDate')
})

defineShortcuts({
  meta_z: () => builder.history.undo(),
  meta_shift_z: () => builder.history.redo(),
  meta_y: () => builder.history.redo(),
  meta_d: { handler: () => builder.duplicate(), usingInput: false },
  delete: () => builder.removeWithUndo(),
  backspace: () => builder.removeWithUndo(),
  alt_arrowup: () => builder.selected.value.length === 1 && builder.move(builder.selected.value[0]!, -1),
  alt_arrowdown: () => builder.selected.value.length === 1 && builder.move(builder.selected.value[0]!, 1),
  escape: () => (builder.selected.value = []),
})
</script>

<template>
  <AppPanel id="form-builder" :title="form?.name ?? t('builder.crumb')">
    <template #title>
      <UInput
        v-if="form"
        v-model="nameDraft"
        variant="ghost"
        maxlength="120"
        :aria-label="t('forms.actions.rename')"
        :ui="{ base: 'px-1 -mx-1 text-base font-semibold text-highlighted sm:text-lg' }"
        class="min-w-0"
        @blur="saveName"
        @keydown.enter="($event.target as HTMLInputElement).blur()"
        @keydown.esc="nameDraft = form.name"
      />
      <USkeleton v-else class="h-6 w-48" />
    </template>
    <template v-if="form" #meta>
      <span class="flex min-w-0 items-center gap-1.5" aria-live="polite">
        <DataStatusBadge :status="form.status" />
        <UBadge
          v-if="form.has_unpublished_changes"
          :label="t('builder.unpublished')"
          color="warning"
          variant="subtle"
          size="sm"
          class="rounded-md"
        />
        <UIcon
          :name="
            autosave.state.value === 'saving' || autosave.state.value === 'pending'
              ? 'i-lucide-loader-circle'
              : autosave.state.value === 'error' || autosave.state.value === 'conflict'
                ? 'i-lucide-cloud-alert'
                : 'i-lucide-refresh-cw'
          "
          class="size-3 shrink-0"
          :class="autosave.state.value === 'saving' ? 'animate-spin' : ''"
        />
        <span class="truncate">{{ statusText }}</span>
      </span>
    </template>

    <template v-if="form" #actions>
      <UButton
        class="hidden sm:inline-flex"
        icon="i-lucide-undo-2"
        color="neutral"
        variant="outline"
        square
        :disabled="!builder.history.canUndo.value"
        :aria-label="t('builder.undo')"
        @click="builder.history.undo()"
      />
      <UButton
        class="hidden sm:inline-flex"
        icon="i-lucide-redo-2"
        color="neutral"
        variant="outline"
        square
        :disabled="!builder.history.canRedo.value"
        :aria-label="t('builder.redo')"
        @click="builder.history.redo()"
      />
      <UButton
        class="hidden sm:inline-flex"
        icon="i-lucide-eye"
        :label="t('builder.preview.button')"
        color="neutral"
        variant="outline"
        @click="previewOpen = true"
      />
      <!-- Phones: undo / redo / preview fold into one menu so the name stays visible. -->
      <UDropdownMenu :items="phoneMenu" :content="{ align: 'end' }" class="sm:hidden">
        <UButton
          class="sm:hidden"
          icon="i-lucide-ellipsis"
          color="neutral"
          variant="outline"
          square
          :aria-label="t('builder.actions.more')"
        />
      </UDropdownMenu>
      <UButton
        icon="i-lucide-globe"
        :label="t('builder.publish.button')"
        color="neutral"
        :loading="publishing"
        @click="publishOpen = true"
      />
    </template>

    <div
      v-if="loading"
      class="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)_300px]"
      :aria-label="t('common.loading')"
    >
      <USkeleton class="hidden h-[70vh] lg:block" />
      <USkeleton class="mx-auto h-[70vh] w-full max-w-3xl" />
      <USkeleton class="hidden h-[70vh] lg:block" />
    </div>

    <UEmpty
      v-else-if="failed"
      icon="i-lucide-file-question"
      :title="failed === 'FRM-GEN-1004' ? t('forms.detail.notFound') : t('dataView.errorTitle')"
      :actions="[
        { label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: load },
        { label: t('nav.forms'), to: '/forms', color: 'neutral' },
      ]"
      variant="outline"
    />

    <template v-else>
      <UAlert
        v-if="autosave.state.value === 'conflict'"
        icon="i-lucide-users"
        color="warning"
        variant="subtle"
        :title="t('builder.save.conflictTitle')"
        :description="t('builder.save.conflictDesc')"
        :actions="[
          { label: t('builder.save.reload'), color: 'neutral', icon: 'i-lucide-rotate-cw', onClick: load },
        ]"
      />
      <div class="grid items-start gap-4 lg:grid-cols-[240px_minmax(0,1fr)_300px]">
        <UCard v-if="large" class="sticky top-0" :ui="{ body: 'p-3 sm:p-3 h-[calc(100dvh-11rem)]' }">
          <FormsBuilderPalette />
        </UCard>
        <div class="mb-20 min-w-0 rounded-xl bg-elevated/40 p-3 sm:p-5 lg:mb-0">
          <FormsBuilderCanvas :issues="issues" />
        </div>
        <UCard v-if="large" class="sticky top-0" :ui="{ body: 'p-4 sm:p-4 h-[calc(100dvh-11rem)]' }">
          <FormsBuilderInspector />
        </UCard>
      </div>
    </template>

    <template v-if="!large">
      <!-- Below laptop width: palette and settings live in a floating bar at the bottom (thumb reach). -->
      <div v-if="form" class="pointer-events-none fixed inset-x-0 bottom-4 z-20 flex justify-center px-4">
        <div
          class="pointer-events-auto flex items-center gap-1 rounded-xl border border-default bg-default p-1 shadow-lg"
        >
          <UButton
            icon="i-lucide-plus"
            :label="t('builder.palette.title')"
            color="neutral"
            @click="paletteOpen = true"
          />
          <UButton
            icon="i-lucide-sliders-horizontal"
            :label="t('builder.inspector.panel')"
            color="neutral"
            variant="ghost"
            @click="inspectorOpen = true"
          />
        </div>
      </div>
      <USlideover v-if="tablet" v-model:open="paletteOpen" side="left" :title="t('builder.palette.title')">
        <template #body><FormsBuilderPalette @added="paletteOpen = false" /></template>
      </USlideover>
      <UDrawer
        v-else
        v-model:open="paletteOpen"
        :title="t('builder.palette.title')"
        :ui="{ body: 'h-[60dvh]' }"
      >
        <template #body><FormsBuilderPalette @added="paletteOpen = false" /></template>
      </UDrawer>
      <USlideover v-if="tablet" v-model:open="inspectorOpen" :title="t('builder.inspector.panel')">
        <template #body><FormsBuilderInspector /></template>
      </USlideover>
      <UDrawer
        v-else
        v-model:open="inspectorOpen"
        :title="t('builder.inspector.panel')"
        :ui="{ body: 'max-h-[75dvh] overflow-y-auto' }"
      >
        <template #body><FormsBuilderInspector /></template>
      </UDrawer>
    </template>

    <FormsBuilderPublishModal
      v-model:open="publishOpen"
      :busy="publishing"
      :republish="form?.status === 'published'"
      @publish="publish"
    />
    <FormsBuilderPreviewModal v-model:open="previewOpen" />
  </AppPanel>
</template>
