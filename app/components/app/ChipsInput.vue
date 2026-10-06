<!--
  Values as chips (owner, 2026-10-06: access rule IPs and domains). Comma, space, Enter or Tab (and
  pasting a list, or leaving the field) turns what was typed into chips; each one is checked first.
  A wrong value stays in the box with the reason, so it can be corrected instead of vanishing.
  Backspace in an empty box takes the last chip back for editing; each chip has its own remove.
-->
<script setup lang="ts">
const props = defineProps<{ placeholder?: string; check: (value: string) => string | null; normalise?: (value: string) => string; mono?: boolean }>()
const model = defineModel<string[]>({ default: () => [] })
const emit = defineEmits<{ error: [message: string | null] }>()
const { t } = useI18n()
const text = ref('')
/** What stayed in the box because it was wrong (not committed again until it is changed). */
const wrongText = ref('')
watch(text, value => value !== wrongText.value && (wrongText.value = ''))

/** Takes the typed text: good values become chips, the first wrong one stays to be fixed. */
function commit(): boolean {
  const parts = text.value.split(/[\s,;]+/).map(part => part.trim()).filter(Boolean)
  if (!parts.length) {
    text.value = ''
    emit('error', null)
    return false
  }
  const next = [...model.value]
  const wrong: string[] = []
  for (const part of parts) {
    const problem = props.check(part)
    if (problem) {
      wrong.push(part)
      emit('error', problem)
      continue
    }
    const value = props.normalise ? props.normalise(part) : part
    if (!next.includes(value)) next.push(value)
  }
  model.value = next
  wrongText.value = wrong.join(' ')
  text.value = wrongText.value
  if (!wrong.length) emit('error', null)
  return true
}
function onKey(event: KeyboardEvent) {
  if ([',', ' ', ';', 'Enter', 'Tab'].includes(event.key)) {
    if (event.key === 'Tab' && !text.value.trim()) return
    event.preventDefault()
    commit()
  } else if (event.key === 'Backspace' && !text.value && model.value.length) {
    event.preventDefault()
    text.value = model.value[model.value.length - 1]!
    model.value = model.value.slice(0, -1)
  }
}
function onPaste(event: ClipboardEvent) {
  const pasted = event.clipboardData?.getData('text') ?? ''
  if (!/[\s,;]/.test(pasted)) return
  event.preventDefault()
  text.value = `${text.value} ${pasted}`
  commit()
}
// Phone keyboards and pasted text often send no key events: a separator in the text commits too
watch(text, value => {
  if (/[s,;]/.test(value) && !wrongText.value) commit()
})
const remove = (value: string) => (model.value = model.value.filter(item => item !== value))
defineExpose({ commit })
</script>

<template>
  <div class="flex w-full flex-wrap items-center gap-1.5 rounded-md bg-default px-2 py-1.5 ring ring-accented ring-inset focus-within:ring-2 focus-within:ring-(--ui-border-inverted)">
    <UBadge v-for="value in model" :key="value" color="neutral" variant="soft" size="md" class="gap-1 rounded-md" :class="mono ? 'font-mono' : ''" dir="ltr">
      {{ value }}
      <button type="button" class="rounded-sm text-muted hover:text-highlighted focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)" :aria-label="t('common.removeItem', { name: value })" @click="remove(value)">
        <UIcon name="i-lucide-x" class="size-3.5" />
      </button>
    </UBadge>
    <input
      v-model="text"
      class="min-w-32 flex-1 bg-transparent py-0.5 text-sm text-highlighted outline-none placeholder:text-dimmed"
      :class="mono ? 'font-mono' : ''"
      :placeholder="model.length ? '' : placeholder"
      dir="ltr"
      @keydown="onKey"
      @paste="onPaste"
      @blur="commit"
    >
  </div>
</template>
