<!--
  "From a template" tab of New form (F9): the system catalogue as selectable cards — each with a
  mini preview in its own design — narrowed by category and search. The full gallery (with your
  workspace templates and usage) is one click away.
-->
<script setup lang="ts">
import { SYSTEM_TEMPLATES, TEMPLATE_CATEGORIES, categoryOf, previewLabels, templateSchema } from '#shared/templates'

const model = defineModel<string>({ required: true })
const { t, te } = useI18n()

const nameOf = (key: string, fallback: string) => (te(`templates.items.${key}.name`) ? t(`templates.items.${key}.name`) : fallback)
const cards = computed(() =>
  SYSTEM_TEMPLATES.map(def => {
    const schema = templateSchema(def)
    return {
      key: def.key,
      category: def.category,
      icon: def.icon,
      name: nameOf(def.key, def.name),
      theme: schema.theme as Record<string, unknown>,
      labels: previewLabels(schema, 2),
    }
  }),
)

const category = ref<string>(SYSTEM_TEMPLATES.find(def => def.key === model.value)?.category ?? 'all')
const query = ref('')
const categories = computed(() => [
  { value: 'all', label: t('templates.all') },
  ...TEMPLATE_CATEGORIES.filter(c => cards.value.some(card => card.category === c.key)).map(c => ({
    value: c.key,
    label: t(`templates.categories.${c.key}`),
  })),
])
const shown = computed(() => {
  const q = query.value.trim().toLowerCase()
  return cards.value.filter(card => (category.value === 'all' || card.category === category.value) && (!q || card.name.toLowerCase().includes(q)))
})
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
      <UInput v-model="query" icon="i-lucide-search" :placeholder="t('templates.search')" class="w-full sm:w-64" :aria-label="t('templates.search')" />
      <USelectMenu v-model="category" :items="categories" value-key="value" class="w-full sm:w-56" :aria-label="t('templates.filter.category')" />
      <UButton :label="t('templates.openGallery')" icon="i-lucide-layout-grid" color="neutral" variant="link" to="/templates" class="sm:ms-auto" />
    </div>

    <div role="radiogroup" :aria-label="t('forms.new.template')" class="grid max-h-[28rem] grid-cols-1 gap-2 overflow-y-auto p-0.5 sm:grid-cols-2 lg:grid-cols-3">
      <button
        v-for="card in shown"
        :key="card.key"
        type="button"
        role="radio"
        :aria-checked="model === card.key"
        class="flex flex-col overflow-hidden rounded-lg border text-start transition-colors focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
        :class="model === card.key ? 'border-inverted ring-1 ring-inverted' : 'border-default hover:border-accented'"
        @click="model = card.key"
      >
        <TemplatesThumb :theme="card.theme" :title="card.name" :labels="card.labels" compact />
        <span class="flex items-center gap-2 border-t border-default px-2.5 py-2">
          <UIcon :name="card.icon" class="size-4 shrink-0 text-muted" />
          <span class="min-w-0 flex-1 truncate text-sm font-medium text-highlighted">{{ card.name }}</span>
          <span class="size-2 shrink-0 rounded-[1px]" :class="categoryOf(card.category)?.dot" aria-hidden="true" />
        </span>
      </button>
      <p v-if="!shown.length" class="col-span-full py-6 text-center text-sm text-muted">{{ t('templates.emptyTitle') }}</p>
    </div>
  </div>
</template>
