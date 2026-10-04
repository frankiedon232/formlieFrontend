import type { DropdownMenuItem } from '@nuxt/ui'
import { formLink, publicHosts } from '#shared/utils/urls/public'
import type { FormSummary } from '#shared/types/forms'

interface FormMenuHandlers {
  rename: (form: FormSummary) => void
  move: (form: FormSummary) => void
  tags: (form: FormSummary) => void
  /** Save the form as a workspace template (F9). */
  saveTemplate: (form: FormSummary) => void
  /** Open from / open until (F10). */
  availability: (form: FormSummary) => void
}

/** Row / card menu for a form: open & edit · share · lifecycle for its status · delete. */
export function useFormMenu(actions: ReturnType<typeof useFormActions>, handlers: FormMenuHandlers) {
  const { t } = useI18n()
  const toast = useToast()
  const { copy } = useClipboard({ legacy: true })
  const config = useRuntimeConfig().public
  const tenant = useTenant()
  const request = useRequestURL()
  /** Public fill link: https://{forms | sub}.formalie.com/{formKey}/fill (docs/01-ARCHITECTURE.md). */
  const fillLink = (key: string) =>
    formLink(publicHosts(config, request.port), key, 'fill', tenant.profile.value?.subdomain ?? null)

  return (form: FormSummary): DropdownMenuItem[][] => {
    // People access (decision 97): "Can view" / "Responses only" people change nothing, so no
    // duplicate, template, sharing or lifecycle actions; only open, copy the live link, responses.
    if (!canEditForm(form))
      return [
        [
          { label: t('forms.actions.open'), icon: 'i-lucide-square-arrow-out-up-right', to: `/forms/${form.id}` },
          ...(form.my_access === 'view' ? [{ label: t('preview.crumb'), icon: 'i-lucide-eye', to: `/forms/${form.id}/preview` }] : []),
          ...(form.status === 'published'
            ? [
                {
                  label: t('forms.copyLink'),
                  icon: 'i-lucide-link',
                  onSelect: () => {
                    copy(fillLink(form.custom_link || form.public_key))
                    toast.add({ title: t('forms.linkCopied'), color: 'success' as const, icon: 'i-lucide-check' })
                  },
                },
              ]
            : []),
          { label: t('forms.viewResponses'), icon: 'i-lucide-inbox', to: `/forms/${form.id}/responses` },
        ],
      ]
    const lifecycle: DropdownMenuItem[] = []
    const add = (action: Parameters<typeof actions.lifecycle>[1], icon: string) =>
      lifecycle.push({
        label: t(`forms.actions.${action}`),
        icon,
        onSelect: () => actions.lifecycle(form, action),
      })
    if (form.status === 'published') {
      add('unpublish', 'i-lucide-globe-lock')
      add('close', 'i-lucide-circle-stop')
    }
    if (form.status === 'closed') add('reopen', 'i-lucide-circle-play')
    if (form.status === 'archived') add('unarchive', 'i-lucide-archive-restore')
    else add('archive', 'i-lucide-archive')

    return [
      [
        {
          label: t('forms.actions.open'),
          icon: 'i-lucide-square-arrow-out-up-right',
          to: `/forms/${form.id}`,
        },
        { label: t('preview.crumb'), icon: 'i-lucide-eye', to: `/forms/${form.id}/preview` },
        { label: t('forms.actions.rename'), icon: 'i-lucide-pencil', onSelect: () => handlers.rename(form) },
        {
          label: t('forms.actions.duplicate'),
          icon: 'i-lucide-copy',
          onSelect: () => actions.duplicate(form),
        },
        {
          label: t('forms.actions.move'),
          icon: 'i-lucide-folder-input',
          onSelect: () => handlers.move(form),
        },
        { label: t('forms.actions.tags'), icon: 'i-lucide-tags', onSelect: () => handlers.tags(form) },
        { label: t('forms.availability.menu'), icon: 'i-lucide-calendar-range', onSelect: () => handlers.availability(form) },
      ],
      [
        ...(form.status === 'published'
          ? [
              {
                label: t('forms.copyLink'),
                icon: 'i-lucide-link',
                onSelect: () => {
                  copy(fillLink(form.custom_link || form.public_key))
                  toast.add({
                    title: t('forms.linkCopied'),
                    color: 'success' as const,
                    icon: 'i-lucide-check',
                  })
                },
              },
            ]
          : []),
        { label: t('share.open'), icon: 'i-lucide-share-2', to: `/forms/${form.id}/share` },
        { label: t('forms.viewResponses'), icon: 'i-lucide-inbox', to: `/forms/${form.id}/responses` },
        { label: t('templates.saveAs'), icon: 'i-lucide-layout-template', onSelect: () => handlers.saveTemplate(form) },
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
