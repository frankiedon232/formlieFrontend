<!--
  Create or edit an option list: a name and one option per line (paste from a spreadsheet works).
  Editing keeps each option's stored value when its text is unchanged, so answers keep matching.
-->
<script setup lang="ts">
import { z } from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'
import type { OptionList } from '#shared/types/forms'
import { keyFromLabel } from '#shared/utils/forms/build'

const props = defineProps<{ list: OptionList | null; initialOptions?: OptionList['options']; initialName?: string }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [list: OptionList] }>()
const { t } = useI18n()
const library = useFieldLibrary()

const schema = z.object({
  name: z.string().trim().min(1, t('library.nameRequired')).max(80),
  lines: z
    .string()
    .refine(v => v.split(/\r?\n/).some(l => l.trim()), t('library.optionsRequired'))
    .refine(v => v.split(/\r?\n/).filter(l => l.trim()).length <= 2000, t('library.optionsTooMany')),
})
const state = reactive({ name: '', lines: '' })
watch(open, value => {
  if (!value) return
  state.name = props.list?.name ?? props.initialName ?? ''
  state.lines = (props.list?.options ?? props.initialOptions ?? []).map(o => o.label).join('\n')
})
const count = computed(() => state.lines.split(/\r?\n/).filter(l => l.trim()).length)

const { busy, run } = useBusy()
async function submit(event: FormSubmitEvent<z.output<typeof schema>>) {
  const previous = new Map((props.list?.options ?? []).map(o => [o.label, o]))
  const taken: string[] = []
  const options = event.data.lines
    .split(/\r?\n/)
    .map(l => l.trim())
    .filter(Boolean)
    .map(label => {
      const kept = previous.get(label)
      const value = kept && !taken.includes(kept.value) ? kept.value : keyFromLabel(label, taken) || `option_${taken.length + 1}`
      taken.push(value)
      return { value, label, ...(kept?.score !== undefined ? { score: kept.score } : {}) }
    })
  const saved = await run(() => library.saveList({ name: event.data.name, options }, props.list?.id))
  if (saved) {
    emit('saved', saved)
    open.value = false
  }
}
</script>

<template>
  <AppModal
    v-model:open="open"
    :title="list ? t('library.editListTitle') : t('library.newListTitle')"
    :description="t('library.listDesc')"
    :dismissible="!busy"
  >
    <template #body>
      <UForm id="option-list-form" :schema="schema" :state="state" class="flex flex-col gap-4" @submit="submit">
        <UFormField name="name" :label="t('library.listName')" required>
          <UInput v-model="state.name" maxlength="80" class="w-full" :placeholder="t('library.listNamePlaceholder')" autofocus />
        </UFormField>
        <UFormField name="lines" :label="t('library.listOptions')" :hint="t('library.optionCount', { count }, count)" required>
          <UTextarea v-model="state.lines" :rows="10" autoresize :maxrows="16" class="w-full" :placeholder="t('library.listOptionsPlaceholder')" />
        </UFormField>
      </UForm>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" :disabled="busy" @click="open = false" />
        <UButton type="submit" form="option-list-form" :label="t('common.save')" icon="i-lucide-check" color="neutral" :loading="busy" />
      </div>
    </template>
  </AppModal>
</template>
