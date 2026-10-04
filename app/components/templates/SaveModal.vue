<!--
  Save a form as a workspace template (F9): its current draft, questions, logic, calculations and
  design, becomes a template everyone in the workspace can start from. Responses never go along.
-->
<script setup lang="ts">
import { z } from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'
import { TEMPLATE_CATEGORIES, TEMPLATE_CATEGORY_KEYS } from '#shared/templates/categories'

const props = defineProps<{ form: { id: string; name: string } | null }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const templates = useTemplates()

const schema = z.object({
  name: z.string().trim().min(1, t('templates.nameRequired')).max(80),
  description: z.string().trim().max(300),
  category: z.enum(TEMPLATE_CATEGORY_KEYS),
})
const state = reactive<{
  name: string
  description: string
  category: (typeof TEMPLATE_CATEGORY_KEYS)[number]
}>({
  name: '',
  description: '',
  category: 'business',
})
// Immediate: in the builder the dialog loads lazily and is already open when it mounts.
watch(
  open,
  value => {
    if (!value || !props.form) return
    state.name = props.form.name.slice(0, 80)
    state.description = ''
  },
  { immediate: true },
)
const categories = computed(() =>
  TEMPLATE_CATEGORIES.map(c => ({ value: c.key, label: t(`templates.categories.${c.key}`), icon: c.icon })),
)

const { busy, run } = useBusy()
async function submit(event: FormSubmitEvent<z.output<typeof schema>>) {
  if (!props.form) return
  const saved = await run(() => templates.saveFromForm({ form_id: props.form!.id, ...event.data }))
  if (saved) open.value = false
}
</script>

<template>
  <AppModal
    v-model:open="open"
    :title="t('templates.saveTitle')"
    :description="t('templates.saveDesc')"
    :dismissible="!busy"
  >
    <template #body>
      <UForm
        id="save-template-form"
        :schema="schema"
        :state="state"
        class="flex flex-col gap-4"
        @submit="submit"
      >
        <UFormField name="name" :label="t('templates.col.name')" required>
          <UInput v-model="state.name" maxlength="80" class="w-full" autofocus />
        </UFormField>
        <UFormField
          name="description"
          :label="t('templates.description')"
          :hint="`${state.description.length}/300`"
        >
          <UTextarea
            v-model="state.description"
            :rows="2"
            autoresize
            maxlength="300"
            class="w-full"
            :placeholder="t('templates.descriptionPlaceholder')"
          />
        </UFormField>
        <UFormField name="category" :label="t('templates.col.category')" required>
          <USelectMenu v-model="state.category" :items="categories" value-key="value" class="w-full" />
        </UFormField>
      </UForm>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton
          :label="t('common.cancel')"
          color="neutral"
          variant="outline"
          :disabled="busy"
          @click="open = false"
        />
        <UButton
          type="submit"
          form="save-template-form"
          :label="t('templates.saveButton')"
          icon="i-lucide-layout-template"
          color="neutral"
          :loading="busy"
        />
      </div>
    </template>
  </AppModal>
</template>
