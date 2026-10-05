<!--
  The SQL editor (F12 M4, CodeMirror 6, owner-approved): the connection's own SQL dialect,
  completion of its schemas, tables and columns, line numbers, bracket matching, undo history.
  Ctrl / ⌘ + Enter runs the selection, or the statement the cursor is in. A database problem marks
  its line. Colours come from the theme (ink, muted, success for text, warning for numbers), so it
  follows light and dark mode.
-->
<script setup lang="ts">
import { autocompletion, closeBrackets, closeBracketsKeymap, completionKeymap } from '@codemirror/autocomplete'
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands'
import { MariaSQL, MSSQL, MySQL, PLSQL, PostgreSQL, sql, type SQLDialect } from '@codemirror/lang-sql'
import { bracketMatching, HighlightStyle, indentOnInput, syntaxHighlighting } from '@codemirror/language'
import { Compartment, EditorState, StateEffect, StateField } from '@codemirror/state'
import { Decoration, drawSelection, EditorView, highlightActiveLine, highlightActiveLineGutter, keymap, lineNumbers, placeholder } from '@codemirror/view'
import { tags } from '@lezer/highlight'
import { statementAt } from '#shared/utils/datasources/sql'
import type { DbEngine } from '#shared/utils/integrations/databases'

const props = defineProps<{ engine: DbEngine; schema: Record<string, string[]>; defaultSchema?: string; errorLine?: number | null; placeholderText?: string }>()
const model = defineModel<string>({ default: '' })
const emit = defineEmits<{ run: [] }>()

const DIALECTS: Record<DbEngine, SQLDialect> = { postgresql: PostgreSQL, mysql: MySQL, mariadb: MariaSQL, sqlserver: MSSQL, oracle: PLSQL }
const host = useTemplateRef<HTMLElement>('host')
let view: EditorView | null = null
const language = new Compartment()

// The line a database problem points at
const setErrorLine = StateEffect.define<number | null>()
const errorLineField = StateField.define({
  create: () => Decoration.none,
  update(decorations, transaction) {
    decorations = decorations.map(transaction.changes)
    for (const effect of transaction.effects) {
      if (!effect.is(setErrorLine)) continue
      const line = effect.value
      decorations = line && line <= transaction.state.doc.lines ? Decoration.set([Decoration.line({ class: 'cm-error-line' }).range(transaction.state.doc.line(line).from)]) : Decoration.none
    }
    return transaction.docChanged ? Decoration.none : decorations
  },
  provide: field => EditorView.decorations.from(field),
})

const highlight = HighlightStyle.define([
  { tag: [tags.keyword, tags.operatorKeyword, tags.modifier], color: 'var(--ui-text-highlighted)', fontWeight: '600' },
  { tag: [tags.string, tags.special(tags.string)], color: 'var(--ui-success)' },
  { tag: [tags.number, tags.bool, tags.null], color: 'var(--ui-warning)' },
  { tag: [tags.lineComment, tags.blockComment, tags.comment], color: 'var(--ui-text-dimmed)', fontStyle: 'italic' },
  { tag: [tags.typeName, tags.standard(tags.name)], color: 'var(--ui-text-muted)' },
  { tag: [tags.operator, tags.punctuation, tags.paren, tags.separator], color: 'var(--ui-text-muted)' },
  { tag: [tags.special(tags.name), tags.variableName], color: 'var(--ui-text)' },
])

const theme = EditorView.theme({
  '&': { height: '100%', fontSize: '12.5px', backgroundColor: 'transparent', color: 'var(--ui-text)' },
  '&.cm-focused': { outline: 'none' },
  '.cm-scroller': { fontFamily: 'var(--font-mono, ui-monospace, monospace)', lineHeight: '1.6' },
  '.cm-content': { caretColor: 'var(--ui-text-highlighted)', padding: '8px 0' },
  '.cm-cursor': { borderLeftColor: 'var(--ui-text-highlighted)' },
  '.cm-gutters': { backgroundColor: 'transparent', color: 'var(--ui-text-dimmed)', border: 'none', borderInlineEnd: '1px solid var(--ui-border)' },
  '.cm-lineNumbers .cm-gutterElement': { padding: '0 10px 0 12px', minWidth: '36px' },
  '.cm-activeLine': { backgroundColor: 'color-mix(in oklab, var(--ui-bg-elevated) 70%, transparent)' },
  '.cm-activeLineGutter': { backgroundColor: 'transparent', color: 'var(--ui-text-highlighted)' },
  '.cm-selectionBackground, &.cm-focused .cm-selectionBackground, .cm-content ::selection': { backgroundColor: 'var(--ui-bg-accented) !important' },
  '.cm-matchingBracket': { backgroundColor: 'var(--ui-bg-accented)', outline: '1px solid var(--ui-border-accented)' },
  '.cm-error-line': { backgroundColor: 'color-mix(in oklab, var(--ui-error) 14%, transparent)' },
  '.cm-placeholder': { color: 'var(--ui-text-dimmed)' },
  '.cm-tooltip': { backgroundColor: 'var(--ui-bg)', border: '1px solid var(--ui-border)', borderRadius: '8px', boxShadow: '0 8px 24px rgb(0 0 0 / 0.18)', overflow: 'hidden' },
  '.cm-tooltip-autocomplete > ul': { fontFamily: 'var(--font-mono, ui-monospace, monospace)', fontSize: '12px', maxHeight: '16rem' },
  '.cm-tooltip-autocomplete > ul > li': { padding: '3px 10px' },
  '.cm-tooltip-autocomplete > ul > li[aria-selected]': { backgroundColor: 'var(--ui-bg-accented)', color: 'var(--ui-text-highlighted)' },
  '.cm-completionDetail': { color: 'var(--ui-text-dimmed)', fontStyle: 'normal', marginInlineStart: '8px' },
})

const languageFor = () => sql({ dialect: DIALECTS[props.engine], schema: props.schema, defaultSchema: props.defaultSchema, upperCaseKeywords: true })

onMounted(() => {
  view = new EditorView({
    parent: host.value!,
    state: EditorState.create({
      doc: model.value,
      extensions: [
        lineNumbers(),
        highlightActiveLineGutter(),
        highlightActiveLine(),
        history(),
        drawSelection(),
        indentOnInput(),
        bracketMatching(),
        closeBrackets(),
        autocompletion({ activateOnTyping: true }),
        syntaxHighlighting(highlight),
        language.of(languageFor()),
        errorLineField,
        theme,
        placeholder(props.placeholderText ?? ''),
        EditorView.lineWrapping,
        keymap.of([
          { key: 'Mod-Enter', preventDefault: true, run: () => (emit('run'), true) },
          ...closeBracketsKeymap,
          ...completionKeymap,
          ...historyKeymap,
          indentWithTab,
          ...defaultKeymap,
        ]),
        EditorView.updateListener.of(update => {
          if (update.docChanged) model.value = update.state.doc.toString()
        }),
        EditorView.contentAttributes.of({ 'aria-label': 'SQL', spellcheck: 'false' }),
      ],
    }),
  })
})
onBeforeUnmount(() => view?.destroy())

// Outside changes (another tab, a history item) replace the text
watch(model, value => {
  if (view && value !== view.state.doc.toString()) view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: value } })
})
watch(() => [props.engine, props.schema, props.defaultSchema], () => view?.dispatch({ effects: language.reconfigure(languageFor()) }))
watch(() => props.errorLine, line => view?.dispatch({ effects: setErrorLine.of(line ?? null) }))

/** The selection, or else the statement the cursor is in, with where it starts in the text. */
function runText(): { text: string; from: number } | null {
  if (!view) return null
  const { from, to, head } = view.state.selection.main
  const doc = view.state.doc.toString()
  if (to > from && doc.slice(from, to).trim()) return { text: doc.slice(from, to), from }
  const statement = statementAt(doc, head)
  return statement ? { text: statement.text, from: statement.from } : null
}
/** The line of a position in the text (1-based). */
const lineAt = (position: number) => (view ? view.state.doc.lineAt(Math.min(position, view.state.doc.length)).number : 1)
function insert(text: string) {
  if (!view) return
  const { from, to } = view.state.selection.main
  view.dispatch({ changes: { from, to, insert: text }, selection: { anchor: from + text.length } })
  view.focus()
}
const hasSelection = () => !!view && !view.state.selection.main.empty
function goToLine(line: number) {
  if (!view) return
  const target = view.state.doc.line(Math.min(Math.max(1, line), view.state.doc.lines))
  view.dispatch({ selection: { anchor: target.from, head: target.to }, effects: EditorView.scrollIntoView(target.from, { y: 'center' }) })
  view.focus()
}
defineExpose({ runText, lineAt, insert, hasSelection, goToLine, focus: () => view?.focus() })
</script>

<template>
  <div ref="host" class="h-full min-h-0 overflow-hidden" dir="ltr" />
</template>
