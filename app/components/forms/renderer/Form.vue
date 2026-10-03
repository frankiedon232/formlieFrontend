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
import { calculateResult } from '#shared/utils/forms/formula'
import { evaluateLogic } from '#shared/utils/forms/logic'
import { effectiveField, nextPageIndex } from '#shared/utils/forms/submission'
import { identityOf } from '#shared/utils/forms/identity'
import { validateAnswer, type AddressPart, type ValidationIssue } from '#shared/utils/forms/validate'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import type { FormTheme } from '#shared/utils/forms/theme'
import type { RendererRespondent, RendererSubmitOutcome } from '#shared/types/public'

const props = defineProps<{
  schema: FormSchemaV1
  preview?: boolean
  theme?: FormTheme
  /** Designer: show the thank-you page instead of the questions. */
  showThankYou?: boolean
  /** Public page: send the answers; the button stays busy until it reports back (no double submit). */
  submit?: (answers: Record<string, unknown>) => Promise<RendererSubmitOutcome>
  /** Public page: this browser already sent the form, and how to start one for someone else. */
  respondent?: RendererRespondent
}>()
const { t } = useI18n()

const labelPosition = computed(() => props.schema.settings?.label_position ?? 'top')
// Themed buttons (F8): primary colour, style, corners, full width. Unthemed: the portal's black.
const button = computed(() => {
  const b = props.theme?.buttons
  return {
    color: (props.theme ? 'primary' : 'neutral') as 'primary' | 'neutral',
    variant: (b?.variant ?? 'solid') as 'solid' | 'outline' | 'soft',
    block: !!b?.full_width,
    class: props.theme ? 'rounded-[var(--form-button-radius)] justify-center' : '',
  }
})
const labelWidth = computed(() => labelColumnWidth([...allFieldsByKey.value.values()]))
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
const done = ref(!!props.showThankYou)
watch(
  () => props.showThankYou,
  value => (done.value = !!value),
)


// Logic, set values and calculated fields follow the answers live.
const logic = computed(() => evaluateLogic(props.schema, answers.value))
watchEffect(() => {
  for (const [id, value] of logic.value.values) {
    const field = [...allFieldsByKey.value.values()].find(f => f.id === id)
    if (field && JSON.stringify(answers.value[field.key] ?? null) !== JSON.stringify(value)) answers.value[field.key] = value
  }
  for (const field of allFieldsByKey.value.values())
    if (field.type === 'calculated') {
      const value = calculateResult(String(field.props?.formula ?? ''), answers.value, allFieldsByKey.value)
      if (answers.value[field.key] !== value) answers.value[field.key] = value
    }
})

// Pages: hidden pages are skipped everywhere (progress, Next, Back).
const pages = computed(() => props.schema.pages.filter(p => !logic.value.hiddenPages.has(p.id)))
const page = computed(() => props.schema.pages[index.value])
const position = computed(() => Math.max(0, pages.value.findIndex(p => p.id === page.value?.id)))
const nextIndex = computed(() => nextPageIndex(props.schema, logic.value, index.value))
const last = computed(() => nextIndex.value < 0)

/** The field as respondents get it right now — same rules as the API (shared/utils/forms/submission.ts). */
const effective = (field: FormField) => effectiveField(field, logic.value)

const visibleRows = computed(() =>
  (page.value?.rows ?? [])
    .map(row => ({
      ...row,
      // Internal calculations (e.g. a loyalty group) are worked out and saved, but not shown.
      fields: (row.fields as FormField[])
        .filter(f => !logic.value.hidden.has(f.id) && !(f.type === 'calculated' && f.props?.internal))
        .map(effective),
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

// Validation (shared/utils/forms/validate.ts — the API runs the same rules). After a first
// failed Next / Submit, errors update live as respondents fix their answers.
const errorParts = ref<Record<string, AddressPart[]>>({})
const attempted = ref(false)
const PART_LABEL: Record<AddressPart, string> = {
  line1: 'renderer.address.line1',
  city: 'renderer.address.city',
  region: 'renderer.address.region',
  postal_code: 'renderer.address.postalCode',
  country: 'renderer.address.country',
}
function message(field: FormField, issue: ValidationIssue) {
  const name = field.label?.trim() || t('builder.untitled')
  if (issue.code === 'required')
    return field.label?.trim() ? t('renderer.requiredNamed', { field: name }) : t('renderer.requiredError')
  if (issue.code === 'address')
    return t('renderer.invalid.address', { field: name, parts: (issue.parts ?? []).map(part => t(PART_LABEL[part])).join(', ') })
  const custom = field.validation?.pattern_message
  if (issue.code === 'pattern' && typeof custom === 'string' && custom.trim()) return custom
  return t(`renderer.invalid.${issue.code}`, { field: name, ...issue.params })
}
function check(unfold = true): boolean {
  const next: Record<string, string> = {}
  const parts: Record<string, AddressPart[]> = {}
  for (const row of visibleRows.value)
    for (const field of row.fields) {
      if (!isInputField(field.type) || field.type === 'hidden' || field.type === 'calculated' || isLocked(field)) continue
      const issue = validateAnswer(field, answers.value[field.key], !!field.required)
      if (!issue) continue
      next[field.key] = message(field, issue)
      if (issue.parts) parts[field.key] = issue.parts
    }
  errors.value = next
  errorParts.value = parts
  if (unfold)
    for (const row of visibleRows.value) {
      const owner = ownerOf.value.get(row.id)
      if (owner && row.fields.some(f => next[f.key])) folded.value[owner] = false
    }
  return !Object.keys(next).length
}
watch(answers, () => attempted.value && check(false), { deep: true })
// Pages visited, so Back follows the path the respondent actually took (jumps included).
const trail = ref<number[]>([])
const { date: formatDate } = useFormat()
const submitting = ref(false)
/** Thank-you text from the server (it may differ from the schema's, e.g. per language). */
const thanks = ref<{ title: string; message: string } | null>(null)
// After sending (public page): "already sent from this browser" and exact-duplicate notices.
const blocked = ref(false)
const startedAgain = ref(false)
const duplicateNotice = ref(false)
// Telling people apart (F10): "already registered" notice, and the "different person?" / email-code dialogs.
const registered = ref<{ at?: string } | null>(null)
const identityPrompt = ref<{ reason: 'possible' | 'verify'; field?: string; hint?: { at?: string; email?: string } } | null>(null)
const identityEmail = computed(() => String(identityPrompt.value?.field ? (answers.value[identityPrompt.value.field] ?? '') : ''))
function identityContinue() {
  identityPrompt.value = null
  void send()
}
const showAlready = computed(() => !done.value && !props.preview && (blocked.value || (!!props.respondent?.alreadySent && !startedAgain.value)))
function onAnother() {
  props.respondent?.another()
  restart()
  startedAgain.value = true
  blocked.value = false
}

async function send() {
  if (!props.submit || props.preview) return (done.value = true)
  submitting.value = true
  try {
    const outcome = await props.submit({ ...answers.value })
    duplicateNotice.value = outcome.done ? false : outcome.reason === 'duplicate'
    registered.value = !outcome.done && outcome.reason === 'registered' ? { at: outcome.hint?.at } : null
    if (!outcome.done && outcome.reason === 'already') return void (blocked.value = true)
    if (!outcome.done && (outcome.reason === 'possible' || outcome.reason === 'verify'))
      return void (identityPrompt.value = { reason: outcome.reason, field: outcome.field, hint: outcome.hint })
    if (!outcome.done && outcome.reason === 'registered' && outcome.field)
      errors.value = { [outcome.field]: t('renderer.identity.registeredField') }
    if (outcome.done) {
      if (outcome.thank_you?.redirect_url) return void (await navigateTo(outcome.thank_you.redirect_url, { external: true }))
      if (outcome.thank_you) thanks.value = { title: outcome.thank_you.title, message: outcome.thank_you.message }
      done.value = true
      return
    }
    // The server found problems (it runs the same rules): show them on the questions.
    const next: Record<string, string> = {}
    for (const issue of outcome.issues ?? []) {
      const field = allFieldsByKey.value.get(issue.key)
      if (field) next[issue.key] = message(field, { code: issue.code, params: issue.params } as ValidationIssue)
    }
    errors.value = next
    attempted.value = true
  } finally {
    submitting.value = false
  }
}
function next() {
  if (submitting.value) return
  attempted.value = true
  if (!check()) return
  attempted.value = false
  if (last.value) return void send()
  trail.value.push(index.value)
  index.value = nextIndex.value
}
function back() {
  index.value = trail.value.pop() ?? Math.max(0, index.value - 1)
}
// Save and resume (F10 M2): restore saved answers + page, then save after every change.
const resume = computed(() => (props.preview ? undefined : props.respondent?.resume))
const resumeOpen = ref(false)
watch(
  () => resume.value?.initial,
  saved => {
    if (!saved) return
    answers.value = { ...defaults(), ...saved.data }
    index.value = Math.min(Math.max(0, saved.page), props.schema.pages.length - 1)
    trail.value = []
  },
  { immediate: true },
)
watch(
  [answers, index],
  () => {
    if (resume.value && !done.value) resume.value.save({ ...answers.value }, index.value)
  },
  { deep: true },
)
const resumeEmail = computed(() => {
  const key = identityOf(props.schema).email ?? [...allFieldsByKey.value.values()].find(f => f.type === 'email')?.key
  const value = key ? answers.value[key] : ''
  return typeof value === 'string' ? value : ''
})
const { relative } = useFormat()

function restart() {
  index.value = 0
  trail.value = []
  answers.value = defaults()
  errors.value = {}
  errorParts.value = {}
  attempted.value = false
  done.value = false
}
</script>

<template>
  <div class="flex flex-col gap-5 @container/form" :style="{ '--form-label-w': labelWidth }">
    <FormsRendererAfter v-if="showAlready" mode="already" class="py-10 text-center" @another="onAnother" />
    <template v-else-if="!done && page">
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
              :error-parts="errorParts[field.key]"
            />
          </div>
        </div>
        <UAlert
          v-if="registered"
          icon="i-lucide-user-round-check"
          color="warning"
          variant="subtle"
          :title="t('renderer.identity.registeredTitle')"
          :description="registered.at ? t('renderer.identity.registeredDesc', { date: formatDate(registered.at) }) : t('renderer.identity.registeredDescNoDate')"
        />
        <UAlert v-if="duplicateNotice" icon="i-lucide-copy-x" color="warning" variant="subtle" :title="t('renderer.after.duplicate')" :description="t('renderer.after.duplicateDesc')" />
        <div class="flex items-center gap-2 pt-2" :class="button.block ? 'flex-col-reverse' : 'justify-between'">
          <UButton
            v-if="trail.length"
            :label="t('common.back')"
            icon="i-lucide-arrow-left"
            :color="button.color"
            variant="ghost"
            :block="button.block"
            :class="button.class"
            class="rtl:[&_svg]:rotate-180"
            @click="back"
          />
          <span v-else-if="!button.block" />
          <UButton
            type="submit"
            :loading="submitting"
            :label="last ? t('renderer.submit') : t('renderer.next')"
            :trailing-icon="last ? undefined : 'i-lucide-arrow-right'"
            :color="button.color"
            :variant="button.variant"
            :block="button.block"
            :class="button.class"
            class="rtl:[&_svg]:rotate-180"
          />
        </div>
        <!-- Save and resume: saved status + "continue later". -->
        <div v-if="resume" class="flex flex-wrap items-center justify-between gap-2 border-t border-(--ui-border) pt-3 text-xs text-muted">
          <span class="flex items-center gap-1.5" role="status" aria-live="polite">
            <UIcon
              :name="resume.state === 'saving' ? 'i-lucide-loader-circle' : resume.state === 'error' ? 'i-lucide-cloud-alert' : 'i-lucide-cloud-check'"
              class="size-3.5 shrink-0"
              :class="resume.state === 'saving' ? 'animate-spin' : resume.state === 'error' ? 'text-(--ui-error)' : ''"
            />
            {{
              resume.state === 'saving'
                ? t('renderer.resume.saving')
                : resume.state === 'error'
                  ? t('renderer.resume.notSaved')
                  : resume.savedAt
                    ? t('renderer.resume.saved', { when: relative(resume.savedAt) })
                    : t('renderer.resume.auto')
            }}
          </span>
          <UButton :label="t('renderer.resume.later')" icon="i-lucide-bookmark" :color="button.color" variant="link" size="xs" class="px-0" @click="resumeOpen = true" />
        </div>
      </form>
      <FormsRendererResume v-if="resume" v-model:open="resumeOpen" :default-email="resumeEmail" :later="resume.later" />
    </template>

    <div v-else class="flex flex-col items-center gap-3 py-10 text-center">
      <UIcon v-if="theme?.thank_you.show_icon !== false" name="i-lucide-circle-check" class="size-10" :class="theme ? 'text-(--ui-primary)' : 'text-success'" />
      <h2 class="text-xl font-semibold text-highlighted">
        {{ thanks?.title || schema.thank_you?.title || t('renderer.thanks') }}
      </h2>
      <p v-if="thanks?.message || schema.thank_you?.message" class="max-w-md text-sm text-muted">
        {{ thanks?.message || schema.thank_you?.message }}
      </p>
      <p v-if="preview" class="text-xs text-muted">{{ t('builder.preview.nothingSent') }}</p>
      <FormsRendererAfter v-if="respondent && !preview" mode="thanks" class="pt-2" @another="onAnother" />
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
    <FormsRendererIdentity
      v-if="respondent && !preview"
      :reason="identityPrompt?.reason ?? null"
      :hint="identityPrompt?.hint"
      :email="identityEmail"
      :respondent="respondent"
      @continue="identityContinue"
      @cancel="identityPrompt = null"
    />
  </div>
</template>
