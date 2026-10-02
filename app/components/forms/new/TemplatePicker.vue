<!-- "From a template" tab of New form: starter templates as selectable cards. -->
<script setup lang="ts">
import { STARTER_TEMPLATES, type StarterTemplateKey } from '#shared/utils/templates/starters'

const model = defineModel<StarterTemplateKey>({ required: true })
const { t } = useI18n()

const templates = computed(() =>
  STARTER_TEMPLATES.map(item => ({
    value: item.key,
    label: t(`templates.starter.${item.key}.name`),
    description: t('onboarding.firstForm.fields', { count: item.fields }, item.fields),
    iconName: item.icon,
  })),
)
</script>

<template>
  <URadioGroup
    v-model="model"
    :items="templates"
    variant="card"
    color="neutral"
    indicator="hidden"
    :aria-label="t('forms.new.template')"
    :ui="{
      fieldset: 'grid gap-2 sm:grid-cols-2',
      item: 'items-start',
      wrapper: 'w-full items-start text-start',
    }"
  >
    <template #label="{ item }">
      <span class="flex items-center gap-3">
        <span class="flex size-9 shrink-0 items-center justify-center rounded-md border border-default bg-elevated/50">
          <UIcon :name="item.iconName" class="size-4 text-highlighted" />
        </span>
        <span class="font-medium text-highlighted">{{ item.label }}</span>
      </span>
    </template>
    <template #description="{ item }">
      <span class="ms-12 block text-xs text-muted">{{ item.description }}</span>
    </template>
  </URadioGroup>
</template>
