<!--
  Form overview → highlights (F11 insights on the form's home): the two most telling questions of
  the last 30 days (choices and ratings first), summarised like the Insights view, side by side at
  one height; "All insights" opens the full summary.
-->
<script setup lang="ts">
import type { ResponseInsights } from '#shared/types/responses'

const props = defineProps<{ formId: string; insights: ResponseInsights }>()
const { t } = useI18n()
const picked = computed(() => {
  const all = props.insights.questions
  const telling = all.filter(item => (item.kind === 'choice' || item.kind === 'rating') && item.answered > 0)
  return telling.slice(0, 2).map(question => ({ question, index: all.indexOf(question) }))
})
</script>

<template>
  <section v-if="picked.length" class="flex flex-col gap-3">
    <div class="flex items-center justify-between gap-2">
      <h2 class="text-sm font-semibold text-highlighted">{{ t('forms.overview.highlights') }}</h2>
      <UButton :label="t('forms.overview.allInsights')" trailing-icon="i-lucide-arrow-right" color="neutral" variant="link" size="xs" :to="`/forms/${formId}/responses?view=insights`" class="rtl:[&_svg]:rotate-180" />
    </div>
    <div class="grid items-stretch gap-4 md:grid-cols-2">
      <FormsResponsesQuestion
        v-for="item in picked"
        :key="item.question.key"
        :question="item.question"
        :index="item.index"
        :total="insights.period.count"
        class="h-full"
        @open="id => navigateTo(`/forms/${formId}/responses?response=${id}`)"
      />
    </div>
  </section>
</template>
