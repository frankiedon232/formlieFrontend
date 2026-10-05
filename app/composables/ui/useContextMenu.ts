/**
 * The app's own right-click menu (owner 2026-10-05: never the browser's). One menu for the whole
 * portal (AppContextMenu); any component can add items for its area:
 *
 *   const { register } = useContextMenu()
 *   register(rootRef, target => target.closest('tr') ? [[{ label: t('…'), onSelect }]] : null)
 *
 * The nearest area that answers wins; the app's own items (back, search, theme, …) follow. Text
 * fields get Cut / Copy / Paste / Select all; links get Open in a new tab / Copy link.
 */
import type { ContextMenuItem } from '@nuxt/ui'
import type { ComponentPublicInstance } from 'vue'

export type ContextMenuGroups = ContextMenuItem[][]
export type ContextMenuProvider = (target: HTMLElement, event: MouseEvent) => ContextMenuGroups | null | undefined

const providers = new WeakMap<Element, ContextMenuProvider>()

/** The items of the nearest area that answers for this element (none = null). */
export function contextItemsFor(target: HTMLElement, event: MouseEvent): ContextMenuGroups | null {
  for (let node: HTMLElement | null = target; node; node = node.parentElement) {
    const provider = providers.get(node)
    const groups = provider?.(target, event)
    if (groups?.length) return groups
  }
  return null
}

export function useContextMenu() {
  /** Adds a provider for an element (a ref, a component or a getter) while the component lives. */
  function register(element: MaybeRefOrGetter<HTMLElement | ComponentPublicInstance | null | undefined>, provider: ContextMenuProvider) {
    let current: Element | null = null
    const stop = watch(
      () => unrefElement(element as MaybeRefOrGetter<HTMLElement | null | undefined>),
      next => {
        if (current) providers.delete(current)
        current = next ?? null
        if (current) providers.set(current, provider)
      },
      { immediate: true, flush: 'post' },
    )
    onBeforeUnmount(() => {
      stop()
      if (current) providers.delete(current)
    })
  }
  return { register }
}
