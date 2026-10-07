<!--
  One field on the canvas: the real field inside a selectable frame. The field works, so you can
  try it while designing (what you type is never saved); double-click its label (or press F2)
  to rename it in place.
  Hover → hairline border; selected → dark outline (monochrome, docs/design). The type pill and
  the drag · duplicate · delete · ⋯ buttons live in FieldToolbar.
  Click selects, Ctrl/⌘ toggles, Shift selects a range; Enter / Space select from the keyboard.
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{
  field: FormField
  selected: boolean
  issue?: string
  labelPosition?: 'top' | 'left'
}>()
const emit = defineEmits<{ remove: [] }>()
const { t } = useI18n()
const builder = useBuilder()

function onSelect(event: MouseEvent | KeyboardEvent) {
  builder.select(
    props.field.id,
    event.shiftKey ? 'range' : event.metaKey || event.ctrlKey ? 'toggle' : 'only',
  )
}

// Trying the field out: a local answer only, reset when the field type changes. Fields from a list
// share theirs with the canvas, so a level narrows the next as in the form (F15 M2).
const local = ref<unknown>(props.field.default ?? null)
const canvas = inject(RENDERER_ANSWERS, null)
const shared = computed(() => !!canvas && !!props.field.option_set_id)
const trial = computed({
  get: () => (shared.value ? (canvas!.answers.value[props.field.key] ?? null) : local.value),
  set: value => (shared.value ? (canvas!.answers.value = { ...canvas!.answers.value, [props.field.key]: value }) : (local.value = value)),
})
watch(
  () => props.field.type,
  () => (trial.value = null),
)

// Inline rename (double-click the label, or F2 on the selected field).
const renaming = ref(false)
const draft = ref('')
const input = useTemplateRef<{ inputRef?: HTMLInputElement }>('rename')
async function startRename() {
  if (!hasControl(props.field.type, 'label')) return
  builder.select(props.field.id)
  draft.value = props.field.label
  renaming.value = true
  await nextTick()
  input.value?.inputRef?.select()
}
function commitRename() {
  if (!renaming.value) return
  renaming.value = false
  if (draft.value !== props.field.label) builder.renameField(props.field.id, draft.value)
}
defineExpose({ startRename })

// Section description: double-click to edit in place (Enter on a new line, Esc to cancel).
const editingDesc = ref(false)
const descDraft = ref('')
const descInput = useTemplateRef<{ textareaRef?: HTMLTextAreaElement }>('desc')
async function startDesc() {
  builder.select(props.field.id)
  descDraft.value = String(props.field.props?.description ?? '')
  editingDesc.value = true
  await nextTick()
  descInput.value?.textareaRef?.focus()
}
function commitDesc() {
  if (!editingDesc.value) return
  editingDesc.value = false
  if (descDraft.value !== (props.field.props?.description ?? ''))
    builder.updateProps(props.field.id, { description: descDraft.value.trim() })
}

</script>

<template>
  <div
    class="group/field relative rounded-lg border px-3 py-2.5 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--ui-border-inverted)"
    :class="
      selected
        ? 'border-(--ui-border-inverted) bg-elevated/30 ring-1 ring-(--ui-border-inverted)'
        : issue
          ? 'border-warning/60 hover:border-warning'
          : 'border-transparent hover:border-default'
    "
    role="group"
    tabindex="0"
    :aria-current="selected || undefined"
    :aria-label="
      t('builder.fieldAria', {
        label: field.label || t(`builder.field.${field.type}`),
        type: t(`builder.field.${field.type}`),
      })
    "
    :data-field-id="field.id"
    @click.stop="onSelect"
    @keydown.enter.self.prevent="onSelect"
    @keydown.space.self.prevent="onSelect"
    @keydown.f2.self.prevent="startRename"
  >
    <FormsBuilderFieldToolbar :field="field" :selected="selected" :issue="issue" @remove="emit('remove')" />

    <!-- Paragraph and image blocks are edited right on the canvas. -->
    <FormsBuilderBlockParagraph v-if="field.type === 'paragraph'" :field="field" />
    <FormsBuilderBlockImage v-else-if="field.type === 'image'" :field="field" :selected="selected" />

    <!-- Everything else: the real field, as respondents see it, and it works, so it can be tried out. -->
    <FormsRendererField v-else v-model="trial" :field="field" mode="builder" :label-position="labelPosition">
      <template v-if="renaming" #label>
        <UInput
          ref="rename"
          v-model="draft"
          :size="field.type === 'section' ? 'md' : 'sm'"
          maxlength="500"
          class="min-w-0 flex-1"
          :aria-label="field.type === 'section' ? t('builder.inspector.title') : t('builder.inspector.label')"
          @click.stop
          @keydown.enter.prevent="commitRename"
          @keydown.esc.stop.prevent="renaming = false"
          @blur="commitRename"
        />
      </template>
      <template v-else-if="hasControl(field.type, 'label')" #label>
        <span
          class="min-w-0 cursor-text"
          :class="[
            field.type === 'section' ? '' : 'text-sm font-medium text-highlighted',
            field.type === 'section' && !field.label ? 'text-dimmed' : '',
          ]"
          :title="t('builder.renameHint')"
          @dblclick.stop="startRename"
        >
          {{
            field.label ||
            (field.type === 'section' ? t('builder.blocks.sectionPlaceholder') : t('builder.untitled'))
          }}
          <span v-if="field.required" class="text-error" aria-hidden="true">*</span>
        </span>
      </template>
      <template v-if="field.type === 'section'" #description>
        <UTextarea
          v-if="editingDesc"
          ref="desc"
          v-model="descDraft"
          :rows="2"
          autoresize
          size="sm"
          class="w-full"
          :aria-label="t('builder.inspector.description')"
          @click.stop
          @keydown.esc.stop.prevent="editingDesc = false"
          @blur="commitDesc"
        />
        <p
          v-else
          class="cursor-text text-sm whitespace-pre-line"
          :class="field.props?.description ? 'text-muted' : 'text-dimmed italic'"
          :title="t('builder.renameHint')"
          @dblclick.stop="startDesc"
        >
          {{ field.props?.description || t('builder.blocks.descriptionPlaceholder') }}
        </p>
      </template>
    </FormsRendererField>
  </div>
</template>
