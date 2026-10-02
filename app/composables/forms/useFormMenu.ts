import type { DropdownMenuItem } from '@nuxt/ui'
import type { FormSummary } from '#shared/types/forms'

interface FormMenuHandlers {
  rename: (form: FormSummary) => void
  move: (form: FormSummary) => void
  tags: (form: FormSummary) => void
}

/** Row / card menu for a form: open & edit · share · lifecycle for its status · delete. */
export function useFormMenu(actions: ReturnType<typeof useFormActions>, handlers: FormMenuHandlers) {
  const { t } = useI18n()
  const toast = useToast()
  const { copy } = useClipboard({ legacy: true })
  const origin = useRequestURL().origin

  return (form: FormSummary): DropdownMenuItem[][] => {
    const lifecycle: DropdownMenuItem[] = []
    const add = (action: Parameters<typeof actions.lifecycle>[1], icon: string) =>
      lifecycle.push({ label: t(`forms.actions.${action}`), icon, onSelect: () => actions.lifecycle(form, action) })
    if (form.status === 'published') {
      add('unpublish', 'i-lucide-globe-lock')
      add('close', 'i-lucide-circle-stop')
    }
    if (form.status === 'closed') add('reopen', 'i-lucide-circle-play')
    if (form.status === 'archived') add('unarchive', 'i-lucide-archive-restore')
    else add('archive', 'i-lucide-archive')

    return [
      [
        { label: t('forms.actions.open'), icon: 'i-lucide-square-arrow-out-up-right', to: `/forms/${form.id}` },
        { label: t('forms.actions.rename'), icon: 'i-lucide-pencil', onSelect: () => handlers.rename(form) },
        { label: t('forms.actions.duplicate'), icon: 'i-lucide-copy', onSelect: () => actions.duplicate(form) },
        { label: t('forms.actions.move'), icon: 'i-lucide-folder-input', onSelect: () => handlers.move(form) },
        { label: t('forms.actions.tags'), icon: 'i-lucide-tags', onSelect: () => handlers.tags(form) },
      ],
      [
        ...(form.status === 'published'
          ? [
              {
                label: t('forms.copyLink'),
                icon: 'i-lucide-link',
                onSelect: () => {
                  copy(`${origin}/f/${form.slug}`)
                  toast.add({ title: t('forms.linkCopied'), color: 'success' as const, icon: 'i-lucide-check' })
                },
              },
            ]
          : []),
        { label: t('forms.viewResponses'), icon: 'i-lucide-inbox', to: `/responses?form=${form.id}` },
      ],
      lifecycle,
      [
        {
          label: t('forms.actions.delete'),
          icon: 'i-lucide-trash-2',
          color: 'error' as const,
          onSelect: () => actions.remove(form),
        },
      ],
    ]
  }
}
