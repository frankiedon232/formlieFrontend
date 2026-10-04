<!--
  Every answer of a response, a card per page (F11 panel): page title with how many of its
  questions were answered and a slim bar; each question numbered, with its type icon, the
  question, and the answer shown by kind (FormsResponsesAnswer).
-->
<script setup lang="ts">
import type { ResponseDetail } from '#shared/types/responses'
import { FIELD_TYPES, isInputField } from '#shared/utils/forms/fields'

const props = defineProps<{ response: ResponseDetail }>()
const { t } = useI18n()

const filled = (value: unknown) => value != null && value !== '' && !(Array.isArray(value) && !value.length)
const pages = computed(() => {
  let n = 0
  return props.response.schema.pages
    .map((page, index) => {
      const fields = page.rows.flatMap(row => row.fields).filter(field => isInputField(field.type) && field.type !== 'payment' && field.type !== 'hidden')
      const items = fields.map(field => ({ field, n: ++n, icon: (FIELD_TYPES as Record<string, { icon: string }>)[field.type]?.icon ?? 'i-lucide-circle-help' }))
      return { id: page.id, title: page.title || t('preview.page', { n: index + 1 }), items, answered: fields.filter(field => filled(props.response.data[field.key])).length }
    })
    .filter(page => page.items.length)
})
</script>

<template>
  <section v-for="page in pages" :key="page.id" class="overflow-hidden rounded-lg border border-default">
    <header class="flex items-center gap-3 border-b border-default bg-elevated/40 px-4 py-2.5">
      <h3 class="min-w-0 flex-1 truncate text-sm font-semibold text-highlighted">{{ page.title }}</h3>
      <span class="shrink-0 text-xs text-muted tabular-nums">{{ t('responses.detail.answeredOf', { n: page.answered, total: page.items.length }) }}</span>
      <span class="h-1 w-14 shrink-0 overflow-hidden rounded-full bg-accented/60" role="presentation">
        <span class="block h-full rounded-full bg-inverted" :style="{ width: `${(page.answered / page.items.length) * 100}%` }" />
      </span>
    </header>
    <dl class="divide-y divide-default">
      <div v-for="item in page.items" :key="item.field.id" class="flex gap-3 px-4 py-3">
        <span class="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md bg-elevated text-muted">
          <UIcon :name="item.icon" class="size-3.5" />
        </span>
        <div class="flex min-w-0 flex-1 flex-col gap-1.5">
          <dt class="text-xs text-muted"><span class="me-1 text-dimmed tabular-nums">{{ item.n }}.</span>{{ item.field.label || item.field.key }}</dt>
          <dd class="min-w-0"><FormsResponsesAnswer :field="item.field" :value="response.data[item.field.key]" /></dd>
        </div>
      </div>
    </dl>
  </section>
</template>
