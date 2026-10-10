import type { DropdownMenuItem } from '@nuxt/ui'
import { formLink, publicHosts } from '#shared/utils/urls/public'
import { channelsOf, type FormSummary } from '#shared/types/forms'

interface FormMenuHandlers {
  rename: (form: FormSummary) => void
  move: (form: FormSummary) => void
  tags: (form: FormSummary) => void
  /** Save the form as a workspace template (F9). */
  saveTemplate: (form: FormSummary) => void
  /** Open from / open until (F10). */
  availability: (form: FormSummary) => void
}

/**
 * Row / card / right-click menu for a form: open & change · share · lifecycle for its status · delete.
 * Every item follows what this person may do with this form (F22 R2: `form.can`, from the role's scope,
 * who made it, whom it is shared with and its folder); the API checks again. `page`: the form's own page
 * (no Open, Preview, Rename, Move or Tags there; Restore when it is in Trash).
 */
export function useFormMenu(actions: ReturnType<typeof useFormActions>, handlers: FormMenuHandlers) {
  const { t } = useI18n()
  const toast = useToast()
  const { copy } = useClipboard({ legacy: true })
  const config = useRuntimeConfig().public
  const tenant = useTenant()
  const request = useRequestURL()
  const { can } = useCan()
  /** Public fill link: https://{forms | sub}.formalie.com/{formKey}/fill (docs/01-ARCHITECTURE.md). */
  const fillLink = (key: string) => formLink(publicHosts(config, request.port), key, 'fill', tenant.profile.value?.subdomain ?? null)

  return (form: FormSummary, { page = false } = {}): DropdownMenuItem[][] => {
    const allowed = (action: Parameters<typeof formCan>[1]) => formCan(form, action)
    const when = <T>(ok: boolean, item: T): T[] => (ok ? [item] : [])
    if (form.deleted_at)
      return page && allowed('delete') ? [[{ label: t('forms.actions.restore'), icon: 'i-lucide-undo-2', onSelect: () => actions.lifecycle(form, 'restore') }]] : []

    const lifecycle: DropdownMenuItem[] = []
    const add = (action: Parameters<typeof actions.lifecycle>[1], icon: string) => lifecycle.push({ label: t(`forms.actions.${action}`), icon, onSelect: () => actions.lifecycle(form, action) })
    // Taking a form offline (unpublish, close, reopen) and archiving are separate permissions
    if (allowed('close')) {
      if (form.status === 'published') {
        add('unpublish', 'i-lucide-globe-lock')
        add('close', 'i-lucide-circle-stop')
      }
      if (form.status === 'closed') add('reopen', 'i-lucide-circle-play')
    }
    if (allowed('archive')) {
      if (form.status === 'archived') add('unarchive', 'i-lucide-archive-restore')
      else add('archive', 'i-lucide-archive')
    }
    const linkLive = form.status === 'published' && channelsOf(form).includes('link')

    return [
      [
        ...when(!page, { label: t('forms.actions.open'), icon: 'i-lucide-square-arrow-out-up-right', to: `/forms/${form.id}` }),
        ...when(!page && allowed('preview'), { label: t('preview.crumb'), icon: 'i-lucide-eye', to: `/forms/${form.id}/preview` }),
        ...when(!page && allowed('rename'), { label: t('forms.actions.rename'), icon: 'i-lucide-pencil', onSelect: () => handlers.rename(form) }),
        ...when(allowed('duplicate'), { label: t('forms.actions.duplicate'), icon: 'i-lucide-copy', onSelect: () => actions.duplicate(form) }),
        ...when(!page && allowed('move'), { label: t('forms.actions.move'), icon: 'i-lucide-folder-input', onSelect: () => handlers.move(form) }),
        ...when(!page && allowed('edit'), { label: t('forms.actions.tags'), icon: 'i-lucide-tags', onSelect: () => handlers.tags(form) }),
        ...when(allowed('availability'), { label: t('forms.availability.menu'), icon: 'i-lucide-calendar-range', onSelect: () => handlers.availability(form) }),
      ],
      [
        ...when(linkLive, {
          label: t('forms.copyLink'),
          icon: 'i-lucide-link',
          onSelect: () => {
            copy(fillLink(form.custom_link || form.public_key))
            toast.add({ title: t('forms.linkCopied'), color: 'success' as const, icon: 'i-lucide-check' })
          },
        }),
        ...when(allowed('share_view'), { label: t('share.open'), icon: 'i-lucide-share-2', to: `/forms/${form.id}/share` }),
        ...when(!page && can('responses.view'), { label: t('forms.viewResponses'), icon: 'i-lucide-inbox', to: `/forms/${form.id}/responses` }),
        // A template is a resource too (templates get their own permissions later; until then resources.manage)
        ...when(allowed('save_template') && can('resources.manage'), { label: t('templates.saveAs'), icon: 'i-lucide-layout-template', onSelect: () => handlers.saveTemplate(form) }),
      ],
      lifecycle,
      when(allowed('delete'), { label: t('forms.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => actions.remove(form) }),
    ].filter(group => group.length)
  }
}
