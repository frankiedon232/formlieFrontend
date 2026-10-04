<!-- Step 5, start a first form: blank or one of the starter templates. Finishing opens it. -->
<script setup lang="ts">
import type { OnboardingFirstForm } from '#shared/types/onboarding'
import { STARTER_TEMPLATES, type StarterTemplateKey } from '#shared/utils/templates/starters'

const firstForm = defineModel<OnboardingFirstForm>({ required: true })
const emit = defineEmits<{ submit: [] }>()
const { t } = useI18n()

/** One radio value per card: `blank` or the template key. */
const selected = computed({
  get: () =>
    (firstForm.value.choice === 'template' ? firstForm.value.template_key : firstForm.value.choice) ??
    undefined,
  set: (value: string | undefined) => {
    if (!value) return
    firstForm.value =
      value === 'blank'
        ? { choice: 'blank', template_key: null }
        : { choice: 'template', template_key: value as StarterTemplateKey }
  },
})

const options = computed(() => [
  {
    value: 'blank',
    label: t('onboarding.firstForm.blank'),
    description: t('onboarding.firstForm.blankDesc'),
    iconName: 'i-lucide-file-plus',
  },
  ...STARTER_TEMPLATES.map(template => ({
    value: template.key,
    label: t(`templates.starter.${template.key}.name`),
    description: t('onboarding.firstForm.fields', { count: template.fields }, template.fields),
    iconName: template.icon,
  })),
])
</script>

<template>
  <UForm id="onboarding-step" :state="firstForm" @submit="emit('submit')">
    <URadioGroup
      v-model="selected"
      :items="options"
      variant="card"
      color="neutral"
      indicator="hidden"
      :aria-label="t('onboarding.steps.first_form.title')"
      :ui="{
        fieldset: 'grid gap-2 sm:grid-cols-2',
        item: 'items-start',
        wrapper: 'w-full items-start text-start',
      }"
    >
      <template #label="{ item }">
        <span class="flex items-center gap-3">
          <span
            class="flex size-9 shrink-0 items-center justify-center rounded-md border border-default bg-elevated/50"
          >
            <UIcon :name="item.iconName" class="size-4 text-highlighted" />
          </span>
          <span class="font-medium text-highlighted">{{ item.label }}</span>
        </span>
      </template>
      <template #description="{ item }">
        <span class="ms-12 block text-xs text-muted">{{ item.description }}</span>
      </template>
    </URadioGroup>
    <p class="mt-4 text-sm text-muted">{{ t('onboarding.firstForm.hint') }}</p>
  </UForm>
</template>
