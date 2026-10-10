<!--
  New form (F6): blank · from a template (catalogue, F9) · import a JSON export (FormSchema v1, validated
  and previewed before anything is created). `?mode=template|import` and `?template=<key>` preselect.
-->
<script setup lang="ts">
import type { FormFolder, FormSummary } from '#shared/types/forms'
import { systemTemplate } from '#shared/templates'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'

definePageMeta({ breadcrumb: 'nav.newForm' })

const { t, locale } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const counts = useNavCounts()
const { busy, run } = useBusy()
// From the rail's New template (owner, 2026-10-06): a template starts as a form, then Save as template
const forTemplate = computed(() => route.query.purpose === 'template')
useHead({ title: () => (forTemplate.value ? t('nav.newTemplate') : t('nav.newForm')) })

type Mode = 'blank' | 'template' | 'import'
const mode = computed<Mode>({
  get: () =>
    // Import is its own permission (F22 R2)
    route.query.mode === 'template' || (route.query.mode === 'import' && useCan().can('forms.import')) ? (route.query.mode as Mode) : 'blank',
  set: value => router.replace({ query: { ...route.query, mode: value === 'blank' ? undefined : value } }),
})
const tabs = computed(() => [
  { value: 'blank', label: t('forms.new.blank'), icon: 'i-lucide-file-plus' },
  { value: 'template', label: t('forms.new.template'), icon: 'i-lucide-layout-template' },
  ...(useCan().can('forms.import') ? [{ value: 'import', label: t('forms.new.import'), icon: 'i-lucide-file-json' }] : []),
])

const folders = ref<FormFolder[]>([])
const foldersLoading = ref(true)
onMounted(async () => {
  try {
    folders.value = (await api.get<FormFolder[]>('/folders', undefined, { background: true })).data
  } catch {
    // Folder stays "No folder".
  } finally {
    foldersLoading.value = false
  }
})
const NONE = '__none__'
// Opened from a folder page (F11 M4): that folder is preselected.
const folderId = ref(typeof route.query.folder === 'string' && route.query.folder ? route.query.folder : NONE)
const folderItems = computed(() => [
  { value: NONE, label: t('forms.noFolder'), icon: 'i-lucide-folder-minus' },
  ...folders.value.map(folder => ({ value: folder.id, label: folder.name, icon: 'i-lucide-folder' })),
])

// Import: the picked file, validated and parsed (FormsNewImport).
const imported = ref<{ name?: string; schema: FormSchemaV1 } | null>(null)
watch(imported, () => (nameTouched.value = false))

// ── Name (follows the chosen template until the user types their own) ─────────────
const name = ref('')
const nameTouched = ref(false)
const templateKey = ref<string>(
  systemTemplate(String(route.query.template ?? ''))?.key ?? 'customer_feedback',
)
watchEffect(() => {
  if (nameTouched.value) return
  name.value =
    mode.value === 'template'
      ? t(`templates.items.${templateKey.value}.name`)
      : mode.value === 'import'
        ? (imported.value?.name ?? '')
        : t('onboarding.firstForm.untitled')
})

// Where labels sit, a form-wide choice made up front (changeable later in Form settings).
const labelPosition = ref<'top' | 'left'>('top')
// The workspace's default for new forms (Settings → Form defaults)
onMounted(async () => {
  try {
    labelPosition.value = (await api.get<{ settings: { label_position: 'top' | 'left' } }>('/settings/form_defaults', undefined, { background: true })).data.settings.label_position
  } catch {
    // keep "top"
  }
})
const labelItems = computed(() => [
  { value: 'top', label: t('builder.labels.top'), icon: 'i-lucide-panel-top' },
  { value: 'left', label: t('builder.labels.left'), icon: 'i-lucide-panel-left' },
])

const canCreate = computed(() => !!name.value.trim() && (mode.value !== 'import' || !!imported.value))
const submitLabel = computed(() => (mode.value === 'import' ? t('forms.new.importSubmit') : t('forms.new.create')))
const detailsHint = computed(() =>
  mode.value === 'import' && !imported.value ? t('forms.new.pickFile') : t('forms.new.later'),
)

async function create() {
  if (!canCreate.value) return
  const folder = folderId.value === NONE ? null : folderId.value
  const created = await run(
    () =>
      mode.value === 'import'
        ? api.post<FormSummary>('/forms/import', {
            name: name.value.trim(),
            folder_id: folder,
            schema: {
              ...imported.value!.schema,
              settings: { ...imported.value!.schema.settings, label_position: labelPosition.value },
            },
          })
        : api.post<FormSummary>('/forms', {
            name: name.value.trim(),
            folder_id: folder,
            template_key: mode.value === 'template' ? templateKey.value : null,
            label_position: labelPosition.value,
            language: locale.value,
          }),
    { success: t('forms.toast.created') },
  )
  if (!created) return
  counts.refresh(true)
  await navigateTo({ path: `/forms/${created.data.id}/build`, query: forTemplate.value ? { save: 'template' } : undefined })
}
</script>

<template>
  <AppPanel
    id="forms-new"
    :title="forTemplate ? t('nav.newTemplate') : t('nav.newForm')"
    :subtitle="forTemplate ? t('forms.new.templateSubtitle') : t('forms.new.subtitle')"
    subtitle-icon="i-lucide-sparkles"
  >
    <template #actions>
      <UButton :label="t('common.cancel')" color="neutral" variant="outline" to="/forms" />
      <UButton
:label="submitLabel"
        :icon="mode === 'import' ? 'i-lucide-file-down' : 'i-lucide-plus'"
        color="neutral"
        :loading="busy"
        :disabled="!canCreate"
        @click="create"
      />
    </template>

    <div class="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <UTabs v-model="mode" :items="tabs" :content="false" color="neutral" variant="link" class="w-full" />
      <UAlert v-if="forTemplate" icon="i-lucide-bookmark-plus" color="neutral" variant="subtle" :title="t('forms.new.templateTitle')" :description="t('forms.new.templateHint')" />

      <form class="flex flex-col gap-6" @submit.prevent="create">
        <FormsNewBlankIntro v-if="mode === 'blank'" :name="name" />
        <FormsNewTemplatePicker v-if="mode === 'template'" v-model="templateKey" />

        <FormsNewImport v-if="mode === 'import'" v-model="imported" />

        <UCard
          :ui="{
            header: 'p-4 sm:px-6',
            body: 'p-4 sm:p-6',
            footer: 'flex flex-col-reverse gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-6',
          }"
        >
          <template #header>
            <h2 class="text-sm font-semibold text-highlighted">{{ t('forms.new.details') }}</h2>
            <p class="text-xs text-muted">{{ t('forms.new.detailsDesc') }}</p>
          </template>
          <div class="grid gap-5 sm:grid-cols-2">
            <UFormField :label="t('forms.new.name')" required>
              <UInput
                v-model="name"
                maxlength="120"
                size="lg"
                class="w-full"
                :disabled="mode === 'import' && !imported"
                @update:model-value="nameTouched = true"
              />
            </UFormField>
            <UFormField :label="t('forms.move.folder')">
              <template #label>
                <AppInfoLabel :label="t('forms.move.folder')" :info="t('forms.new.folderHint')" />
              </template>
              <USelectMenu
                v-model="folderId"
                :items="folderItems"
                value-key="value"
                :loading="foldersLoading"
                :search-input="{ placeholder: t('common.search') }"
                size="lg"
                class="w-full"
              />
            </UFormField>
            <UFormField :label="t('builder.labels.title')" :description="t('builder.labels.hint')" class="sm:col-span-2">
              <UTabs
                v-model="labelPosition"
                :items="labelItems"
                :content="false"
                color="neutral"
                size="sm"
                :ui="SEGMENTED_UI"
                :aria-label="t('builder.labels.title')"
              />
            </UFormField>
          </div>
          <template #footer>
            <p class="flex items-center gap-1.5 text-xs text-muted" aria-live="polite">
              <UIcon name="i-lucide-info" class="size-3.5 shrink-0" />{{ detailsHint }}
            </p>
            <UButton
              type="submit"
              :label="t('forms.new.continue')"
              trailing-icon="i-lucide-arrow-right"
              color="neutral"
              size="lg"
              :loading="busy"
              :disabled="!canCreate"
              :aria-label="`${t('forms.new.continue')}: ${submitLabel}`"
              class="justify-center sm:w-auto rtl:[&_svg]:rotate-180"
              block
            />
          </template>
        </UCard>
      </form>
    </div>
  </AppPanel>
</template>
