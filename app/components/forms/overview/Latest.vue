<!--
  Form overview → the latest responses (rule 21 card model): the four newest as response cards in
  two columns; a card opens that response in the Responses page panel. Empty: a clear next step.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ResponseRow } from '#shared/types/responses'
import { allFields } from '#shared/utils/forms/build'
import { isInputField } from '#shared/utils/forms/fields'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'

const props = defineProps<{ formId: string; schema: FormSchemaV1 | null; published: boolean }>()
const { t } = useI18n()
const api = useApi()

const rows = ref<ResponseRow[] | null>(null)
onMounted(async () => {
  try {
    rows.value = (await api.list<ResponseRow>(`/forms/${props.formId}/responses`, { page_size: 4, sort: '-submitted_at' }, { background: true })).data
  } catch {
    rows.value = []
  }
})
const fields = computed(() => (props.schema ? allFields(props.schema).filter(field => isInputField(field.type) && goodColumn(field)).slice(0, 2) : []))
const link = (row: ResponseRow) => `/forms/${props.formId}/responses?response=${row.id}`
const actions = (row: ResponseRow): DropdownMenuItem[][] => [
  [
    { label: t('responses.list.open'), icon: 'i-lucide-panel-right-open', to: link(row) },
    { label: t('responses.list.allOfForm'), icon: 'i-lucide-table-2', to: `/forms/${props.formId}/responses` },
  ],
]
function open(event: MouseEvent, row: ResponseRow) {
  if ((event.target as HTMLElement).closest('a, button, [role="menu"], [role="menuitem"]')) return
  void navigateTo(link(row))
}
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex items-center justify-between gap-2">
      <h2 class="text-sm font-semibold text-highlighted">{{ t('forms.overview.latest') }}</h2>
      <UButton :label="t('forms.overview.allResponses')" trailing-icon="i-lucide-arrow-right" color="neutral" variant="link" size="xs" :to="`/forms/${formId}/responses`" class="rtl:[&_svg]:rotate-180" />
    </div>
    <div v-if="rows === null" class="grid gap-3 sm:grid-cols-2">
      <USkeleton v-for="n in 2" :key="n" class="h-56 rounded-lg" />
    </div>
    <UEmpty
      v-else-if="!rows.length"
      icon="i-lucide-inbox"
      :title="t('responses.list.empty')"
      :description="published ? t('forms.overview.noResponsesYet') : t('forms.overview.publishFirst')"
      :actions="[{ label: published ? t('forms.overview.shareForm') : t('forms.detail.edit'), icon: published ? 'i-lucide-share-2' : 'i-lucide-pencil-ruler', color: 'neutral', variant: 'outline', to: published ? `/forms/${formId}/share` : `/forms/${formId}/build` }]"
      variant="naked"
    />
    <div v-else class="grid gap-3 sm:grid-cols-2">
      <div v-for="row in rows" :key="row.id" class="h-full cursor-pointer" @click="open($event, row)">
        <FormsResponsesCard :row="row" :fields="fields" :actions="actions(row)" @open="navigateTo(link(row))" />
      </div>
    </div>
  </UCard>
</template>
