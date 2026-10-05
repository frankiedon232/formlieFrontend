<!--
  Grid card for a form, in the locked card format (owner 2026-10-04; docs/design 084447 task card,
  same structure as the response cards): an "updated" pill, status and ⋯ on top; the form name as
  the title (red flag = unpublished changes) with its folder; responses, availability, owner and
  access in two columns; a divider, then Completion with a black bar (drafts: not started); owner,
  link key and counts at the bottom. Same structure in every card so grid rows line up.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { FormSummary } from '#shared/types/forms'

const props = defineProps<{ form: FormSummary; actions: DropdownMenuItem[][]; busy?: boolean }>()
const { t } = useI18n()
const { relative, number, compact } = useFormat()
const draft = computed(() => props.form.status === 'draft')
const facts = computed(() => [
  { key: 'responses', label: t('forms.col.responses'), value: number(props.form.responses_count) },
  { key: 'availability', label: t('forms.col.availability'), value: null },
  { key: 'owner', label: t('forms.col.owner'), value: props.form.owner.name },
  { key: 'access', label: t('forms.card.access'), value: t(`share.access.${props.form.access ?? 'public'}`) },
])
</script>

<template>
  <article class="group flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md">
    <!-- Updated · status · menu -->
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon :name="busy ? 'i-lucide-loader-circle' : 'i-lucide-clock-3'" class="size-3.5 shrink-0 text-muted" :class="busy ? 'animate-spin' : ''" />
        <span class="truncate">{{ t('forms.card.updated', { when: relative(form.updated_at) }) }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <DataStatusBadge :status="form.status" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <!-- Name and folder -->
    <div class="mt-3 flex min-w-0 items-center gap-1.5">
      <UTooltip v-if="form.has_unpublished_changes" :text="t('forms.unpublished')">
        <UIcon name="i-lucide-flag" class="size-4 shrink-0 text-error" :aria-label="t('forms.unpublished')" />
      </UTooltip>
      <NuxtLink :to="`/forms/${form.id}`" class="truncate text-base font-semibold text-highlighted hover:underline focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">{{ form.name }}</NuxtLink>
    </div>
    <p class="flex min-w-0 items-center gap-1.5 text-sm text-muted">
      <UIcon name="i-lucide-folder" class="size-3.5 shrink-0" />
      <span class="truncate">{{ form.folder?.name ?? t('forms.noFolder') }}</span>
      <FormsStorageMark :storage="form.storage" />
    </p>

    <!-- Facts (two columns, one line each) -->
    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="flex h-5 min-w-0 items-center text-sm text-default">
          <FormsListAvailabilityBadge v-if="fact.key === 'availability' && form.status === 'published'" :form="form" />
          <span v-else-if="fact.key === 'availability'" class="text-dimmed">–</span>
          <span v-else class="truncate" :class="fact.key === 'responses' ? 'font-medium text-highlighted tabular-nums' : ''">{{ fact.value }}</span>
        </dd>
      </div>
    </dl>

    <!-- Completion (the design's Progress) -->
    <div class="mt-auto pt-4">
      <div class="border-t border-default pt-3">
        <div class="mb-1.5 flex items-center justify-between text-xs">
          <span class="text-muted">{{ t('forms.col.completion') }}</span>
          <span class="font-medium text-highlighted tabular-nums">{{ draft ? t('forms.notStarted') : `${form.completion_rate}%` }}</span>
        </div>
        <div class="h-1.5 overflow-hidden rounded-full bg-elevated" role="presentation">
          <div class="h-full rounded-full bg-inverted" :style="{ width: `${draft ? 0 : form.completion_rate}%` }" />
        </div>
      </div>

      <!-- Owner, key, counts -->
      <div class="mt-4 flex items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-2">
          <UAvatar :alt="form.owner.name" size="xs" />
          <span class="truncate font-mono text-xs text-muted">{{ form.custom_link || form.public_key }}</span>
        </div>
        <div class="flex shrink-0 items-center gap-3 text-xs text-muted">
          <UTooltip :text="form.tags.join(', ') || t('forms.card.noTags')">
            <span class="flex items-center gap-1" :class="form.tags.length ? 'text-toned' : ''"><UIcon name="i-lucide-tag" class="size-3.5" />{{ form.tags.length }}</span>
          </UTooltip>
          <span class="flex items-center gap-1" :class="form.responses_count ? 'text-toned' : ''"><UIcon name="i-lucide-inbox" class="size-3.5" />{{ compact(form.responses_count) }}</span>
        </div>
      </div>
    </div>
  </article>
</template>
