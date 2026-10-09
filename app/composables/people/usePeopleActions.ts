/**
 * What can be done to a person from the People page, its cards and the detail panel (F16): for an
 * invitation, send it again, copy a fresh link, or withdraw it (asks first). The row that is busy shows a
 * spinner; a toast confirms; `done` refreshes the list and the cards.
 */
import type { PersonRow } from '#shared/types/people'

export function usePeopleActions(done: () => unknown) {
  const { t } = useI18n()
  const api = useApi()
  const toast = useToast()
  const confirm = useConfirm()
  const { handle } = useErrorHandler()
  const { copy } = useClipboard({ legacy: true })
  const busy = ref<string | null>(null)

  async function act(person: PersonRow, work: () => Promise<unknown>, message: string) {
    if (busy.value) return
    busy.value = person.id
    try {
      await work()
      toast.add({ title: message, color: 'success', icon: 'i-lucide-circle-check' })
      await done()
    } catch (error) {
      handle(error)
    } finally {
      busy.value = null
    }
  }

  const resend = (person: PersonRow) => act(person, () => api.post(`/people/${person.id}/invite/resend`), t('people.invite.resent', { email: person.email }))
  const copyLink = (person: PersonRow) =>
    act(
      person,
      async () => {
        const { data } = await api.post<{ link: string }>(`/people/${person.id}/invite/link`)
        await copy(data.link)
      },
      t('people.invite.linkCopied'),
    )
  async function revoke(person: PersonRow) {
    const ok = await confirm({ title: t('people.invite.revokeTitle', { email: person.email }), description: t('people.invite.revokeDesc'), confirmLabel: t('people.invite.revoke'), danger: true })
    if (ok) await act(person, () => api.del(`/people/${person.id}/invite`), t('people.invite.revoked', { email: person.email }))
  }

  return { busy, resend, copyLink, revoke }
}
