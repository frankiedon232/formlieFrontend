/**
 * The explorer's right-click menus (F12 M3, owner 2026-10-05): every action of the page in reach
 * of the pointer. Tree: a schema (New table here), a table (open, structure, columns and indexes,
 * rename, empty, delete, export), a column (change, delete). Rows: open, edit, delete, copy the
 * value or the row. The table area: refresh, add row, export, structure changes. Structure
 * changes only where they are allowed (their own tables, Full access); an action on another
 * table opens it first, then runs.
 */
import type { ContextMenuItem } from '@nuxt/ui'
import type { ExplorerNode, TableExport, TableRow, TableStructure } from '#shared/types/explorer'
import { EXPORT_MAX_ROWS } from '#shared/utils/datasources/exportFormats'

export interface ExplorerMenuActions {
  structure: Ref<TableStructure | null>
  /** May create tables on this connection (Full access). */
  canCreate: Ref<boolean>
  /** Tables that are Formalie's response tables (never changed here). */
  isFormalie: (schema: string, table: string) => boolean
  open: (table: { schema: string; name: string }, tab?: 'data' | 'structure') => void
  refresh: () => void
  newTable: (schema?: string) => void
  addRow: () => void
  openRow: (row: TableRow) => void
  editRow: (row: TableRow) => void
  removeRow: (row: TableRow) => void
  exportAs: (format: TableExport['format'], scope: TableExport['scope']) => void
  schema: () => { addColumn: () => void; addIndex: () => void; table: (mode: 'rename' | 'truncate' | 'drop') => void; editColumn: (column: TableStructure['columns'][number]) => void; dropColumn: (column: TableStructure['columns'][number]) => void } | null
}

export function useExplorerMenus(actions: ExplorerMenuActions) {
  const { t } = useI18n()
  const toast = useToast()
  const { copy } = useClipboard({ legacy: true })
  const { number } = useFormat()
  const copyText = (text: string) => {
    void copy(text)
    toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
  }

  // An action on a table that isn't open yet: open it, run once its structure is in.
  let pending: { key: string; run: () => void } | null = null
  watch(actions.structure, structure => {
    if (!structure || !pending || pending.key !== `${structure.schema}.${structure.name}`) return
    const { run } = pending
    pending = null
    void nextTick(run)
  })
  function onTable(schema: string, table: string, run: () => void, tab: 'data' | 'structure' = 'structure') {
    const current = actions.structure.value
    if (current && current.schema === schema && current.name === table) {
      actions.open({ schema, name: table }, tab)
      return void nextTick(run)
    }
    pending = { key: `${schema}.${table}`, run }
    actions.open({ schema, name: table }, tab)
  }

  // Export: this page first; all rows is a deliberate choice, up to EXPORT_MAX_ROWS
  const formats = (run: (format: TableExport['format'], scope: TableExport['scope']) => void, scope: TableExport['scope']): ContextMenuItem[] => [
    { label: t('responses.export.format.xlsx'), icon: 'i-lucide-file-spreadsheet', onSelect: () => run('xlsx', scope) },
    { label: t('responses.export.format.csv'), icon: 'i-lucide-file-text', onSelect: () => run('csv', scope) },
    { label: t('explorer.exportJson'), icon: 'i-lucide-file-json', onSelect: () => run('json', scope) },
    { label: t('explorer.exportSql'), icon: 'i-lucide-file-code', onSelect: () => run('sql', scope) },
  ]
  const exportGroup = (run: (format: TableExport['format'], scope: TableExport['scope']) => void): ContextMenuItem[] => [
    {
      label: t('explorer.export'),
      icon: 'i-lucide-file-down',
      children: [
        [{ type: 'label', label: t('explorer.exportThisPage') }, ...formats(run, 'page')],
        [{ type: 'label', label: t('explorer.exportAllRows', { max: number(EXPORT_MAX_ROWS) }) }, ...formats(run, 'all')],
      ],
    },
  ]

  /** Structure changes for a table, run after it is open. */
  function structureGroups(schema: string, table: string): ContextMenuItem[][] {
    if (!actions.canCreate.value || actions.isFormalie(schema, table)) return []
    const run = (fn: () => void) => onTable(schema, table, fn)
    return [
      [
        { label: t('explorer.ddl.addColumn'), icon: 'i-lucide-columns-3', onSelect: () => run(() => actions.schema()?.addColumn()) },
        { label: t('explorer.ddl.addIndex'), icon: 'i-lucide-list-tree', onSelect: () => run(() => actions.schema()?.addIndex()) },
        { label: t('explorer.ddl.renameButton'), icon: 'i-lucide-pencil', onSelect: () => run(() => actions.schema()?.table('rename')) },
      ],
      [
        { label: t('explorer.ddl.truncateButton'), icon: 'i-lucide-eraser', color: 'error', onSelect: () => run(() => actions.schema()?.table('truncate')) },
        { label: t('explorer.ddl.dropButton'), icon: 'i-lucide-trash-2', color: 'error', onSelect: () => run(() => actions.schema()?.table('drop')) },
      ],
    ]
  }

  function nodeMenu(node: ExplorerNode): ContextMenuItem[][] {
    if (node.kind === 'schema')
      return [
        ...(actions.canCreate.value ? [[{ label: t('explorer.ddl.newTableHere'), icon: 'i-lucide-table-2', onSelect: () => actions.newTable(node.schema) }]] : []),
        [{ label: t('explorer.ddl.copyName'), icon: 'i-lucide-copy', onSelect: () => copyText(node.schema) }],
      ]
    if (node.kind === 'table')
      return [
        [
          { label: t('explorer.menu.openData'), icon: 'i-lucide-rows-3', onSelect: () => actions.open({ schema: node.schema, name: node.table }, 'data') },
          { label: t('explorer.menu.openStructure'), icon: 'i-lucide-network', onSelect: () => actions.open({ schema: node.schema, name: node.table }, 'structure') },
        ],
        exportGroup((format, scope) => onTable(node.schema, node.table, () => actions.exportAs(format, scope), 'data')),
        ...structureGroups(node.schema, node.table),
        [{ label: t('explorer.ddl.copyName'), icon: 'i-lucide-copy', onSelect: () => copyText(`${node.schema}.${node.table}`) }],
      ]
    const columnOf = () => actions.structure.value?.columns.find(column => column.name === node.column)
    const alterable = actions.canCreate.value && !actions.isFormalie(node.schema, node.table)
    return [
      ...(alterable
        ? [
            [
              { label: t('explorer.ddl.editColumnShort'), icon: 'i-lucide-pencil', onSelect: () => onTable(node.schema, node.table, () => columnOf() && actions.schema()?.editColumn(columnOf()!)) },
              { label: t('explorer.ddl.dropColumn'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => onTable(node.schema, node.table, () => columnOf() && !columnOf()!.primary && actions.schema()?.dropColumn(columnOf()!)) },
            ],
          ]
        : []),
      [{ label: t('explorer.ddl.copyName'), icon: 'i-lucide-copy', onSelect: () => copyText(node.column) }],
    ]
  }

  /** The open table's own actions (the content area and rows fall back to these). */
  function tableMenu(): ContextMenuItem[][] {
    const structure = actions.structure.value
    if (!structure) return actions.canCreate.value ? [[{ label: t('explorer.ddl.newTable'), icon: 'i-lucide-table-2', onSelect: () => actions.newTable() }]] : []
    return [
      [
        { label: t('explorer.menu.refresh'), icon: 'i-lucide-rotate-cw', onSelect: () => actions.refresh() },
        ...(structure.read_only ? [] : [{ label: t('explorer.addRow'), icon: 'i-lucide-plus', onSelect: () => actions.addRow() }]),
      ],
      exportGroup((format, scope) => actions.exportAs(format, scope)),
      ...structureGroups(structure.schema, structure.name),
      [
        ...(actions.canCreate.value ? [{ label: t('explorer.ddl.newTable'), icon: 'i-lucide-table-2', onSelect: () => actions.newTable(structure.schema) }] : []),
        { label: t('explorer.ddl.copyName'), icon: 'i-lucide-copy', onSelect: () => copyText(`${structure.schema}.${structure.name}`) },
      ],
    ]
  }

  function rowMenu(row: TableRow, target: HTMLElement): ContextMenuItem[][] {
    const structure = actions.structure.value
    const { __key: _key, ...values } = row
    const cell = target.closest('td')
    const value = cell?.innerText.trim() ?? ''
    return [
      [
        { label: t('explorer.menu.openRow'), icon: 'i-lucide-panel-right-open', onSelect: () => actions.openRow(row) },
        ...(structure && !structure.read_only
          ? [
              { label: t('explorer.edit'), icon: 'i-lucide-pencil', onSelect: () => actions.editRow(row) },
              { label: t('explorer.deleteRow'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => actions.removeRow(row) },
            ]
          : []),
      ],
      [
        ...(cell && value ? [{ label: t('explorer.menu.copyValue'), icon: 'i-lucide-copy', onSelect: () => copyText(value) }] : []),
        { label: t('explorer.copyRow'), icon: 'i-lucide-braces', onSelect: () => copyText(JSON.stringify(values, null, 2)) },
      ],
      exportGroup((format, scope) => actions.exportAs(format, scope)),
    ]
  }

  return { nodeMenu, tableMenu, rowMenu }
}
