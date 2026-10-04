<!--
  Email addresses as chips (owner, 2026-10-04: invitations take emails only). Typing a comma,
  space, semicolon or Enter, or pasting a list, turns each address into its own chip; chips wrap
  onto new lines. Invalid addresses are red with the reason; duplicates are merged; × or Backspace
  removes a chip. v-model: every entry, with `valid` set.
-->
<script setup lang="ts">
import type { EmailChip } from '#shared/types/forms'

defineProps<{ placeholder?: string; disabled?: boolean }>()
const chips = defineModel<EmailChip[]>({ required: true })
const { t } = useI18n()

const EMAIL = /^[^\s@,;<>"]+@[^\s@,;<>"]+\.[a-z]{2,}$/i
const draft = ref('')
const input = useTemplateRef<HTMLInputElement>('input')

/** Text → chips: split on comma, space, semicolon and new lines; lower case; no duplicates. */
function add(text: string) {
  const next = [...chips.value]
  for (const part of text.split(/[\s,;]+/).map(item => item.trim().replace(/^mailto:/i, '')).filter(Boolean)) {
    const value = part.toLowerCase()
    if (!next.some(chip => chip.value === value)) next.push({ value, valid: EMAIL.test(value) })
  }
  chips.value = next
}
function typed(event: Event) {
  const value = (event.target as HTMLInputElement).value
  if (/[\s,;]/.test(value)) {
    add(value)
    draft.value = ''
  } else draft.value = value
}
function keydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    event.preventDefault()
    if (draft.value.trim()) add(draft.value)
    draft.value = ''
  } else if (event.key === 'Backspace' && !draft.value && chips.value.length) chips.value = chips.value.slice(0, -1)
}
function pasted(event: ClipboardEvent) {
  const text = event.clipboardData?.getData('text') ?? ''
  if (!text) return
  event.preventDefault()
  add(`${draft.value} ${text}`)
  draft.value = ''
}
function blurred() {
  if (draft.value.trim()) add(draft.value)
  draft.value = ''
}
const remove = (value: string) => (chips.value = chips.value.filter(chip => chip.value !== value))
</script>

<template>
  <div
    class="flex min-h-20 w-full cursor-text flex-wrap content-start items-start gap-1.5 rounded-md border border-default bg-default p-2 focus-within:ring-2 focus-within:ring-inverted"
    :class="disabled ? 'pointer-events-none opacity-60' : ''"
    @click="input?.focus()"
  >
    <span
      v-for="chip in chips"
      :key="chip.value"
      class="inline-flex max-w-full items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-xs"
      :class="chip.valid ? 'border-default bg-elevated text-highlighted' : 'border-error/50 bg-error/10 text-error'"
      :title="chip.valid ? chip.value : t('share.invite.notEmail')"
    >
      <UIcon v-if="!chip.valid" name="i-lucide-circle-alert" class="size-3.5 shrink-0" />
      <span class="truncate" dir="ltr">{{ chip.value }}</span>
      <button
        type="button"
        class="ms-0.5 rounded-full p-0.5 hover:bg-accented focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
        :disabled="disabled"
        :aria-label="t('share.invite.removeEmail', { email: chip.value })" @click.stop="remove(chip.value)">
        <UIcon name="i-lucide-x" class="block size-3" />
      </button>
    </span>
    <input
      ref="input"
      :value="draft"
      type="text"
      inputmode="email"
      :disabled="disabled"
      autocomplete="off"
      :placeholder="chips.length ? '' : placeholder"
      :aria-label="placeholder"
      class="min-w-48 flex-1 bg-transparent px-1 py-0.5 text-sm text-highlighted outline-none placeholder:text-dimmed"
      @input="typed"
      @keydown="keydown"
      @paste="pasted"
      @blur="blurred"
    >
  </div>
</template>
