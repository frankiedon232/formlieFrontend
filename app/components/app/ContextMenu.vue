<!--
  The app's right-click menu everywhere in the portal (owner 2026-10-05: never the browser's own;
  useContextMenu). Items come from the nearest area that offers some (e.g. a table row, a tree
  node), then: text fields → Cut / Copy / Paste / Select all; links → Open in a new tab / Copy
  link; selected text → Copy; and always the app's own (Back, Forward, Reload, Search, Shortcuts,
  Theme, Copy link to this page). Right-clicks in dialogs and panels (rendered outside this
  wrapper) are handed over too. Public form pages keep the browser's menu for respondents.
  Keyboard: the Menu key or Shift+F10 opens it on the focused element.
-->
<script setup lang="ts">
import type { ContextMenuItem } from '@nuxt/ui'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const colorMode = useColorMode()
const { shortcutsOpen } = useAppUi()
const enabled = computed(() => route.meta.layout !== 'public')
const root = useTemplateRef<HTMLElement>('root')
const items = shallowRef<ContextMenuItem[][]>([])
let replaying = false

type Field = HTMLInputElement | HTMLTextAreaElement
const isField = (node: Element | null): node is Field => !!node && (node instanceof HTMLTextAreaElement || (node instanceof HTMLInputElement && !['checkbox', 'radio', 'button', 'submit', 'reset', 'file', 'range', 'color', 'hidden'].includes(node.type)))

async function writeClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
  } catch {
    toast.add({ title: t('contextMenu.clipboardBlocked'), color: 'warning', icon: 'i-lucide-clipboard-x' })
  }
}

/** Cut / Copy / Paste / Select all for an input, a text area or an editor. */
function fieldItems(target: HTMLElement): ContextMenuItem[][] | null {
  const field = target.closest('input, textarea')
  const editable = !isField(field) ? (target.closest('[contenteditable="true"], [contenteditable=""]') as HTMLElement | null) : null
  if (!isField(field) && !editable) return null
  const element = (isField(field) ? field : editable)!
  const readOnly = isField(field) ? field.readOnly || field.disabled : false
  // The selection is kept now: opening the menu moves the focus away.
  const start = isField(field) ? (field.selectionStart ?? 0) : 0
  const end = isField(field) ? (field.selectionEnd ?? 0) : 0
  const range = editable && window.getSelection()?.rangeCount ? window.getSelection()!.getRangeAt(0).cloneRange() : null
  const selected = isField(field) ? field.value.slice(start, end) : (range?.toString() ?? '')
  const restore = () => {
    element.focus()
    if (isField(field)) field.setSelectionRange(start, end)
    else if (range) {
      window.getSelection()?.removeAllRanges()
      window.getSelection()?.addRange(range)
    }
  }
  return [
    [
      { label: t('contextMenu.cut'), icon: 'i-lucide-scissors', kbds: ['meta', 'x'], disabled: readOnly || !selected, onSelect: () => void writeClipboard(selected).then(() => (restore(), document.execCommand('delete'))) },
      { label: t('contextMenu.copy'), icon: 'i-lucide-copy', kbds: ['meta', 'c'], disabled: !selected, onSelect: () => void writeClipboard(selected) },
      {
        label: t('contextMenu.paste'),
        icon: 'i-lucide-clipboard-paste',
        kbds: ['meta', 'v'],
        disabled: readOnly,
        onSelect: async () => {
          try {
            const text = await navigator.clipboard.readText()
            restore()
            document.execCommand('insertText', false, text)
          } catch {
            toast.add({ title: t('contextMenu.pasteBlocked'), color: 'warning', icon: 'i-lucide-clipboard-x' })
          }
        },
      },
      {
        label: t('contextMenu.selectAll'),
        icon: 'i-lucide-text-select',
        kbds: ['meta', 'a'],
        onSelect: () => {
          element.focus()
          if (isField(field)) field.select()
          else document.execCommand('selectAll')
        },
      },
    ],
  ]
}

function linkItems(target: HTMLElement): ContextMenuItem[][] {
  const link = target.closest('a[href]') as HTMLAnchorElement | null
  if (!link) return []
  return [
    [
      { label: t('contextMenu.openNewTab'), icon: 'i-lucide-external-link', onSelect: () => void window.open(link.href, '_blank', 'noopener') },
      { label: t('contextMenu.copyLinkAddress'), icon: 'i-lucide-link', onSelect: () => void writeClipboard(link.href) },
    ],
  ]
}

function selectionItems(): ContextMenuItem[][] {
  const text = window.getSelection()?.toString() ?? ''
  return text.trim() ? [[{ label: t('contextMenu.copySelection'), icon: 'i-lucide-copy', kbds: ['meta', 'c'], onSelect: () => void writeClipboard(text) }]] : []
}

const appItems = (): ContextMenuItem[][] => [
  [
    { label: t('contextMenu.back'), icon: 'i-lucide-arrow-left', kbds: ['alt', 'arrowleft'], onSelect: () => router.back() },
    { label: t('contextMenu.forward'), icon: 'i-lucide-arrow-right', kbds: ['alt', 'arrowright'], onSelect: () => router.forward() },
    { label: t('contextMenu.reload'), icon: 'i-lucide-rotate-cw', kbds: ['f5'], onSelect: () => window.location.reload() },
  ],
  [
    { label: t('contextMenu.search'), icon: 'i-lucide-search', kbds: ['meta', 'k'], onSelect: () => void document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, metaKey: navigator.platform.startsWith('Mac'), bubbles: true })) },
    { label: t('contextMenu.shortcuts'), icon: 'i-lucide-keyboard', kbds: ['?'], onSelect: () => (shortcutsOpen.value = true) },
    {
      label: t('contextMenu.theme'),
      icon: colorMode.value === 'dark' ? 'i-lucide-moon' : 'i-lucide-sun',
      children: (['light', 'dark', 'system'] as const).map(mode => ({
        label: t(`contextMenu.${mode}`),
        icon: { light: 'i-lucide-sun', dark: 'i-lucide-moon', system: 'i-lucide-monitor' }[mode],
        type: 'checkbox' as const,
        checked: colorMode.preference === mode,
        onSelect: () => (colorMode.preference = mode),
      })),
    },
  ],
  [{ label: t('contextMenu.copyPageLink'), icon: 'i-lucide-link-2', onSelect: () => void writeClipboard(window.location.href) }],
]

function build(event: MouseEvent) {
  const target = (event.target instanceof HTMLElement ? event.target : (event.target as Node | null)?.parentElement) ?? document.body
  const field = fieldItems(target)
  if (field) return void (items.value = field)
  const own = contextItemsFor(target, event)
  // An area with its own menu keeps it short: the app's items move into one "This page" entry.
  const app = own?.length ? [[{ label: t('contextMenu.page'), icon: 'i-lucide-app-window', children: appItems() }]] : appItems()
  items.value = [...(own ?? []), ...linkItems(target), ...selectionItems(), ...app]
}

function onCapture(event: MouseEvent) {
  if (!replaying) build(event)
}

// Right-clicks outside the wrapper (dialogs, panels, menus render at the end of <body>): never the
// browser's menu; ours opens at the same place.
// Inside the wrapper the menu itself takes the event (and blocks the browser's); the copy we hand
// over is left alone too.
useEventListener(document, 'contextmenu', (event: MouseEvent) => {
  if (replaying || !enabled.value || !root.value) return
  if (event.target instanceof Node && root.value.contains(event.target)) return
  event.preventDefault()
  build(event)
  replaying = true
  try {
    root.value.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true, clientX: event.clientX, clientY: event.clientY, button: 2, buttons: 2 }))
  } finally {
    replaying = false
  }
})
</script>

<template>
  <UContextMenu :items="items" :disabled="!enabled" :ui="{ content: 'z-[100] min-w-52' }">
    <div ref="root" class="contents" @contextmenu.capture="onCapture">
      <slot />
    </div>
  </UContextMenu>
</template>
