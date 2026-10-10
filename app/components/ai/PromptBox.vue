<!--
  What to ask the assistant (F19 M2): a description in plain words with ready examples to start from,
  optionally a pasted document and how many pages; Generate (Ctrl / ⌘ + Enter) with what it costs and
  what is left this month. Shared by Create a form and Template ideas.
-->
<script setup lang="ts">
const prompt = defineModel<string>({ required: true })
const documentText = defineModel<string>('document', { default: '' })
const pages = defineModel<'auto' | 'one' | 'several'>('pages', { default: 'auto' })
const props = defineProps<{ examples: string[]; placeholder: string; busy: boolean; cost: number; left: number | null; withDocument?: boolean; withPages?: boolean; label: string }>()
const emit = defineEmits<{ generate: [] }>()
const { t } = useI18n()
const { number } = useFormat()
const uid = useId()
const showDocument = ref(!!documentText.value)
const ready = computed(() => prompt.value.trim().length >= 3 && !props.busy && (props.left === null || props.left >= props.cost))
const pageOptions = computed(() => (['auto', 'one', 'several'] as const).map(value => ({ value, label: t(`ai.create.pages.${value}`) })))
function go() {
  if (ready.value) emit('generate')
}
defineShortcuts({ meta_enter: { usingInput: true, handler: go } })
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-5' }">
    <UFormField :label="label" :name="`${uid}-prompt`" :hint="`${prompt.length} / 2000`">
      <UTextarea :id="`${uid}-prompt`" v-model="prompt" :placeholder="placeholder" :rows="5" autoresize :maxrows="12" :maxlength="2000" class="w-full" :disabled="busy" />
    </UFormField>

    <div class="flex flex-col gap-2">
      <span class="text-xs text-muted">{{ t('ai.create.examples') }}</span>
      <div class="flex flex-wrap gap-1.5">
        <UButton v-for="example in examples" :key="example" :label="example" color="neutral" variant="outline" size="xs" class="max-w-full rounded-full" :ui="{ label: 'truncate' }" :disabled="busy" @click="prompt = example" />
      </div>
    </div>

    <template v-if="withDocument">
      <UButton v-if="!showDocument" :label="t('ai.create.addDocument')" icon="i-lucide-file-text" color="neutral" variant="ghost" size="sm" class="self-start" @click="showDocument = true" />
      <UFormField v-else :label="t('ai.create.document')" :description="t('ai.create.documentHint')">
        <template #hint>
          <UButton :label="t('ai.create.removeDocument')" color="neutral" variant="link" size="xs" @click="(documentText = ''), (showDocument = false)" />
        </template>
        <UTextarea v-model="documentText" :placeholder="t('ai.create.documentPlaceholder')" :rows="6" :maxrows="14" autoresize :maxlength="20000" class="w-full font-mono text-xs" :disabled="busy" />
      </UFormField>
    </template>

    <UFormField v-if="withPages" :label="t('ai.create.pages.label')">
      <UTabs v-model="pages" :items="pageOptions" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" />
    </UFormField>

    <div class="flex flex-wrap items-center justify-between gap-3 border-t border-default pt-4">
      <span class="flex items-center gap-1.5 text-xs text-muted">
        <UIcon name="i-lucide-coins" class="size-3.5" />
        {{ left === null ? t('ai.create.cost', { n: cost }, cost) : t('ai.create.costLeft', { n: cost, left: number(left) }, cost) }}
      </span>
      <UButton :label="t('ai.create.generate')" icon="i-lucide-sparkles" color="neutral" :loading="busy" :disabled="!ready" @click="go">
        <template #trailing><UKbd value="meta" size="sm" class="hidden sm:inline-flex" /><UKbd value="enter" size="sm" class="hidden sm:inline-flex" /></template>
      </UButton>
    </div>
    <UAlert v-if="left !== null && left < cost" color="warning" variant="subtle" icon="i-lucide-gauge" :title="t('errors.FRM-AI-1002')" />
  </UCard>
</template>
