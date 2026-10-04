<!--
  Response panel header (F11): large avatar, name, email, number, form and status; a menu (copy a
  link to this response, delete for editors) and close; then the review bar, every status one
  click away (each with its colour, named), saved at once.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import { RESPONSE_STATUSES, type ResponseDetail, type ResponseStatus } from '#shared/types/responses'

const props = defineProps<{ response: ResponseDetail; busy: boolean }>()
const emit = defineEmits<{ status: [status: ResponseStatus]; delete: []; close: [] }>()
const { t } = useI18n()
const toast = useToast()
const { copy } = useClipboard({ legacy: true })

const name = computed(() => props.response.respondent.name || props.response.respondent.email || t('responses.anonymous'))
const statuses = computed(() => RESPONSE_STATUSES.map(value => ({ value, label: t(`status.${value}`) })))
const menu = computed<DropdownMenuItem[][]>(() => [
  [
    {
      label: t('responses.detail.copyLink'),
      icon: 'i-lucide-link',
      onSelect: () => {
        copy(`${location.origin}/forms/${props.response.form.id}/responses?response=${props.response.id}`)
        toast.add({ title: t('responses.detail.linkCopied'), color: 'success', icon: 'i-lucide-check' })
      },
    },
    { label: t('responses.list.allOfForm'), icon: 'i-lucide-table-2', to: `/forms/${props.response.form.id}/responses` },
  ],
  ...(props.response.can.edit ? [[{ label: t('responses.list.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => emit('delete') }]] : []),
])
</script>

<template>
  <div class="flex w-full flex-col gap-4">
    <div class="flex items-start gap-3.5">
      <UAvatar :alt="response.respondent.name || response.respondent.email || '?'" :icon="response.respondent.kind === 'anonymous' ? 'i-lucide-user-round' : undefined" size="2xl" class="ring-4 ring-(--ui-bg-elevated)" />
      <div class="flex min-w-0 flex-1 flex-col gap-1">
        <div class="flex min-w-0 items-center gap-1.5">
          <h2 class="truncate text-lg leading-tight font-semibold text-highlighted">{{ name }}</h2>
          <UTooltip v-if="response.respondent.kind === 'invite' || response.respondent.kind === 'member'" :text="t(`responses.known.${response.respondent.kind}`)">
            <UIcon name="i-lucide-badge-check" class="size-4 shrink-0 text-highlighted" :aria-label="t(`responses.known.${response.respondent.kind}`)" />
          </UTooltip>
        </div>
        <p v-if="response.respondent.name && response.respondent.email" class="truncate text-sm text-muted" dir="ltr">{{ response.respondent.email }}</p>
        <p v-else class="text-sm text-muted">{{ t(`responses.respondentKind.${response.respondent.kind}`) }}</p>
        <div class="mt-1 flex flex-wrap items-center gap-1.5">
          <UBadge :label="`#${response.number}`" color="neutral" variant="outline" size="sm" class="rounded-md font-mono" />
          <DataStatusBadge :status="response.status" />
          <UBadge :label="response.form.name" icon="i-lucide-file-text" color="neutral" variant="soft" size="sm" class="max-w-56 rounded-md" />
        </div>
      </div>
      <div class="flex shrink-0 items-center gap-1">
        <UDropdownMenu :items="menu" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="sm" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
        <UButton icon="i-lucide-x" color="neutral" variant="soft" size="sm" square class="rounded-full" :aria-label="t('common.close')" @click="emit('close')" />
      </div>
    </div>

    <!-- Review: one click per status -->
    <UTabs
      :model-value="response.status"
      :items="statuses"
      :content="false"
      color="neutral"
      size="sm"
      :ui="{ ...SEGMENTED_UI, root: 'w-full', list: `${SEGMENTED_UI.list} w-full`, trigger: `${SEGMENTED_UI.trigger} flex-1` }"
      :disabled="!response.can.review || busy"
      :aria-label="t('responses.list.status')"
      @update:model-value="value => emit('status', value as ResponseStatus)"
    >
      <template #leading="{ item }">
        <span class="size-2 shrink-0 rounded-full" :class="RESPONSE_STATUS_META[item.value as ResponseStatus].fill" />
      </template>
    </UTabs>
  </div>
</template>
