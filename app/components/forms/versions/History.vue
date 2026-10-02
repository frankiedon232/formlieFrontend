<!--
  Versions body: timeline of the draft + published versions, and the compare card. Loads the
  list itself (with skeletons) and each version's schema on demand (cached).
-->
<script setup lang="ts">
import type { FormVersion } from '#shared/types/forms'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'

const props = defineProps<{ session: BuilderSession }>()
const { t } = useI18n()
const api = useApi()
const confirm = useConfirm()
const { handle } = useErrorHandler()
const { dateTime, relative } = useFormat()
const { form, builder } = props.session

const versions = ref<FormVersion[]>([])
const loading = ref(true)
const failed = ref(false)
async function load() {
  loading.value = true
  failed.value = false
  try {
    versions.value = (await api.get<FormVersion[]>(`/forms/${props.session.formId}/versions`)).data
    compareId.value ??= versions.value[0]?.id ?? null
  } catch (error) {
    failed.value = true
    handle(error)
  } finally {
    loading.value = false
  }
}
onMounted(load)

// Version schemas, fetched once each.
const schemas = shallowRef(new Map<string, FormSchemaV1>())
const fetching = ref<string | null>(null)
async function schemaOf(id: string): Promise<FormSchemaV1 | null> {
  const cached = schemas.value.get(id)
  if (cached) return cached
  fetching.value = id
  try {
    const { data } = await api.get<FormVersion & { schema: FormSchemaV1 }>(`/forms/${props.session.formId}/versions/${id}`)
    schemas.value = new Map(schemas.value).set(id, data.schema)
    return data.schema
  } catch (error) {
    handle(error)
    return null
  } finally {
    fetching.value = null
  }
}

const compareId = ref<string | null>(null)
watch(compareId, id => id && schemaOf(id))
const compared = computed(() => versions.value.find(v => v.id === compareId.value) ?? null)

const preview = ref<{ title: string; schema: FormSchemaV1 } | null>(null)
const previewOpen = ref(false)
async function view(version: FormVersion) {
  const schema = await schemaOf(version.id)
  if (!schema) return
  preview.value = { title: t('versions.versionN', { n: version.number }), schema }
  previewOpen.value = true
}

const restoring = ref<string | null>(null)
async function restore(version: FormVersion) {
  const ok = await confirm({
    title: t('versions.restoreTitle', { n: version.number }),
    description: t('versions.restoreDesc'),
    confirmLabel: t('versions.restore'),
  })
  if (!ok) return
  restoring.value = version.id
  try {
    await props.session.replaceDraft(`/forms/${props.session.formId}/versions/${version.id}/restore`, t('versions.restored', { n: version.number }))
  } finally {
    restoring.value = null
  }
}

async function discard() {
  const ok = await confirm({ title: t('versions.discardTitle'), description: t('versions.discardDesc'), confirmLabel: t('versions.discard'), danger: true })
  if (ok) await props.session.replaceDraft(`/forms/${props.session.formId}/discard`, t('versions.discarded'))
}

const live = computed(() => (form.value?.status === 'published' ? versions.value[0]?.id : null))
const hasDraftChanges = computed(() => !versions.value.length || !!form.value?.has_unpublished_changes)
</script>

<template>
  <div class="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_380px]">
    <UCard :ui="{ header: 'flex items-center gap-2 p-3 sm:px-4', body: 'p-3 sm:p-4' }">
      <template #header>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('versions.title') }}</h2>
        <UBadge :label="String(versions.length)" color="neutral" variant="outline" size="sm" class="rounded-md" />
      </template>

      <div v-if="loading" class="flex flex-col gap-4" :aria-label="t('common.loading')">
        <USkeleton v-for="i in 3" :key="i" class="h-14 w-full" />
      </div>
      <UEmpty
        v-else-if="failed"
        icon="i-lucide-cloud-alert"
        :title="t('dataView.errorTitle')"
        :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: load }]"
        variant="naked"
      />
      <ol v-else class="flex flex-col">
        <!-- The draft sits on top of the timeline. -->
        <FormsVersionsEntry
          :title="t('versions.draft')"
          :meta="hasDraftChanges ? t('versions.draftChanged') : t('versions.draftSame')"
          :when="form ? relative(form.updated_at) : ''"
          icon="i-lucide-pencil"
          current
          :last="!versions.length"
        >
          <template #badges>
            <UBadge v-if="hasDraftChanges" :label="t('builder.unpublished')" color="warning" variant="subtle" size="sm" class="rounded-md" />
          </template>
          <UButton
            v-if="versions.length && form?.has_unpublished_changes"
            icon="i-lucide-undo-2"
            :label="t('versions.discard')"
            color="neutral"
            variant="outline"
            size="sm"
            :loading="session.publishing.value && !restoring"
            @click="discard"
          />
        </FormsVersionsEntry>

        <FormsVersionsEntry
          v-for="(version, i) in versions"
          :key="version.id"
          :title="t('versions.versionN', { n: version.number })"
          :summary="version.change_summary"
          :meta="t('versions.by', { name: version.published_by.name, count: version.fields_count })"
          :when="dateTime(version.published_at)"
          icon="i-lucide-globe"
          :selected="compareId === version.id"
          :last="i === versions.length - 1"
        >
          <template #badges>
            <UBadge v-if="live === version.id" :label="t('versions.live')" color="success" variant="subtle" size="sm" class="rounded-md" />
          </template>
          <UButton
            icon="i-lucide-arrow-up-right"
            :label="t('versions.view')"
            color="neutral"
            variant="outline"
            size="sm"
            :loading="fetching === version.id && !previewOpen"
            @click="view(version)"
          />
          <UButton
            icon="i-lucide-git-compare"
            :label="t('versions.compare')"
            color="neutral"
            :variant="compareId === version.id ? 'solid' : 'outline'"
            size="sm"
            :aria-pressed="compareId === version.id"
            class="lg:hidden xl:inline-flex"
            @click="compareId = version.id"
          />
          <UButton
            icon="i-lucide-history"
            :label="t('versions.restore')"
            color="neutral"
            variant="outline"
            size="sm"
            :loading="restoring === version.id"
            :disabled="!!restoring"
            @click="restore(version)"
          />
        </FormsVersionsEntry>
      </ol>
    </UCard>

    <FormsVersionsCompare
      class="lg:sticky lg:top-0"
      :version="compared"
      :before="compareId ? (schemas.get(compareId) ?? null) : null"
      :after="builder.schema.value"
      :loading="loading || (!!compareId && !schemas.get(compareId))"
      :versions="versions"
      @select="id => (compareId = id)"
    />

    <LazyFormsBuilderPreviewModal v-if="preview" v-model:open="previewOpen" :schema="preview?.schema" :title="preview?.title" />
  </div>
</template>
