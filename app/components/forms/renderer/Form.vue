<!--
  A whole form as respondents use it: progress, one page at a time, Back / Next / Submit,
  required checks per page, logic (show / hide fields and pages, required / optional, enable /
  disable, set / clear values, jump, skip to the end), calculated fields, collapsible sections,
  thank-you screen. Used by the builder preview and by the public form and embed. `preview`
  never sends anything. Columns follow the form's own width (container queries).
-->
<script setup lang="ts">
import { allFields, isLocked, type FormField } from '#shared/utils/forms/build'
import { cascadeClosed, fitAnswer } from '#shared/utils/forms/cascade'
import { isInputField } from '#shared/utils/forms/fields'
import { calculateResult } from '#shared/utils/forms/formula'
import { evaluateLogic } from '#shared/utils/forms/logic'
import { nextPageIndex } from '#shared/utils/forms/submission'
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
  submit?: (answers: Record<string, unknown>, extra?: { trap?: string }) => Promise<RendererSubmitOutcome>
  /** Public page: this browser already sent the form, and how to start one for someone else. */
  respondent?: RendererRespondent
  /** Preview page: go straight to this page (index) or the thank-you screen, answers kept. */
  goTo?: { at: number | 'thanks'; n: number }
}>()
/** Preview page: where the respondent is now (page index or the thank-you screen). */
const emit = defineEmits<{ at: [at: number | 'thanks'] }>()
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

// Logic, set values and calculated fields follow the answers live. A level of a list with levels that has
// nothing under the choice above stays closed, like a hidden field (F15 M2).
const fieldsById = computed(() => new Map(allFields(props.schema).map(f => [f.id, f])))
const logic = computed(() => {
  const state = evaluateLogic(props.schema, answers.value)
  for (const field of fieldsById.value.values()) if (cascadeClosed(field, fieldsById.value, answers.value)) state.hidden.add(field.id)
  return state
})
provide(RENDERER_ANSWERS, { answers, fieldsById })
// A changed choice above clears what no longer fits below
watchEffect(() => {
  for (const field of fieldsById.value.values()) {
    if (!field.option_parent || answers.value[field.key] === undefined) continue
    const fitted = fitAnswer(field, fieldsById.value, answers.value)
    if (JSON.stringify(fitted ?? null) !== JSON.stringify(answers.value[field.key] ?? null)) answers.value[field.key] = fitted
  }
})
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

// Rows on screen and collapsible sections (useRendererSections), same rules as the API.
const { visibleRows, shownRows, collapsible, folded, toggle, unfoldFor } = useRendererSections(page, logic, allFieldsByKey)

// Validation (shared/utils/forms/validate.ts, the API runs the same rules). After a first
// failed Next / Submit, errors update live as respondents fix their answers.
const errorParts = ref<Record<string, AddressPart[]>>({})
const attempted = ref(false)
const message = useAnswerMessages()
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
  if (unfold) unfoldFor(next)
  return !Object.keys(next).length
}
watch(answers, () => attempted.value && check(false), { deep: true })
// Pages visited, so Back follows the path the respondent actually took (jumps included).
const trail = ref<number[]>([])
const submitting = ref(false)
// Spam check (decision 89): a field people never see or reach; bots fill it in.
const trap = ref('')
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
    const outcome = await props.submit({ ...answers.value }, { trap: trap.value })
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
// File questions upload as soon as files are picked (public page); Next / Submit wait for them.
const uploadsPending = ref(0)
// Field icons for the whole form (Form settings → Field icons; default on)
provide(RENDERER_ICONS, computed(() => props.schema.settings?.field_icons !== false))
provide(RENDERER_UPLOADS, { upload: props.preview ? null : (props.respondent?.upload ?? null), pending: uploadsPending })
provide(RENDERER_LOOKUP, props.respondent?.lookup ?? null)

function next() {
  if (submitting.value || uploadsPending.value) return
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
/** "Save and continue later" saves what is on screen right now (also when nothing changed yet). */
function laterWithAnswers(email: string) {
  resume.value?.save({ ...answers.value }, index.value)
  return resume.value ? resume.value.later(email) : Promise.resolve(null)
}
const resumeEmail = computed(() => {
  const key = identityOf(props.schema).email ?? [...allFieldsByKey.value.values()].find(f => f.type === 'email')?.key
  const value = key ? answers.value[key] : ''
  return typeof value === 'string' ? value : ''
})

// Preview page: jump anywhere without filling in what comes before (nothing is ever sent there).
watch(
  () => props.goTo,
  jump => {
    if (!jump || !props.preview) return
    trail.value = []
    errors.value = {}
    attempted.value = false
    done.value = jump.at === 'thanks'
    if (jump.at !== 'thanks') index.value = Math.min(Math.max(0, jump.at), props.schema.pages.length - 1)
  },
)
watch([index, done], () => emit('at', done.value ? 'thanks' : index.value))

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
    <FormsRendererAfter v-if="showAlready" mode="already" :org="respondent?.org" :embedded="respondent?.embedded" class="py-10 text-center" @another="onAnother" />
    <template v-else-if="!done && page">
      <!-- The page name rides with the step progress (owner 2026-10-08), never as a heading in the form -->
      <FormsRendererProgress v-if="pages.length > 1 && schema.settings?.progress_bar !== false" :position="position" :total="pages.length" :page="page.title" />
      <form class="relative flex flex-col gap-4" novalidate @submit.prevent="next">
        <input v-if="submit && !preview" v-model="trap" type="text" name="formalie_hp" tabindex="-1" autocomplete="off" aria-hidden="true" class="pointer-events-none absolute -start-[200vw] top-0 size-px opacity-0">
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
        <FormsRendererNotices :registered="registered" :duplicate="duplicateNotice" :uploads-pending="uploadsPending" />
        <FormsRendererNav :can-go-back="trail.length > 0" :last="last" :submitting="submitting" :uploads-pending="uploadsPending" :button="button" @back="back" />
        <!-- Save and resume: saved status + "continue later". -->
        <FormsRendererResumeBar v-if="resume" :resume="resume" :color="button.color" @later="resumeOpen = true" />
      </form>
      <FormsRendererResume v-if="resume" v-model:open="resumeOpen" :default-email="resumeEmail" :later="laterWithAnswers" />
    </template>

    <FormsRendererThanks
      v-else
      :title="thanks?.title || schema.thank_you?.title"
      :message="thanks?.message || schema.thank_you?.message"
      :icon="theme?.thank_you.show_icon !== false"
      :themed="!!theme"
      :preview="preview"
      :respondent="respondent"
      @another="onAnother"
      @restart="restart"
    />
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
