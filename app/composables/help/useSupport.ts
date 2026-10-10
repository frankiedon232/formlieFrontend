/**
 * Contact support from anywhere (F25, owner 2026-10-10): one form inside the app (HelpSupportModal, mounted once
 * in the layout) instead of a mail program. `contact()` opens it, optionally with what it is about.
 */
import type { HelpCategory, SupportTopic } from '#shared/types/help'

const open = ref(false)
const preset = ref<{ topic?: SupportTopic; area?: HelpCategory | null; subject?: string; article?: string | null }>({})

export function useSupport() {
  function contact(options: { topic?: SupportTopic; area?: HelpCategory | null; subject?: string; article?: string | null } = {}) {
    preset.value = options
    open.value = true
  }
  return { open, preset, contact }
}
