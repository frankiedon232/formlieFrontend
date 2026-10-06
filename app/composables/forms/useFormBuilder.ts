import type { InjectionKey } from 'vue'
import { newId, keyFromLabel, fieldKey, allFields, type FormField, type FormPage } from '#shared/utils/forms/build'
import type { OptionList, SavedField } from '#shared/types/forms'
import { isInputField, type FieldType } from '#shared/utils/forms/fields'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'

/**
 * Builder state + every edit (FRONTEND-SPEC §6): pages → rows → fields on a 12-column grid.
 * Every mutation records an undo step first. The page creates it with `useFormBuilder()` and
 * children read it with `useBuilder()` (provide / inject, one builder per page).
 */
export function useFormBuilder() {
  const { t } = useI18n()
  const toast = useToast()
  const schema = ref<FormSchemaV1 | null>(null)
  const selected = ref<string[]>([])
  const pageId = ref<string | null>(null)
  /**
   * Keys any published version used (owner, 2026-10-06: clean keys like first_name). Those are fixed
   * (responses, endpoints, storage tables and exports know them) and never reused for another
   * question; every other key follows its label: "First name" → first_name, a clash → first_name_2.
   */
  const publishedKeys = ref<Set<string>>(new Set())
  /** A clean key for a new field: from its label, unique among the fields and every published key. */
  const newKey = (label: string, except?: string) => keyFromLabel(label, [...fields.value.filter(f => f.id !== except).map(f => f.key), ...publishedKeys.value])
  /** A field is being dragged (the canvas shows where it can land). */
  const dragging = ref(false)

  const history = useFormHistory(
    () => schema.value,
    value => {
      schema.value = value
      selected.value = selected.value.filter(id => findField(id))
      if (!schema.value?.pages.some(p => p.id === pageId.value))
        pageId.value = schema.value?.pages[0]?.id ?? null
    },
  )

  function load(value: FormSchemaV1) {
    schema.value = value
    pageId.value = value.pages[0]?.id ?? null
    selected.value = []
    history.reset()
  }

  const pages = computed(() => schema.value?.pages ?? [])
  const page = computed(() => pages.value.find(p => p.id === pageId.value) ?? pages.value[0] ?? null)
  const fields = computed(() => (schema.value ? allFields(schema.value) : []))
  const selectedFields = computed(() =>
    selected.value.map(id => findField(id)?.field).filter((f): f is FormField => !!f),
  )

  /** Where a field lives: its page, row and positions. */
  function findField(id: string) {
    for (const [pi, p] of (schema.value?.pages ?? []).entries())
      for (const [ri, row] of p.rows.entries()) {
        const fi = row.fields.findIndex(f => f.id === id)
        if (fi >= 0)
          return { page: p, pageIndex: pi, row, rowIndex: ri, field: row.fields[fi]!, fieldIndex: fi }
      }
    return null
  }

  const dropEmptyRows = () => schema.value?.pages.forEach(p => (p.rows = p.rows.filter(r => r.fields.length)))

  // ── Creating ─────────────────────────────────────────────────────────────────────
  function createField(type: FieldType): FormField {
    const { defaults } = FIELD_REGISTRY[type]
    // Sections start untitled so the canvas shows the "Section title" placeholder.
    const label = type === 'section' ? '' : t(`builder.field.${type}`)
    const id = newId('fld')
    const field: FormField = {
      id,
      key: newKey(label || type),
      type,
      label,
      // New fields start at half width (owner) so they pair up when dropped side by side; layout
      // blocks (heading, paragraph, divider, image) span the row. The width stays adjustable.
      width: isInputField(type) ? 6 : 12,
      required: false,
      ...structuredClone(defaults),
    }
    if (field.options)
      field.options = field.options.map((_, i) => ({
        value: `option_${i + 1}`,
        label: t('builder.defaults.option', { n: i + 1 }),
      }))
    if (type === 'matrix')
      field.props = { ...field.props, rows: [1, 2, 3].map(n => t('builder.defaults.row', { n })) }
    return field
  }

  /** A saved field as a fresh copy: new id, unique key. */
  function createFromSaved(saved: SavedField): FormField {
    const id = newId('fld')
    const field = structuredClone(toRaw(saved.field)) as Omit<FormField, 'id'>
    return { ...field, id, key: newKey(field.label || field.type) }
  }

  /** A choice field filled from an option list (a copy of its options; the list id is kept). */
  function createFromList(list: OptionList, type: FieldType = 'dropdown'): FormField {
    const field = createField(type)
    field.label = list.name
    field.key = newKey(list.name)
    field.options = structuredClone(toRaw(list.options))
    field.option_set_id = list.id
    return field
  }

  /** Puts a field in its own row, after the selected field, else at the end of the page. */
  function place(field: FormField, target?: { pageId: string; rowIndex: number }): FormField | null {
    if (!schema.value || !page.value) return null
    history.record()
    const anchor = selected.value.length === 1 ? findField(selected.value[0]!) : null
    const destPage = target
      ? schema.value.pages.find(p => p.id === target.pageId)!
      : (anchor?.page ?? page.value)
    const index = target?.rowIndex ?? (anchor ? anchor.rowIndex + 1 : destPage.rows.length)
    destPage.rows.splice(index, 0, { id: newId('row'), fields: [field] })
    pageId.value = destPage.id
    selected.value = [field.id]
    return field
  }
  const addField = (type: FieldType, target?: { pageId: string; rowIndex: number }) =>
    schema.value ? place(createField(type), target) : null

  // ── Editing ──────────────────────────────────────────────────────────────────────
  function updateField(id: string, patch: Partial<FormField>, group?: string) {
    const found = findField(id)
    if (!found) return
    history.record(group ?? `field:${id}:${Object.keys(patch).join(',')}`)
    const oldKey = found.field.key
    Object.assign(found.field, patch)
    // Formulas refer to keys: follow a renamed key so calculations keep working.
    if (patch.key && patch.key !== oldKey)
      for (const f of fields.value)
        if (typeof f.props?.formula === 'string' && f.props.formula.includes(`{${oldKey}}`))
          f.props = { ...f.props, formula: f.props.formula.replaceAll(`{${oldKey}}`, `{${patch.key}}`) }
  }

  /** New label; a key no published version used follows it: "Full name" → full_name. */
  function renameField(id: string, label: string) {
    const found = findField(id)
    if (!found) return
    const { field } = found
    const others = fields.value.filter(f => f.id !== id).map(f => f.key)
    // Only a key the field got automatically follows (a clean one, or the older label_suffix kind)
    const auto = field.key === newKey(field.label || field.type, id) || field.key === fieldKey(field.label || field.type, id, others)
    const follows = !publishedKeys.value.has(field.key) && auto
    updateField(id, follows ? { label, key: newKey(label || field.type, id) } : { label }, `field:${id}:label`)
  }

  function updateProps(id: string, patch: Record<string, unknown>, group?: string) {
    const found = findField(id)
    if (!found) return
    history.record(group ?? `props:${id}:${Object.keys(patch).join(',')}`)
    found.field.props = { ...found.field.props, ...patch }
  }

  function setWidth(ids: string[], width: number) {
    history.record()
    for (const id of ids) {
      const found = findField(id)
      if (found) found.field.width = width
    }
  }

  function duplicate(ids = selected.value) {
    if (!ids.length) return
    history.record()
    const copies: string[] = []
    for (const id of ids) {
      const found = findField(id)
      if (!found) continue
      const copyId = newId('fld')
      const copy: FormField = {
        ...structuredClone(toRaw(found.field)),
        id: copyId,
        key: newKey(found.field.label || found.field.type),
      }
      found.page.rows.splice(found.rowIndex + 1, 0, { id: newId('row'), fields: [copy] })
      copies.push(copy.id)
    }
    selected.value = copies
  }

  /** Removes fields; resolves the undo step so the caller can offer "Undo" in a toast. */
  function remove(ids = selected.value): number {
    const targets = ids.filter(id => findField(id))
    if (!targets.length) return 0
    history.record()
    for (const id of targets) {
      const found = findField(id)
      found?.row.fields.splice(found.fieldIndex, 1)
    }
    dropEmptyRows()
    selected.value = []
    return targets.length
  }

  /** Delete + a toast with Undo (FRONTEND-SPEC §6: "Del with undo toast"). */
  function removeWithUndo(ids = selected.value) {
    const count = remove(ids)
    if (!count) return
    toast.add({
      title: t('builder.toast.deleted', { count }, count),
      icon: 'i-lucide-trash-2',
      color: 'neutral',
      actions: [
        {
          label: t('builder.undo'),
          color: 'neutral',
          variant: 'outline',
          onClick: () => void history.undo(),
        },
      ],
    })
  }

  /** Drops from the palette or other rows land as fields in the page's row list: wrap them in rows. */
  function normaliseRows(target: FormPage) {
    target.rows = target.rows
      .map(row => ('fields' in row ? row : { id: newId('row'), fields: [row as unknown as FormField] }))
      .filter(row => row.fields.length)
    // A field dropped next to others: share the row evenly when they no longer fit (½ ½, ⅓ ⅓ ⅓, ¼ × 4).
    for (const row of target.rows) {
      const total = row.fields.reduce((sum, f) => sum + (f.width ?? 12), 0)
      if (total > 12 && row.fields.length <= 4) {
        const even = 12 / row.fields.length
        for (const f of row.fields) f.width = even
      }
    }
  }

  /** Keyboard move (Alt+↑/↓): within a row first, then row by row, then across pages. */
  function move(id: string, direction: -1 | 1) {
    const found = findField(id)
    if (!found || !schema.value) return
    const { page: p, pageIndex, row, rowIndex, fieldIndex } = found
    history.record()
    if (row.fields.length > 1 && fieldIndex + direction >= 0 && fieldIndex + direction < row.fields.length) {
      row.fields.splice(fieldIndex + direction, 0, ...row.fields.splice(fieldIndex, 1))
      return
    }
    row.fields.splice(fieldIndex, 1)
    const emptied = row.fields.length === 0
    const fieldRow = { id: newId('row'), fields: [found.field] }
    // Up: just before the row (or before the previous one if this row is now empty).
    // Down: just after the row (or after the next one if this row is now empty).
    const target = direction < 0 ? rowIndex - (emptied ? 1 : 0) : rowIndex + (emptied ? 2 : 1)
    if (target >= 0 && target <= p.rows.length) p.rows.splice(target, 0, fieldRow)
    else {
      const next = schema.value.pages[pageIndex + direction]
      if (next) {
        if (direction > 0) next.rows.unshift(fieldRow)
        else next.rows.push(fieldRow)
        pageId.value = next.id
      } else p.rows.splice(direction > 0 ? p.rows.length : 0, 0, fieldRow)
    }
    dropEmptyRows()
  }

  function moveToPage(ids: string[], targetPageId: string) {
    const target = schema.value?.pages.find(p => p.id === targetPageId)
    if (!target) return
    history.record()
    for (const id of ids) {
      const found = findField(id)
      if (!found || found.page.id === targetPageId) continue
      found.row.fields.splice(found.fieldIndex, 1)
      target.rows.push({ id: newId('row'), fields: [found.field] })
    }
    dropEmptyRows()
    pageId.value = targetPageId
  }

  // ── Pages ────────────────────────────────────────────────────────────────────────
  function addPage(): FormPage | null {
    if (!schema.value) return null
    history.record()
    const created: FormPage = {
      id: newId('pg'),
      title: t('builder.page.default', { n: pages.value.length + 1 }),
      rows: [],
    }
    const index = page.value ? schema.value.pages.indexOf(page.value) + 1 : schema.value.pages.length
    schema.value.pages.splice(index, 0, created)
    pageId.value = created.id
    selected.value = []
    return created
  }

  function renamePage(id: string, title: string) {
    const target = schema.value?.pages.find(p => p.id === id)
    if (!target || target.title === title) return
    history.record(`page:${id}:title`)
    target.title = title
  }

  function movePage(id: string, direction: -1 | 1) {
    if (!schema.value) return
    const index = schema.value.pages.findIndex(p => p.id === id)
    const to = index + direction
    if (index < 0 || to < 0 || to >= schema.value.pages.length) return
    history.record()
    schema.value.pages.splice(to, 0, ...schema.value.pages.splice(index, 1))
  }

  function removePage(id: string) {
    if (!schema.value || schema.value.pages.length < 2) return
    history.record()
    const index = schema.value.pages.findIndex(p => p.id === id)
    schema.value.pages.splice(index, 1)
    pageId.value = schema.value.pages[Math.max(0, index - 1)]!.id
    selected.value = []
  }

  // ── Selection ────────────────────────────────────────────────────────────────────
  function select(id: string, mode: 'only' | 'toggle' | 'range' = 'only') {
    if (mode === 'toggle')
      selected.value = selected.value.includes(id)
        ? selected.value.filter(s => s !== id)
        : [...selected.value, id]
    else if (mode === 'range' && selected.value.length) {
      const order = (page.value?.rows ?? []).flatMap(r => r.fields.map(f => f.id))
      const from = order.indexOf(selected.value.at(-1)!)
      const to = order.indexOf(id)
      selected.value = from < 0 || to < 0 ? [id] : order.slice(Math.min(from, to), Math.max(from, to) + 1)
    } else selected.value = [id]
  }

  return {
    schema,
    pages,
    page,
    pageId,
    fields,
    selected,
    selectedFields,
    history,
    publishedKeys,
    dragging,
    load,
    findField,
    createField,
    createFromSaved,
    createFromList,
    place,
    addField,
    updateField,
    renameField,
    updateProps,
    setWidth,
    duplicate,
    remove,
    removeWithUndo,
    normaliseRows,
    move,
    moveToPage,
    addPage,
    renamePage,
    movePage,
    removePage,
    select,
    dropEmptyRows,
  }
}

export type FormBuilder = ReturnType<typeof useFormBuilder>
const BUILDER_KEY: InjectionKey<FormBuilder> = Symbol('form-builder')

export const provideFormBuilder = (builder: FormBuilder) => provide(BUILDER_KEY, builder)

/** The builder of the current page (components inside the builder only). */
export function useBuilder(): FormBuilder {
  const builder = inject(BUILDER_KEY)
  if (!builder) throw new Error('useBuilder() must be used inside the form builder page.')
  return builder
}

/** The builder when inside the editor, else null (e.g. the read-only preview on the overview). */
export const useBuilderIfAny = (): FormBuilder | null => inject(BUILDER_KEY, null)
