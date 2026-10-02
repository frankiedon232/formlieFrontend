<!--
  Blank tab of "New form": a small live preview of the empty form (shows the name as you type)
  beside what a blank form starts with. Decorative preview is hidden from screen readers.
-->
<script setup lang="ts">
defineProps<{ name: string }>()
const { t } = useI18n()

const points = computed(() => [
  { icon: 'i-lucide-blocks', title: t('forms.new.points.fieldsTitle'), text: t('forms.new.points.fieldsText') },
  { icon: 'i-lucide-git-branch', title: t('forms.new.points.logicTitle'), text: t('forms.new.points.logicText') },
  { icon: 'i-lucide-cloud-check', title: t('forms.new.points.saveTitle'), text: t('forms.new.points.saveText') },
])
</script>

<template>
  <UCard :ui="{ body: 'p-0 sm:p-0' }">
    <div class="grid md:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
      <div class="hidden border-b border-default bg-elevated/40 p-4 sm:block sm:p-6 md:border-e md:border-b-0" aria-hidden="true">
        <div class="flex flex-col gap-4 rounded-lg border border-default bg-default p-4 shadow-xs">
          <div class="flex items-center justify-between gap-2">
            <span class="rounded-md border border-default px-2 py-0.5 text-xs text-muted">
              {{ t('builder.page.default', { n: 1 }) }}
            </span>
            <span class="flex gap-1">
              <span class="size-1.5 rounded-full bg-accented" />
              <span class="size-1.5 rounded-full bg-accented" />
              <span class="size-1.5 rounded-full bg-accented" />
            </span>
          </div>
          <p class="truncate text-base font-semibold text-highlighted">
            {{ name.trim() || t('onboarding.firstForm.untitled') }}
          </p>
          <div class="flex flex-col gap-2">
            <span class="h-2 w-24 rounded-full bg-accented" />
            <span class="h-8 w-full rounded-md border border-default" />
          </div>
          <div
            class="flex items-center justify-center gap-2 rounded-md border border-dashed border-accented py-5 text-sm text-muted"
          >
            <UIcon name="i-lucide-plus" class="size-4" />
            {{ t('forms.new.previewAdd') }}
          </div>
          <span class="h-8 w-24 self-end rounded-md bg-inverted" />
        </div>
      </div>

      <div class="flex flex-col gap-5 p-4 sm:p-6">
        <div class="flex flex-col gap-1">
          <h2 class="text-base font-semibold text-highlighted">{{ t('forms.new.blankTitle') }}</h2>
          <p class="text-sm text-muted">{{ t('forms.new.blankDesc') }}</p>
        </div>
        <ul class="flex flex-col gap-4">
          <li v-for="point in points" :key="point.icon" class="flex items-start gap-3">
            <span class="flex size-9 shrink-0 items-center justify-center rounded-md border border-default bg-elevated/50">
              <UIcon :name="point.icon" class="size-4 text-highlighted" />
            </span>
            <span class="flex min-w-0 flex-col">
              <span class="text-sm font-medium text-highlighted">{{ point.title }}</span>
              <span class="text-xs text-muted">{{ point.text }}</span>
            </span>
          </li>
        </ul>
      </div>
    </div>
  </UCard>
</template>
