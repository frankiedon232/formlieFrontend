<!--
  Form overview → what the form is made of, each part linked to where it is edited: questions and
  pages (Build), rules and calculations (Logic), the look (Design, with a mini preview) and the
  published versions (Versions). Read only (not an editor, decision 97): the same numbers, no links.
-->
<script setup lang="ts">
import type { FormOverview, FormSummary } from '#shared/types/forms'

const props = defineProps<{ form: FormSummary; overview: FormOverview; readOnly?: boolean }>()
const { t } = useI18n()
const { relative } = useFormat()

const base = computed(() => `/forms/${props.form.id}`)
const parts = computed(() => [
  { key: 'questions', icon: 'i-lucide-list', value: props.overview.structure.fields, sub: t('forms.overview.pages', { count: props.overview.structure.pages }, props.overview.structure.pages), to: `${base.value}/build` },
  { key: 'logic', icon: 'i-lucide-git-branch', value: props.overview.structure.logic, sub: t('forms.overview.rules'), to: `${base.value}/logic` },
  { key: 'calculations', icon: 'i-lucide-calculator', value: props.overview.structure.calculations, sub: t('forms.overview.formulas'), to: `${base.value}/logic` },
])
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'p-4 sm:p-5' }">
    <h2 class="mb-3 text-sm font-semibold text-highlighted">{{ t('forms.overview.structureTitle') }}</h2>
    <div class="grid gap-3 sm:grid-cols-[minmax(0,1fr)_11rem]">
      <div class="grid grid-cols-3 gap-2">
        <template v-for="part in parts" :key="part.key">
          <div v-if="readOnly" class="flex flex-col gap-1 rounded-md border border-default p-3">
            <UIcon :name="part.icon" class="size-4 text-muted" />
            <span class="text-xl font-semibold text-highlighted tabular-nums">{{ part.value }}</span>
            <span class="truncate text-xs text-muted">{{ t(`forms.overview.part.${part.key}`) }}</span>
            <span class="truncate text-[11px] text-dimmed">{{ part.sub }}</span>
          </div>
          <NuxtLink
            v-else
            :to="form.deleted_at ? undefined : part.to"
            class="flex flex-col gap-1 rounded-md border border-default p-3 transition-colors hover:border-accented focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
          >
            <UIcon :name="part.icon" class="size-4 text-muted" />
            <span class="text-xl font-semibold text-highlighted tabular-nums">{{ part.value }}</span>
            <span class="truncate text-xs text-muted">{{ t(`forms.overview.part.${part.key}`) }}</span>
            <span class="truncate text-[11px] text-dimmed">{{ part.sub }}</span>
          </NuxtLink>
        </template>
      </div>
      <div v-if="readOnly" class="flex flex-col overflow-hidden rounded-md border border-default">
        <TemplatesThumb :theme="overview.theme" :title="form.name" :labels="overview.preview" compact />
        <span class="border-t border-default px-2.5 py-1.5 text-xs text-muted">{{ t('forms.overview.design') }}</span>
      </div>
      <NuxtLink
        v-else
        :to="form.deleted_at ? undefined : `${base}/design`"
        class="group/design flex flex-col overflow-hidden rounded-md border border-default transition-colors hover:border-accented focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
        :aria-label="t('forms.overview.editDesign')"
      >
        <TemplatesThumb :theme="overview.theme" :title="form.name" :labels="overview.preview" compact />
        <span class="flex items-center justify-between gap-1 border-t border-default px-2.5 py-1.5 text-xs text-muted">
          {{ t('forms.overview.design') }}
          <UIcon name="i-lucide-arrow-up-right" class="size-3.5" />
        </span>
      </NuxtLink>
    </div>

    <div class="mt-4 flex flex-col gap-2">
      <div class="flex items-center justify-between">
        <h3 class="text-xs font-medium text-muted uppercase">{{ t('forms.overview.versions') }}</h3>
        <UButton v-if="!readOnly" :label="t('forms.overview.allVersions')" color="neutral" variant="link" size="xs" :to="`${base}/versions`" trailing-icon="i-lucide-arrow-right" />
      </div>
      <ol v-if="overview.versions.length" class="flex flex-col">
        <li v-for="version in overview.versions" :key="version.id" class="flex items-center gap-3 border-s border-default py-1.5 ps-3">
          <UBadge :label="`v${version.number}`" color="neutral" variant="outline" size="sm" class="font-mono" />
          <span class="min-w-0 flex-1 truncate text-sm text-default">{{ version.published_by.name }}</span>
          <span class="shrink-0 text-xs text-muted">{{ relative(version.published_at) }}</span>
        </li>
      </ol>
      <p v-else class="text-sm text-muted">{{ form.status === 'draft' ? t('forms.overview.noVersions') : t('forms.overview.noHistory') }}</p>
    </div>
  </UCard>
</template>
