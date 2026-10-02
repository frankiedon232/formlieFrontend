<!--
  Form overview (F6) — where a new or opened form lands until the builder (F7) takes over this
  route's "Edit" action: status, details, lifecycle actions and the form's activity.
-->
<script setup lang="ts">
import type { FormSummary } from '#shared/types/forms'

const { t } = useI18n()
const route = useRoute()
const api = useApi()
const { setLabel } = useBreadcrumbs()
const { dateTime, relative, number } = useFormat()
const { handle } = useErrorHandler()

const form = ref<(FormSummary & { template_key: string | null }) | null>(null)
const loading = ref(true)
const notFound = ref(false)
useHead({ title: () => form.value?.name ?? t('nav.forms') })

async function load() {
  try {
    form.value = (
      await api.get<FormSummary & { template_key: string | null }>(`/forms/${route.params.id}`)
    ).data
    setLabel(route.path, form.value.name)
  } catch (error) {
    const normalised = handle(error, { silent: true })
    if (normalised.code === 'FRM-GEN-1004') notFound.value = true
    else handle(error)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const actions = useFormActions(load)
const busy = computed(() => !!form.value && actions.isBusy(form.value))
const menu = useFormMenu(actions, {
  rename: () => {},
  move: () => {},
  tags: () => {},
})
// Overview: lifecycle + delete only (rename / move / tags live in the list for now).
const lifecycleItems = computed(() => {
  if (!form.value) return []
  if (form.value.deleted_at)
    return [
      [
        {
          label: t('forms.actions.restore'),
          icon: 'i-lucide-undo-2',
          onSelect: () => actions.lifecycle(form.value!, 'restore'),
        },
      ],
    ]
  return menu(form.value).slice(2)
})
const canSeeActivity = computed(() => useSession().user.value?.role !== 'member')

const details = computed(() =>
  form.value
    ? [
        { label: t('forms.col.status'), value: t(`status.${form.value.status}`) },
        { label: t('forms.move.folder'), value: form.value.folder?.name ?? t('forms.noFolder') },
        { label: t('forms.col.owner'), value: form.value.owner.name },
        { label: t('forms.col.responses'), value: number(form.value.responses_count) },
        { label: t('forms.detail.created'), value: dateTime(form.value.created_at) },
        {
          label: t('forms.col.updated'),
          value: `${relative(form.value.updated_at)} · ${dateTime(form.value.updated_at)}`,
        },
        {
          label: t('forms.detail.source'),
          value: form.value.template_key
            ? t(`templates.starter.${form.value.template_key}.name`)
            : t('forms.detail.blank'),
        },
      ]
    : [],
)
</script>

<template>
  <AppPanel
    id="form-overview"
    :title="form?.name ?? t('nav.forms')"
    :subtitle="form ? `/f/${form.slug}` : undefined"
    subtitle-icon="i-lucide-link"
  >
    <template v-if="form" #actions>
      <UDropdownMenu :items="lifecycleItems" :content="{ align: 'end' }">
        <UButton
          icon="i-lucide-ellipsis"
          :label="t('dataView.actions')"
          color="neutral"
          variant="outline"
          :loading="busy"
        />
      </UDropdownMenu>
      <UButton
        icon="i-lucide-pencil-ruler"
        :label="t('forms.detail.edit')"
        color="neutral"
        :to="`/forms/${form.id}/build`"
        :disabled="!!form.deleted_at"
      />
    </template>

    <div
      v-if="loading"
      class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]"
      :aria-label="t('common.loading')"
    >
      <USkeleton class="h-72 w-full" />
      <USkeleton class="h-72 w-full" />
    </div>

    <UEmpty
      v-else-if="notFound"
      icon="i-lucide-file-question"
      :title="t('forms.detail.notFound')"
      :description="t('forms.detail.notFoundDesc')"
      :actions="[{ label: t('nav.forms'), to: '/forms', color: 'neutral', icon: 'i-lucide-arrow-left' }]"
      variant="outline"
    />

    <div
      v-else-if="form"
      class="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]"
      :class="busy ? 'pointer-events-none opacity-60' : ''"
      :aria-busy="busy || undefined"
    >
      <div class="flex flex-col gap-6">
        <UAlert
          v-if="form.deleted_at"
          icon="i-lucide-trash-2"
          color="warning"
          variant="subtle"
          :title="t('forms.detail.inTrash')"
          :actions="[
            { label: t('forms.trash.title'), to: '/forms/trash', color: 'neutral', variant: 'outline' },
          ]"
        />
        <UCard :ui="{ body: 'p-0 sm:p-0' }">
          <dl class="divide-y divide-default">
            <div v-for="row in details" :key="row.label" class="grid gap-1 px-4 py-3 sm:grid-cols-3 sm:gap-4">
              <dt class="text-sm text-muted">{{ row.label }}</dt>
              <dd class="text-sm text-highlighted sm:col-span-2">{{ row.value }}</dd>
            </div>
          </dl>
        </UCard>
        <UEmpty
          icon="i-lucide-pencil-ruler"
          :title="t('forms.detail.openBuilder')"
          :description="t('forms.detail.openBuilderDesc')"
          :actions="
            form.deleted_at
              ? []
              : [
                  {
                    label: t('forms.detail.edit'),
                    icon: 'i-lucide-pencil-ruler',
                    color: 'neutral',
                    to: `/forms/${form.id}/build`,
                  },
                ]
          "
          variant="outline"
        />
      </div>

      <UCard v-if="canSeeActivity" :ui="{ body: 'p-4 sm:p-5' }">
        <h2 class="mb-4 text-sm font-semibold text-highlighted">{{ t('forms.detail.activity') }}</h2>
        <AuditTimeline
          :key="form.row_version"
          :filters="{ 'filter[resource_id]': form.id }"
          :limit="8"
          :view-all="`/audit?q=${encodeURIComponent(form.name)}`"
        />
      </UCard>
    </div>
  </AppPanel>
</template>
