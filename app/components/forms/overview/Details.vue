<!-- Form overview → details: status, owner, folder, tags, where it came from (template link), dates. -->
<script setup lang="ts">
import type { FormOverview, FormSummary } from '#shared/types/forms'

defineProps<{ form: FormSummary; template: FormOverview['template'] }>()
const emit = defineEmits<{ availability: [] }>()
const { t } = useI18n()
const { dateTime, relative } = useFormat()
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'p-4 sm:p-5' }">
    <h2 class="mb-3 text-sm font-semibold text-highlighted">{{ t('forms.overview.detailsTitle') }}</h2>
    <dl class="flex flex-col gap-3 text-sm">
      <div class="flex items-center justify-between gap-3">
        <dt class="text-muted">{{ t('forms.col.status') }}</dt>
        <dd><DataStatusBadge :status="form.status" /></dd>
      </div>
      <div class="flex items-center justify-between gap-3">
        <dt class="text-muted">{{ t('forms.col.availability') }}</dt>
        <dd class="flex items-center gap-1.5">
          <FormsListAvailabilityBadge v-if="form.status === 'published'" :form="form" />
          <span v-else class="text-highlighted">{{ form.opens_at || form.closes_at ? t('forms.availability.set') : t('forms.availability.notSet') }}</span>
          <UButton icon="i-lucide-pencil" color="neutral" variant="ghost" size="xs" :aria-label="t('forms.availability.menu')" :disabled="!!form.deleted_at" @click="emit('availability')" />
        </dd>
      </div>
      <div class="flex items-center justify-between gap-3">
        <dt class="text-muted">{{ t('forms.col.owner') }}</dt>
        <dd class="flex min-w-0 items-center gap-2">
          <UAvatar :alt="form.owner.name" size="2xs" />
          <span class="truncate text-highlighted">{{ form.owner.name }}</span>
        </dd>
      </div>
      <div class="flex items-center justify-between gap-3">
        <dt class="text-muted">{{ t('forms.move.folder') }}</dt>
        <dd class="flex min-w-0 items-center gap-1.5 text-highlighted">
          <UIcon :name="form.folder ? 'i-lucide-folder' : 'i-lucide-folder-minus'" class="size-4 shrink-0 text-muted" />
          <span class="truncate">{{ form.folder?.name ?? t('forms.noFolder') }}</span>
        </dd>
      </div>
      <div class="flex items-start justify-between gap-3">
        <dt class="text-muted">{{ t('forms.overview.tags') }}</dt>
        <dd class="flex flex-wrap justify-end gap-1">
          <UBadge v-for="tag in form.tags" :key="tag" :label="tag" color="neutral" variant="soft" size="sm" />
          <span v-if="!form.tags.length" class="text-muted">-</span>
        </dd>
      </div>
      <div class="flex items-center justify-between gap-3">
        <dt class="text-muted">{{ t('forms.detail.source') }}</dt>
        <dd class="min-w-0 truncate">
          <NuxtLink v-if="template" :to="`/templates/${template.key}`" class="flex items-center gap-1 text-highlighted hover:underline">
            <UIcon name="i-lucide-layout-template" class="size-4 shrink-0 text-muted" />
            <span class="truncate">{{ template.name }}</span>
          </NuxtLink>
          <span v-else class="text-highlighted">{{ t('forms.detail.blank') }}</span>
        </dd>
      </div>
      <USeparator />
      <div class="flex items-center justify-between gap-3">
        <dt class="text-muted">{{ t('forms.detail.created') }}</dt>
        <dd class="text-highlighted" :title="dateTime(form.created_at)">{{ relative(form.created_at) }}</dd>
      </div>
      <div class="flex items-center justify-between gap-3">
        <dt class="text-muted">{{ t('forms.col.updated') }}</dt>
        <dd class="text-highlighted" :title="dateTime(form.updated_at)">{{ relative(form.updated_at) }}</dd>
      </div>
    </dl>
  </UCard>
</template>
