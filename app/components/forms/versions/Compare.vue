<!-- "Draft vs version N": added / changed / removed fields, page and rule count changes. -->
<script setup lang="ts">
import type { FormVersion } from '#shared/types/forms'
import { diffSchemas, type FormField } from '#shared/utils/forms/build'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'

const props = defineProps<{
  version: FormVersion | null
  before: FormSchemaV1 | null
  after: FormSchemaV1 | null
  loading: boolean
  versions: FormVersion[]
}>()
const emit = defineEmits<{ select: [id: string] }>()
const { t } = useI18n()

const diff = computed(() => (props.before && props.after ? diffSchemas(props.before, props.after) : null))
const groups = computed(() =>
  diff.value
    ? [
        { key: 'added', icon: 'i-lucide-plus', color: 'success' as const, tone: 'text-success', fields: diff.value.added },
        { key: 'changed', icon: 'i-lucide-pencil', color: 'warning' as const, tone: 'text-warning', fields: diff.value.changed },
        { key: 'removed', icon: 'i-lucide-minus', color: 'error' as const, tone: 'text-error', fields: diff.value.removed },
      ].filter(g => g.fields.length)
    : [],
)
const same = computed(() => diff.value && !groups.value.length && !diff.value.pages && !diff.value.rules)
const items = computed(() => props.versions.map(v => ({ value: v.id, label: t('versions.versionN', { n: v.number }) })))
const name = (f: FormField) => f.label?.trim() || t('builder.untitled')
const signed = (n: number) => (n > 0 ? `+${n}` : String(n))
</script>

<template>
  <UCard :ui="{ header: 'flex flex-wrap items-center gap-2 p-3 sm:px-4', body: 'p-3 sm:p-4' }">
    <template #header>
      <h2 class="text-sm font-semibold text-highlighted">{{ t('versions.compareTitle') }}</h2>
      <USelect
        v-if="versions.length"
        :model-value="version?.id"
        :items="items"
        size="sm"
        class="ms-auto w-36"
        :aria-label="t('versions.compareWith')"
        @update:model-value="v => emit('select', String(v))"
      />
    </template>

    <AppEmpty v-if="!versions.length && !loading" icon="i-lucide-git-compare" :title="t('versions.noneTitle')" :description="t('versions.noneDesc')" variant="naked" size="sm" />
    <div v-else-if="loading || !diff" class="flex flex-col gap-2" :aria-label="t('common.loading')">
      <USkeleton v-for="i in 4" :key="i" class="h-6 w-full" />
    </div>
    <div v-else class="flex flex-col gap-4" aria-live="polite">
      <p class="text-xs text-muted">{{ t('versions.compareDesc', { n: version?.number ?? '' }) }}</p>
      <p v-if="same" class="flex items-center gap-2 text-sm text-default">
        <UIcon name="i-lucide-circle-check" class="size-4 text-success" />{{ t('versions.same') }}
      </p>
      <section v-for="group in groups" :key="group.key" class="flex flex-col gap-1.5">
        <h3 class="flex items-center gap-2 text-xs font-medium text-muted uppercase">
          {{ t(`versions.diff.${group.key}`) }}
          <UBadge :label="String(group.fields.length)" :color="group.color" variant="subtle" size="sm" class="rounded-md" />
        </h3>
        <ul class="flex flex-col gap-1">
          <li v-for="field in group.fields" :key="field.id" class="flex min-w-0 items-center gap-2 text-sm">
            <UIcon :name="group.icon" class="size-3.5 shrink-0" :class="group.tone" />
            <UIcon :name="fieldIcon(field.type)" class="size-4 shrink-0 text-muted" />
            <span class="truncate">{{ name(field) }}</span>
          </li>
        </ul>
      </section>
      <div v-if="diff.pages || diff.rules" class="flex flex-wrap gap-2">
        <UBadge v-if="diff.pages" :label="t('versions.diff.pages', { n: signed(diff.pages) })" color="neutral" variant="outline" class="rounded-md" />
        <UBadge v-if="diff.rules" :label="t('versions.diff.rules', { n: signed(diff.rules) })" color="neutral" variant="outline" class="rounded-md" />
      </div>
    </div>
  </UCard>
</template>
