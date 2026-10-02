<!--
  New form (F6): blank · from a starter template · import a JSON export (FormSchema v1, validated
  and previewed before anything is created). `?mode=template|import` and `?template=<key>` preselect.
-->
<script setup lang="ts">
import type { FormFolder, FormSummary } from '#shared/types/forms'
import { STARTER_TEMPLATES, type StarterTemplateKey } from '#shared/utils/templates/starters'
import { countFields, formImportFile, MAX_IMPORT_BYTES, type FormSchemaV1 } from '#shared/utils/forms/schema'

definePageMeta({ breadcrumb: 'nav.newForm' })

const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const counts = useNavCounts()
const { busy, run } = useBusy()
useHead({ title: () => t('nav.newForm') })

type Mode = 'blank' | 'template' | 'import'
const mode = computed<Mode>({
  get: () => (['template', 'import'].includes(String(route.query.mode)) ? (route.query.mode as Mode) : 'blank'),
  set: value => router.replace({ query: { ...route.query, mode: value === 'blank' ? undefined : value } }),
})
const tabs = computed(() => [
  { value: 'blank', label: t('forms.new.blank'), icon: 'i-lucide-file-plus' },
  { value: 'template', label: t('forms.new.template'), icon: 'i-lucide-layout-template' },
  { value: 'import', label: t('forms.new.import'), icon: 'i-lucide-file-json' },
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
const folderId = ref(NONE)
const folderItems = computed(() => [
  { value: NONE, label: t('forms.noFolder'), icon: 'i-lucide-folder-minus' },
  ...folders.value.map(folder => ({ value: folder.id, label: folder.name, icon: 'i-lucide-folder' })),
])

// ── Import ────────────────────────────────────────────────────────────────────────
const file = ref<File | null>(null)
const reading = ref(false)
const importError = ref<string | null>(null)
const imported = ref<{ name?: string; schema: FormSchemaV1 } | null>(null)

watch(file, async picked => {
  imported.value = null
  importError.value = null
  if (!picked) return
  if (picked.size > MAX_IMPORT_BYTES) return (importError.value = t('forms.new.tooBig'))
  reading.value = true
  try {
    const raw: unknown = JSON.parse(await picked.text())
    const parsed = formImportFile.safeParse(raw)
    if (!parsed.success) {
      // A union reports one wrapper issue; use the branch that matches the file's shape
      // (`{ name, schema }` export vs a bare schema) so the path points at the real problem.
      const issue = parsed.error.issues[0]
      const wrapped = !!raw && typeof raw === 'object' && 'schema' in raw
      const inner = issue?.code === 'invalid_union' ? issue.errors[wrapped ? 0 : 1]?.[0] : issue
      importError.value = t('forms.new.invalid', { detail: inner?.path.join('.') || '—' })
      return
    }
    imported.value = parsed.data
    nameTouched.value = false
  } catch {
    importError.value = t('forms.new.notJson')
  } finally {
    reading.value = false
  }
})

// ── Name (follows the chosen template until the user types their own) ─────────────
const name = ref('')
const nameTouched = ref(false)
const templateKey = ref<StarterTemplateKey>(
  (STARTER_TEMPLATES.find(item => item.key === route.query.template)?.key ?? 'customer_feedback') as StarterTemplateKey,
)
const templates = computed(() =>
  STARTER_TEMPLATES.map(item => ({
    value: item.key,
    label: t(`templates.starter.${item.key}.name`),
    description: t('onboarding.firstForm.fields', { count: item.fields }, item.fields),
    iconName: item.icon,
  })),
)
watchEffect(() => {
  if (nameTouched.value) return
  name.value =
    mode.value === 'template'
      ? t(`templates.starter.${templateKey.value}.name`)
      : mode.value === 'import'
        ? (imported.value?.name ?? '')
        : t('onboarding.firstForm.untitled')
})

const canCreate = computed(() => !!name.value.trim() && (mode.value !== 'import' || !!imported.value))

async function create() {
  if (!canCreate.value) return
  const folder = folderId.value === NONE ? null : folderId.value
  const created = await run(
    () =>
      mode.value === 'import'
        ? api.post<FormSummary>('/forms/import', { name: name.value.trim(), folder_id: folder, schema: imported.value!.schema })
        : api.post<FormSummary>('/forms', {
            name: name.value.trim(),
            folder_id: folder,
            template_key: mode.value === 'template' ? templateKey.value : null,
          }),
    { success: t('forms.toast.created') },
  )
  if (!created) return
  counts.refresh(true)
  await navigateTo(`/forms/${created.data.id}`)
}
</script>

<template>
  <AppPanel id="forms-new" :title="t('nav.newForm')" :subtitle="t('forms.new.subtitle')" subtitle-icon="i-lucide-sparkles">
    <template #actions>
      <UButton :label="t('common.cancel')" color="neutral" variant="outline" to="/forms" />
      <UButton
        :label="mode === 'import' ? t('forms.new.importSubmit') : t('forms.new.create')"
        :icon="mode === 'import' ? 'i-lucide-file-down' : 'i-lucide-plus'"
        color="neutral"
        :loading="busy"
        :disabled="!canCreate"
        @click="create"
      />
    </template>

    <div class="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <UTabs v-model="mode" :items="tabs" :content="false" color="neutral" variant="link" class="w-full" />

      <form class="flex flex-col gap-6" @submit.prevent="create">
        <div v-if="mode === 'template'">
          <URadioGroup
            v-model="templateKey"
            :items="templates"
            variant="card"
            color="neutral"
            indicator="hidden"
            :aria-label="t('forms.new.template')"
            :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2', item: 'items-start', wrapper: 'w-full items-start text-start' }"
          >
            <template #label="{ item }">
              <span class="flex items-center gap-3">
                <span class="flex size-9 shrink-0 items-center justify-center rounded-md border border-default bg-elevated/50">
                  <UIcon :name="item.iconName" class="size-4 text-highlighted" />
                </span>
                <span class="font-medium text-highlighted">{{ item.label }}</span>
              </span>
            </template>
            <template #description="{ item }">
              <span class="ms-12 block text-xs text-muted">{{ item.description }}</span>
            </template>
          </URadioGroup>
        </div>

        <div v-if="mode === 'import'" class="flex flex-col gap-3">
          <UFileUpload
            v-model="file"
            accept="application/json,.json"
            :label="t('forms.new.drop')"
            :description="t('forms.new.dropHint')"
            icon="i-lucide-file-json"
            color="neutral"
            layout="list"
            class="min-h-36 w-full"
          />
          <p v-if="reading" class="flex items-center gap-2 text-sm text-muted" aria-live="polite">
            <UIcon name="i-lucide-loader-circle" class="size-4 animate-spin" /> {{ t('forms.new.reading') }}
          </p>
          <UAlert v-if="importError" icon="i-lucide-file-x" color="error" variant="subtle" :title="importError" />
          <UAlert
            v-if="imported"
            icon="i-lucide-file-check"
            color="success"
            variant="subtle"
            :title="t('forms.new.ready')"
            :description="
              t('forms.new.summary', {
                pages: imported.schema.pages.length,
                fields: countFields(imported.schema),
              })
            "
          />
        </div>

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
        </div>
        <button type="submit" class="hidden" tabindex="-1" aria-hidden="true" />
      </form>
    </div>
  </AppPanel>
</template>
