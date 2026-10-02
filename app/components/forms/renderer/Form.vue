<!--
  A whole form as respondents use it: progress, one page at a time, Back / Next / Submit,
  required checks per page, logic (show / hide fields and pages, required / optional, enable /
  disable, set / clear values, jump, skip to the end), calculated fields, collapsible sections,
  thank-you screen. Used by the builder preview and by the public form and embed. `preview`
  never sends anything. Columns follow the form's own width (container queries).
-->
<script setup lang="ts">
import { isLocked, sectionOwners, type FormField } from '#shared/utils/forms/build'
import { isInputField } from '#shared/utils/forms/fields'
import { calculate } from '#shared/utils/forms/formula'
import { END_OF_FORM, evaluateLogic } from '#shared/utils/forms/logic'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'

const props = defineProps<{ schema: FormSchemaV1; preview?: boolean }>()
const { t } = useI18n()

const labelPosition = computed(() => props.schema.settings?.label_position ?? 'top')
const allFieldsByKey = computed(
  () => new Map(props.schema.pages.flatMap(p => p.rows.flatMap(r => r.fields as FormField[])).map(f => [f.key, f])),
)
const defaults = () =>
  Object.fromEntries(
    [...allFieldsByKey.value.values()].filter(f => f.default != null && f.default !== '').map(f => [f.key, f.default]),
  )

const index = ref(0)
const answers = ref<Record<string, unknown>>(defaults())
const errors = ref<Record<string, string>>({})
const done = ref(false)

const empty = (value: unknown) =>
  value == null || value === '' || (Array.isArray(value) && !value.length) || value === false

// Logic, set values and calculated fields follow the answers live.
const logic = computed(() => evaluateLogic(props.schema, answers.value))
watchEffect(() => {
  for (const [id, value] of logic.value.values) {
    const field = [...allFieldsByKey.value.values()].find(f => f.id === id)
    if (field && JSON.stringify(answers.value[field.key] ?? null) !== JSON.stringify(value)) answers.value[field.key] = value
  }
  for (const field of allFieldsByKey.value.values())
    if (field.type === 'calculated') {
      const value = calculate(String(field.props?.formula ?? ''), answers.value, allFieldsByKey.value)
      if (answers.value[field.key] !== value) answers.value[field.key] = value
    }
})

// Pages: hidden pages are skipped everywhere (progress, Next, Back).
const pages = computed(() => props.schema.pages.filter(p => !logic.value.hiddenPages.has(p.id)))
const page = computed(() => props.schema.pages[index.value])
const position = computed(() => Math.max(0, pages.value.findIndex(p => p.id === page.value?.id)))
const nextIndex = computed(() => {
  const jump = page.value && logic.value.jumps.get(page.value.id)
  if (jump === END_OF_FORM) return -1
  const target = jump ? props.schema.pages.findIndex(p => p.id === jump) : -1
  const from = target > index.value ? target : index.value + 1
  return props.schema.pages.findIndex((p, i) => i >= from && !logic.value.hiddenPages.has(p.id))
})
const last = computed(() => nextIndex.value < 0)

/** The field as respondents get it right now (logic can disable / enable it and change "required"). */
function effective(field: FormField): FormField {
  const disabled = logic.value.disabled.has(field.id) ? true : logic.value.enabled.has(field.id) ? false : field.disabled
  const wanted = logic.value.optional.has(field.id) ? false : !!field.required || logic.value.required.has(field.id)
  // Read-only, disabled and hidden fields are never required: nobody could fill them in.
  const required = wanted && !isLocked({ ...field, disabled }) && field.type !== 'hidden'
  return { ...field, disabled, required }
}

const visibleRows = computed(() =>
  (page.value?.rows ?? [])
    .map(row => ({
      ...row,
      fields: (row.fields as FormField[]).filter(f => !logic.value.hidden.has(f.id)).map(effective),
    }))
    .filter(row => row.fields.length),
)

// Collapsible sections: a section heading with `collapsible` folds the rows below it, up to the
// next section. Folded fields still count for required checks (a failing one unfolds its section).
const collapsible = (field?: FormField) => field?.type === 'section' && !!field.props?.collapsible
const folded = ref<Record<string, boolean>>({})
watch(
  () => [...allFieldsByKey.value.values()].filter(collapsible),
  sections => {
    for (const section of sections) folded.value[section.id] ??= !!section.props?.collapsed
  },
  { immediate: true },
)
const ownerOf = computed(() => sectionOwners(visibleRows.value))
/** What's on screen: hidden-type fields carry values but are never shown to respondents. */
const shownRows = computed(() =>
  visibleRows.value
    .filter(row => !folded.value[ownerOf.value.get(row.id) ?? ''])
    .map(row => ({ ...row, fields: row.fields.filter(f => f.type !== 'hidden') }))
    .filter(row => row.fields.length),
)
const toggle = (id: string) => (folded.value[id] = !folded.value[id])

function check(): boolean {
  const next: Record<string, string> = {}
  for (const row of visibleRows.value)
    for (const field of row.fields)
      if (field.required && isInputField(field.type) && empty(answers.value[field.key]))
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
  trail.value.push(index.value)
  index.value = nextIndex.value
}
function back() {
  index.value = trail.value.pop() ?? Math.max(0, index.value - 1)
}
function restart() {
  index.value = 0
  trail.value = []
  answers.value = defaults()
  errors.value = {}
  done.value = false
}
</script>

<template>
  <div class="flex flex-col gap-5 @container/form" :class="FORM_RADIUS">
    <template v-if="!done && page">
      <div v-if="pages.length > 1 && schema.settings?.progress_bar !== false" class="flex flex-col gap-1.5">
        <div class="flex justify-between text-xs text-muted">
          <span>{{ t('builder.page.stepOf', { n: position + 1, total: pages.length }) }}</span>
          <span>{{ Math.round(((position + 1) / pages.length) * 100) }}%</span>
        </div>
        <UProgress :model-value="position + 1" :max="pages.length" color="neutral" size="xs" />
      </div>
      <h2 v-if="page.title" class="text-xl font-semibold text-highlighted">{{ page.title }}</h2>
      <form class="flex flex-col gap-4" novalidate @submit.prevent="next">
        <div v-for="row in shownRows" :key="row.id" class="grid grid-cols-12 gap-x-4 gap-y-4">
          <div
            v-for="field in row.fields"
            :key="field.id"
            class="col-span-12 @container"
            :class="FIELD_SPAN[field.width ?? 12]"
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
              :field="field"
              :label-position="labelPosition"
              :error="errors[field.key]"
            />
          </div>
        </div>
        <div class="flex items-center justify-between gap-2 pt-2">
          <UButton
            v-if="trail.length"
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
