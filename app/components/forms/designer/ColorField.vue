<!--
  Colour token: swatch button opening Nuxt UI's colour picker, plus a hex box for typing or
  pasting. Optional `against` colour shows a contrast warning below WCAG AA (4.5 : 1).
-->
<script setup lang="ts">
const props = defineProps<{ label: string; modelValue: string; against?: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const { t } = useI18n()

const draft = ref(props.modelValue)
watch(
  () => props.modelValue,
  value => (draft.value = value),
)
const valid = (value: string) => /^#[0-9a-f]{6}$/i.test(value)
function typed(value: string) {
  draft.value = value.startsWith('#') ? value : `#${value}`
  if (valid(draft.value)) emit('update:modelValue', draft.value.toLowerCase())
}
const ratio = computed(() => (props.against && valid(props.modelValue) ? contrastRatio(props.modelValue, props.against) : null))
</script>

<template>
  <UFormField
    :label="label"
    :error="!valid(draft) ? t('designer.colorInvalid') : undefined"
    :hint="ratio !== null && ratio < 4.5 ? t('designer.lowContrast', { ratio: ratio.toFixed(1) }) : undefined"
    :ui="{ hint: 'text-warning text-xs' }"
  >
    <div class="flex items-center gap-2">
      <UPopover>
        <UButton
          color="neutral"
          variant="outline"
          square
          class="size-8 shrink-0 p-1"
          :aria-label="t('designer.pickColor', { name: label })"
        >
          <span class="size-full rounded-sm border border-default" :style="{ background: modelValue }" />
        </UButton>
        <template #content>
          <UColorPicker
            :model-value="modelValue"
            format="hex"
            class="p-2"
            @update:model-value="v => v && valid(v) && emit('update:modelValue', v.toLowerCase())"
          />
        </template>
      </UPopover>
      <UInput
        :model-value="draft"
        maxlength="7"
        class="min-w-0 flex-1 font-mono"
        :aria-label="label"
        @update:model-value="v => typed(String(v))"
      />
    </div>
  </UFormField>
</template>
