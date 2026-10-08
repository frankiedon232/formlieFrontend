<!--
  Option list editor → Size (F15 M5, owner 2026-10-08: "do 1 and 2", and say first what choosing Large
  means). Standard: up to 20,000 options, copied into each form, everything instant. Large: up to
  200,000, kept on the server and loaded level by level as people choose. Switching to Large explains
  what changes and asks first; back to Standard only while the list fits 20,000.
-->
<script setup lang="ts">
import { MAX_LARGE_OPTIONS, MAX_OPTIONS } from '#shared/utils/forms/options'

const large = defineModel<boolean>('large', { required: true })
const props = defineProps<{ count: number }>()
const { t } = useI18n()
const { number } = useFormat()
const confirm = useConfirm()

const open = ref(false)
const sizes = computed(() => [
  { value: 'standard', label: t('optionSets.large.standard'), icon: 'i-lucide-list' },
  { value: 'large', label: t('optionSets.large.large'), icon: 'i-lucide-server' },
])
const tooBigForStandard = computed(() => props.count > MAX_OPTIONS)
const ask = () => (open.value = true)
function accept() {
  large.value = true
  open.value = false
}
async function pick(value: string | number) {
  if (value === 'large' && !large.value) return ask()
  if (value === 'standard' && large.value) {
    if (tooBigForStandard.value) return
    const ok = await confirm({ title: t('optionSets.large.toStandardTitle'), description: t('optionSets.large.toStandardDesc'), confirmLabel: t('optionSets.large.toStandard') })
    if (ok) large.value = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-2 rounded-lg border border-default p-3">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
      <div class="flex shrink-0 flex-col gap-1">
        <span class="text-xs font-medium text-highlighted">{{ t('optionSets.large.size') }}</span>
        <UTooltip :text="large && tooBigForStandard ? t('optionSets.large.cannotStandard', { max: number(MAX_OPTIONS) }) : undefined" :disabled="!(large && tooBigForStandard)">
          <UTabs :model-value="large ? 'large' : 'standard'" :items="sizes" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" class="w-fit" @update:model-value="pick" />
        </UTooltip>
      </div>
      <p class="min-w-0 flex-1 text-xs text-muted">{{ large ? t('optionSets.large.largeHint', { n: number(count), max: number(MAX_LARGE_OPTIONS) }) : t('optionSets.large.standardHint', { n: number(count), max: number(MAX_OPTIONS) }) }}</p>
    </div>

    <AppModal v-model:open="open" :title="t('optionSets.large.askTitle')" :description="t('optionSets.large.askDesc')">
      <template #body><OptionSetsLargePoints /></template>
      <template #footer>
        <div class="flex w-full justify-end gap-2">
          <UButton :label="t('optionSets.large.keepStandard')" color="neutral" variant="outline" @click="open = false" />
          <UButton :label="t('optionSets.large.makeLarge')" icon="i-lucide-server" color="neutral" @click="accept" />
        </div>
      </template>
    </AppModal>
  </div>
</template>
