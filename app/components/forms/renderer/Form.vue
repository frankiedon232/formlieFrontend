<!--
  A whole form as respondents use it: progress, one page at a time, Back / Next / Submit,
  required-field checks per page, thank-you screen. Used by the builder preview now and by the
  public form and embed (F10). `preview` never sends anything.
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'
import { isInputField } from '#shared/utils/forms/fields'
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

function check(): boolean {
  const next: Record<string, string> = {}
  for (const row of page.value?.rows ?? [])
    for (const field of row.fields as FormField[])
      if (field.required && isInputField(field.type) && empty(answers.value[field.key]))
        next[field.key] = t('renderer.requiredError')
  errors.value = next
  return !Object.keys(next).length
}
function next() {
  if (!check()) return
  if (last.value) done.value = true
  else index.value++
}
function restart() {
  index.value = 0
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
        <div v-for="row in page.rows" :key="row.id" class="grid grid-cols-12 gap-x-4 gap-y-5">
          <div
            v-for="field in row.fields"
            :key="field.id"
            class="col-span-12"
            :class="SPAN[field.width ?? 12]"
          >
            <FormsRendererField v-model="answers[field.key]" :field="field" :error="errors[field.key]" />
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
            @click="index--"
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
