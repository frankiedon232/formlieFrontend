<!--
  Gallery card (F9): the template's own design in miniature, name, category, what it holds
  (questions, minutes, calculations, logic) and how often it was used. The whole card opens the
  template page; "Use" starts a form straight away.
-->
<script setup lang="ts">
import type { TemplateSummary } from '#shared/types/templates'
import { categoryOf } from '#shared/templates/categories'

const props = defineProps<{ template: TemplateSummary; busy?: boolean }>()
const emit = defineEmits<{ use: [template: TemplateSummary] }>()
const { t } = useI18n()
const { compact } = useFormat()
const category = computed(() => categoryOf(props.template.category))
</script>

<template>
  <article class="group/card relative flex h-full flex-col overflow-hidden rounded-lg border border-default bg-default transition-colors hover:border-accented">
    <TemplatesThumb :theme="template.theme" :title="template.name" :labels="template.preview" />
    <div class="flex flex-1 flex-col gap-2 border-t border-default p-3">
      <div class="flex items-start gap-2">
        <UIcon :name="template.icon" class="mt-0.5 size-4 shrink-0 text-muted" />
        <NuxtLink
          :to="`/templates/${template.key}`"
          class="min-w-0 flex-1 font-medium text-highlighted after:absolute after:inset-0 focus-visible:outline-none after:focus-visible:rounded-lg after:focus-visible:outline-2 after:focus-visible:outline-(--ui-border-inverted)"
        >
          <span class="line-clamp-2">{{ template.name }}</span>
        </NuxtLink>
        <UIcon v-if="busy" name="i-lucide-loader-circle" class="size-4 shrink-0 animate-spin text-muted" />
      </div>
      <p class="line-clamp-2 text-xs text-muted">{{ template.description }}</p>
      <div class="mt-auto flex flex-wrap items-center gap-1.5 pt-1">
        <UBadge color="neutral" variant="outline" size="sm" class="gap-1.5">
          <span class="size-2 rounded-[1px]" :class="category?.dot" aria-hidden="true" />
          {{ t(`templates.categories.${template.category}`) }}
        </UBadge>
        <UBadge v-if="template.calculations_count" :label="t('templates.badge.calculations')" icon="i-lucide-calculator" color="neutral" variant="soft" size="sm" />
        <UBadge v-if="template.logic_count" :label="t('templates.badge.logic')" icon="i-lucide-git-branch" color="neutral" variant="soft" size="sm" />
        <UBadge v-if="template.source === 'workspace'" :label="t('templates.badge.workspace')" icon="i-lucide-building-2" color="neutral" variant="soft" size="sm" />
      </div>
      <div class="flex items-center justify-between gap-2 text-xs text-muted">
        <span class="flex items-center gap-3">
          <span class="flex items-center gap-1"><UIcon name="i-lucide-list" class="size-3.5" />{{ t('templates.questions', { count: template.fields_count }, template.fields_count) }}</span>
          <span class="flex items-center gap-1"><UIcon name="i-lucide-timer" class="size-3.5" />{{ t('templates.minutes', { n: template.minutes }) }}</span>
        </span>
        <span class="flex items-center gap-1" :title="t('templates.usedTitle')">
          <UIcon name="i-lucide-file-text" class="size-3.5" />{{ compact(template.forms_count) }}
        </span>
      </div>
      <UButton
        :label="t('templates.use')"
        icon="i-lucide-file-plus"
        color="neutral"
        variant="outline"
        size="sm"
        block
        class="relative z-10"
        :disabled="busy"
        @click="emit('use', template)"
      />
    </div>
  </article>
</template>
