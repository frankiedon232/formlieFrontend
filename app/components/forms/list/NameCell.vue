<!-- Form name with folder · tags, or the inline rename field (Enter / blur saves, Esc cancels). -->
<script setup lang="ts">
import type { FormSummary } from '#shared/types/forms'

const props = defineProps<{ form: FormSummary; editing: boolean; busy?: boolean }>()
const emit = defineEmits<{ save: [name: string]; cancel: [] }>()
const { t } = useI18n()

const draft = ref(props.form.name)
const input = useTemplateRef<{ inputRef: HTMLInputElement }>('input')
let settled = false

watch(
  () => props.editing,
  editing => {
    if (!editing) return
    settled = false
    draft.value = props.form.name
    nextTick(() => input.value?.inputRef?.select())
  },
  { immediate: true },
)

function save() {
  if (settled) return
  settled = true
  if (draft.value.trim() && draft.value.trim() !== props.form.name) emit('save', draft.value)
  else emit('cancel')
}
function cancel() {
  settled = true
  emit('cancel')
}
</script>

<template>
  <div class="min-w-0">
    <UInput
      v-if="editing"
      ref="input"
      v-model="draft"
      size="sm"
      maxlength="120"
      :aria-label="t('forms.actions.rename')"
      class="w-full max-w-sm"
      @keydown.enter.prevent="save"
      @keydown.esc.prevent.stop="cancel"
      @blur="save"
    />
    <template v-else>
      <p class="flex items-center gap-1.5 truncate font-medium text-highlighted">
        <UIcon v-if="busy" name="i-lucide-loader-circle" class="size-3.5 shrink-0 animate-spin text-muted" />
        <ULink :to="`/forms/${form.id}`" class="truncate text-highlighted hover:text-highlighted hover:underline">{{ form.name }}</ULink>
      </p>
      <p class="flex min-w-0 items-center gap-1.5 truncate text-xs text-muted">
        <span class="truncate">{{ form.folder?.name ?? t('forms.noFolder') }}</span>
        <span v-if="form.has_unpublished_changes">· {{ t('forms.unpublished') }}</span>
        <UBadge
          v-for="tag in form.tags.slice(0, 3)"
          :key="tag"
          :label="tag"
          color="neutral"
          variant="outline"
          size="sm"
          class="rounded-md"
        />
        <span v-if="form.tags.length > 3">+{{ form.tags.length - 3 }}</span>
      </p>
    </template>
  </div>
</template>
