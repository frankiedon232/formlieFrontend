<!--
  Option list editor → How lists work (owner 2026-10-08: "proper instructions"): three short steps,
  open until someone closes it (remembered in this browser, a display preference only).
-->
<script setup lang="ts">
const { t } = useI18n()
const open = useLocalStorage('formalie-list-guide-open', true)
const steps = computed(() => [
  { icon: 'i-lucide-network', title: t('optionSets.guide.typeTitle'), text: t('optionSets.guide.type') },
  { icon: 'i-lucide-file-up', title: t('optionSets.guide.fillTitle'), text: t('optionSets.guide.fill') },
  { icon: 'i-lucide-file-check', title: t('optionSets.guide.useTitle'), text: t('optionSets.guide.use') },
])
</script>

<template>
  <UCollapsible v-model:open="open" class="rounded-lg border border-default">
    <UButton :label="t('optionSets.guide.title')" icon="i-lucide-lightbulb" trailing-icon="i-lucide-chevron-down" color="neutral" variant="ghost" size="sm" block class="justify-start" :ui="{ trailingIcon: 'ms-auto transition-transform group-data-[state=open]:rotate-180' }" />
    <template #content>
      <ol class="grid gap-3 px-3 pb-3 sm:grid-cols-3">
        <li v-for="(step, index) in steps" :key="index" class="flex gap-2.5">
          <span class="flex size-7 shrink-0 items-center justify-center rounded-lg border border-primary/25 bg-primary/10 text-primary"><UIcon :name="step.icon" class="size-4" /></span>
          <div class="flex min-w-0 flex-col gap-0.5">
            <span class="text-xs font-medium text-highlighted">{{ index + 1 }}. {{ step.title }}</span>
            <span class="text-xs text-muted">{{ step.text }}</span>
          </div>
        </li>
      </ol>
    </template>
  </UCollapsible>
</template>
