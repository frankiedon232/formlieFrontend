<!-- Grid card for a form (docs/design kanban card: date pill · ⋯ · title · subtitle · progress · footer). -->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { FormSummary } from '#shared/types/forms'

const props = defineProps<{ form: FormSummary; actions: DropdownMenuItem[][]; busy?: boolean }>()
const { t } = useI18n()
const { date, number } = useFormat()
</script>

<template>
  <UCard :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-4' }" class="h-full">
    <div class="flex items-center justify-between gap-2">
      <UBadge
        icon="i-lucide-clock"
        :label="t('forms.updatedOn', { date: date(props.form.updated_at) })"
        color="neutral"
        variant="outline"
        size="sm"
        class="rounded-md"
      />
      <UDropdownMenu :items="props.actions" :content="{ align: 'end' }">
        <UButton
          icon="i-lucide-ellipsis"
          color="neutral"
          variant="ghost"
          size="xs"
          square
          :aria-label="t('dataView.actions')"
        />
      </UDropdownMenu>
    </div>

    <div class="min-w-0">
      <div class="flex items-center gap-2">
        <DataStatusBadge :status="props.form.status" />
        <UIcon
          v-if="props.busy"
          name="i-lucide-loader-circle"
          class="size-4 shrink-0 animate-spin text-muted"
        />
        <h3 class="truncate font-semibold text-highlighted">
          <ULink :to="`/forms/${props.form.id}`" class="hover:underline">{{ props.form.name }}</ULink>
        </h3>
      </div>
      <p class="mt-1 truncate text-sm text-muted">{{ props.form.folder?.name ?? t('forms.noFolder') }}</p>
      <div v-if="props.form.tags.length" class="mt-2 flex flex-wrap gap-1">
        <UBadge
          v-for="tag in props.form.tags.slice(0, 4)"
          :key="tag"
          :label="tag"
          color="neutral"
          variant="outline"
          size="sm"
          class="rounded-md"
        />
      </div>
    </div>

    <div>
      <div class="mb-1.5 flex justify-between text-sm">
        <span class="text-muted">{{ t('forms.col.completion') }}</span>
        <span class="text-default">{{ props.form.completion_rate }}%</span>
      </div>
      <UProgress :model-value="props.form.completion_rate" color="neutral" size="sm" />
    </div>

    <div class="flex items-center justify-between border-t border-default pt-3 text-sm">
      <UAvatar :alt="props.form.owner.name" size="xs" />
      <span class="flex items-center gap-1 text-default">
        <UIcon name="i-lucide-inbox" class="size-4 text-muted" />
        {{ number(props.form.responses_count) }}
      </span>
    </div>
  </UCard>
</template>
