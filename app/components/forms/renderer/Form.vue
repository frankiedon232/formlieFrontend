<!--
  A whole form as respondents use it: progress, one page at a time, Back / Next / Submit,
  required-field checks per page, logic (show / hide, required-if, jump to page), calculated
  fields, thank-you screen. Used by the builder preview now and by the
  public form and embed (F10). `preview` never sends anything.
-->
<script setup lang="ts">
import { sectionOwners, type FormField } from '#shared/utils/forms/build'
import { isInputField } from '#shared/utils/forms/fields'
import { calculate, evaluateLogic } from '#shared/utils/forms/logic'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'

const props = defineProps<{ schema: FormSchemaV1; preview?: boolean }>()
const { t } = useI18n()

const SPAN: Record<number, string> = {
  12: 'sm:col-span-12',
  9: 'sm:col-span-9',
  8: 'sm:col-span-8',
  6: 'sm:col-span-6',
  4: 'sm:col-span-4',
  3: 'sm:col-span-3',
}
const index = ref(0)
const answers = ref<Record<string, unknown>>({})
const errors = ref<Record<string, string>>({})
const done = ref(false)
const page = computed(() => props.schema.pages[index.value])
const last = computed(() => index.value === props.schema.pages.length - 1)

const empty = (value: unknown) =>
  value == null || value === '' || (Array.isArray(value) && !value.length) || value === false

// Logic + calculated fields follow the answers live.
const logic = computed(() => evaluateLogic(props.schema, answers.value))
watchEffect(() => {
  for (const p of props.schema.pages)
    for (const row of p.rows)
      for (const field of row.fields as FormField[])
        if (field.type === 'calculated') {
          const value = calculate(String(field.props?.formula ?? ''), answers.value)
          if (answers.value[field.key] !== value) answers.value[field.key] = value
        }
})
const visibleRows = computed(() =>
  (page.value?.rows ?? [])
    .map(row => ({ ...row, fields: (row.fields as FormField[]).filter(f => !logic.value.hidden.has(f.id)) }))
    .filter(row => row.fields.length),
)

// Collapsible sections: a section heading with `collapsible` folds the rows below it, up to the
// next section. Folded fields still count for required checks (a failing one unfolds its section).
const collapsible = (field?: FormField) => field?.type === 'section' && !!field.props?.collapsible
const folded = ref<Record<string, boolean>>({})
watch(
  () => props.schema.pages.flatMap(p => p.rows.flatMap(r => r.fields as FormField[])).filter(collapsible),
  sections => {
    for (const section of sections) folded.value[section.id] ??= !!section.props?.collapsed
  },
  { immediate: true },
)
const ownerOf = computed(() => sectionOwners(visibleRows.value))
const shownRows = computed(() => visibleRows.value.filter(row => !folded.value[ownerOf.value.get(row.id) ?? '']))
const toggle = (id: string) => (folded.value[id] = !folded.value[id])
const isRequired = (field: FormField) => !!field.required || logic.value.required.has(field.id)

function check(): boolean {
  const next: Record<string, string> = {}
  for (const row of visibleRows.value)
    for (const field of row.fields)
      if (isRequired(field) && isInputField(field.type) && empty(answers.value[field.key]))
        next[field.key] = t('renderer.requiredError')
  errors.value = next
  for (const row of visibleRows.value) {
    const owner = ownerOf.value.get(row.id)
    if (owner && row.fields.some(f => next[f.key])) folded.value[owner] = false
  }
  return !Object.keys(next).length
}
// Pages visited, so Back follows the path the respondent actually took (jumps included).
const trail = ref<number[]>([])
function next() {
  if (!check()) return
  if (last.value) return (done.value = true)
  const jump = page.value && logic.value.jumps.get(page.value.id)
  const target = jump ? props.schema.pages.findIndex(p => p.id === jump) : -1
  trail.value.push(index.value)
  index.value = target > index.value ? target : index.value + 1
}
function back() {
  index.value = trail.value.pop() ?? Math.max(0, index.value - 1)
}
function restart() {
  index.value = 0
  trail.value = []
  answers.value = {}
  errors.value = {}
  done.value = false
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <template v-if="!done && page">
      <div
        v-if="schema.pages.length > 1 && schema.settings?.progress_bar !== false"
        class="flex flex-col gap-1.5"
      >
        <div class="flex justify-between text-xs text-muted">
          <span>{{ t('builder.page.stepOf', { n: index + 1, total: schema.pages.length }) }}</span>
          <span>{{ Math.round(((index + 1) / schema.pages.length) * 100) }}%</span>
        </div>
        <UProgress :model-value="index + 1" :max="schema.pages.length" color="neutral" size="xs" />
      </div>
      <h2 v-if="page.title" class="text-xl font-semibold text-highlighted">{{ page.title }}</h2>
      <form class="flex flex-col gap-5" novalidate @submit.prevent="next">
        <div v-for="row in shownRows" :key="row.id" class="grid grid-cols-12 gap-x-4 gap-y-5">
          <div
            v-for="field in row.fields"
            :key="field.id"
            class="col-span-12"
            :class="SPAN[field.width ?? 12]"
          >
            <UButton
              v-if="collapsible(field)"
              color="neutral"
              variant="ghost"
              block
              :trailing-icon="folded[field.id] ? 'i-lucide-chevron-down' : 'i-lucide-chevron-up'"
              :aria-expanded="!folded[field.id]"
              class="-mx-2 justify-between px-2 text-start"
              @click="toggle(field.id)"
            >
              <FormsRendererLayout :field="field" mode="live" />
            </UButton>
            <FormsRendererField
              v-else
              v-model="answers[field.key]"
              :field="isRequired(field) && !field.required ? { ...field, required: true } : field"
              :error="errors[field.key]"
            />
          </div>
        </div>
        <div class="flex items-center justify-between gap-2 pt-2">
          <UButton
            v-if="index > 0"
            :label="t('common.back')"
            icon="i-lucide-arrow-left"
            color="neutral"
            variant="outline"
            class="rtl:[&_svg]:rotate-180"
            @click="back"
          />
          <span v-else />
          <UButton
            type="submit"
            :label="last ? t('renderer.submit') : t('renderer.next')"
            :trailing-icon="last ? undefined : 'i-lucide-arrow-right'"
            color="neutral"
            class="rtl:[&_svg]:rotate-180"
          />
        </div>
      </form>
    </template>

    <div v-else class="flex flex-col items-center gap-3 py-10 text-center">
      <UIcon name="i-lucide-circle-check" class="size-10 text-success" />
      <h2 class="text-xl font-semibold text-highlighted">
        {{ schema.thank_you?.title || t('renderer.thanks') }}
      </h2>
      <p v-if="schema.thank_you?.message" class="max-w-md text-sm text-muted">
        {{ schema.thank_you.message }}
      </p>
      <p v-if="preview" class="text-xs text-muted">{{ t('builder.preview.nothingSent') }}</p>
      <UButton
        v-if="preview"
        :label="t('builder.preview.restart')"
        icon="i-lucide-rotate-ccw"
        color="neutral"
        variant="outline"
        size="sm"
        @click="restart"
      />
    </div>
  </div>
</template>
