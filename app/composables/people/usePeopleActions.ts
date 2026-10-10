/**
 * What can be done to people from the People page, its cards and the detail panel (F16): invitations
 * (send again, copy a fresh link, withdraw) and accounts (disable / enable, sign out everywhere, ask for
 * a new password, reset two-step sign-in), one at a time or several at once. Risky ones ask first; the
 * busy row shows a spinner; a toast confirms; `done` refreshes the list, the cards and the menu counts.
 */
import type { DropdownMenuItem } from '@nuxt/ui'
import type { WorkspaceRole } from '#shared/types/auth'
import type { PersonRow } from '#shared/types/people'

export function usePeopleActions(done: () => unknown) {
  const { t } = useI18n()
const { roleName } = useBuiltInNames()
  const api = useApi()
  const toast = useToast()
  const confirm = useConfirm()
  const session = useSession()
  const counts = useNavCounts()
  const team = useTeam()
  const { handle } = useErrorHandler()
  const { copy } = useClipboard({ legacy: true })
  const busy = ref<string | null>(null)
  const me = computed(() => session.user.value?.id ?? null)
  const iAmOwner = computed(() => session.user.value?.role === 'owner')

  async function act(id: string, work: () => Promise<unknown>, message: string) {
    if (busy.value) return
    busy.value = id
    try {
      await work()
      toast.add({ title: message, color: 'success', icon: 'i-lucide-circle-check' })
      await done()
      void counts.refresh(true)
      void team.refresh(true)
    } catch (error) {
      handle(error)
    } finally {
      busy.value = null
    }
  }
  const ask = (key: string, person: PersonRow, danger = false) => confirm({ title: t(`people.manage.${key}Title`, { name: person.name }), description: t(`people.manage.${key}Desc`), confirmLabel: t(`people.manage.${key}`), danger })
  const post = (person: PersonRow, path: string) => api.post(`/people/${person.id}/${path}`)

  const { can } = useCan()
  const resend = (person: PersonRow) => act(person.id, () => post(person, 'invite/resend'), t('people.invite.resent', { email: person.email }))
  const copyLink = (person: PersonRow) =>
    act(
      person.id,
      async () => {
        const { data } = await api.post<{ link: string }>(`/people/${person.id}/invite/link`)
        await copy(data.link)
      },
      t('people.invite.linkCopied'),
    )
  async function reject(person: PersonRow) {
    const ok = await confirm({ title: t('people.approve.rejectTitle', { name: person.name }), description: t('people.approve.rejectDesc'), confirmLabel: t('people.approve.reject'), danger: true })
    if (ok) await act(person.id, () => api.post(`/people/${person.id}/reject`, {}), t('people.approve.rejected', { name: person.name }))
  }
  async function revoke(person: PersonRow) {
    const activation = person.status === 'not_activated'
    const ok = await confirm({ title: activation ? t('people.add.removeTitle', { name: person.name }) : t('people.invite.revokeTitle', { email: person.email }), description: activation ? t('people.add.removeDesc') : t('people.invite.revokeDesc'), confirmLabel: activation ? t('people.add.remove') : t('people.invite.revoke'), danger: true })
    if (ok) await act(person.id, () => api.del(`/people/${person.id}/invite`), t('people.invite.revoked', { email: person.email }))
  }
  async function disable(person: PersonRow) {
    if (await ask('disable', person, true)) await act(person.id, () => post(person, 'disable'), t('people.manage.disabled', { name: person.name }))
  }
  const enable = (person: PersonRow) => act(person.id, () => post(person, 'enable'), t('people.manage.enabled', { name: person.name }))
  async function signOut(person: PersonRow) {
    if (await ask('signOut', person)) await act(person.id, () => post(person, 'sign-out'), t('people.manage.signedOut', { name: person.name }))
  }
  async function password(person: PersonRow) {
    if (await ask('password', person)) await act(person.id, () => post(person, 'password'), t('people.manage.passwordDone', { name: person.name }))
  }
  async function twoStep(person: PersonRow) {
    if (await ask('twoStep', person, true)) await act(person.id, () => post(person, 'two-step/reset'), t('people.manage.twoStepDone', { name: person.name }))
  }

  /** Several people at once; says how many were changed and how many left as they were. */
  async function bulk(ids: string[], action: 'role' | 'department' | 'job_title' | 'disable' | 'enable', value?: string) {
    if (action === 'disable' && !(await confirm({ title: t('people.bulk.disableTitle', { n: ids.length }, ids.length), description: t('people.manage.disableDesc'), confirmLabel: t('people.manage.disable'), danger: true }))) return
    await act('bulk', async () => {
      const { data } = await api.post<{ done: number; skipped: number }>('/people/bulk', { ids, action, value })
      if (data.skipped) toast.add({ title: t('people.bulk.skipped', { n: data.skipped }, data.skipped), description: t('people.bulk.skippedDesc'), color: 'warning', icon: 'i-lucide-info' })
    }, t('people.bulk.done', { n: ids.length }, ids.length))
  }

  /** The ⋯ items for a person (row, card, panel); `edit` opens the edit dialog. */
  function menu(person: PersonRow, edit: (person: PersonRow) => void, approve?: (person: PersonRow) => void): DropdownMenuItem[][] {
    // Signed up with a link, waiting: approve (completing the profile) or reject
    if (person.status === 'pending')
      return can('people.approve')
        ? [
            [{ label: t('people.approve.button'), icon: 'i-lucide-user-check', onSelect: () => approve?.(person) }],
            [{ label: t('people.approve.reject'), icon: 'i-lucide-user-x', color: 'error' as const, onSelect: () => void reject(person) }],
          ]
        : []
    // A link is out: a personal sign-up link, or the activation email of a profile an admin made
    if (person.status === 'invited' || person.status === 'not_activated') {
      const activation = person.status === 'not_activated'
      return can('people.manage')
        ? [
            [
              { label: activation ? t('people.add.resend') : t('people.invite.resend'), icon: 'i-lucide-send', onSelect: () => void resend(person) },
              { label: activation ? t('people.add.copyLink') : t('people.invite.copyLink'), icon: 'i-lucide-link', onSelect: () => void copyLink(person) },
              { label: t('people.manage.edit'), icon: 'i-lucide-pencil', onSelect: () => edit(person) },
            ],
            [{ label: activation ? t('people.add.remove') : t('people.invite.revoke'), icon: 'i-lucide-user-minus', color: 'error' as const, onSelect: () => void revoke(person) }],
          ]
        : []
    }
    if (!can('people.manage')) return []
    const self = person.id === me.value
    const ownerLocked = person.role === 'owner' && !iAmOwner.value
    if (ownerLocked) return [[{ label: t('people.manage.ownerOnly'), icon: 'i-lucide-lock', disabled: true }]]
    return [
      [{ label: t('people.manage.edit'), icon: 'i-lucide-pencil', onSelect: () => edit(person) }],
      [
        { label: t('people.manage.signOut'), icon: 'i-lucide-log-out', onSelect: () => void signOut(person) },
        ...(self ? [] : [{ label: t('people.manage.password'), icon: 'i-lucide-key-round', onSelect: () => void password(person) }]),
        ...(person.two_step ? [{ label: t('people.manage.twoStep'), icon: 'i-lucide-shield-off', onSelect: () => void twoStep(person) }] : []),
      ],
      ...(self ? [] : [[person.status === 'disabled' ? { label: t('people.manage.enable'), icon: 'i-lucide-user-check', onSelect: () => void enable(person) } : { label: t('people.manage.disable'), icon: 'i-lucide-user-x', color: 'error' as const, onSelect: () => void disable(person) }]]),
    ]
  }

  // The workspace's roles (Owner only offered to owners)
  const { roles, refresh: loadRoles } = useRoles()
  void loadRoles()
  const roleItems = (pick: (role: WorkspaceRole) => void): DropdownMenuItem[] =>
    roles.value.filter(role => role.id !== 'owner' || iAmOwner.value).map(role => ({ label: roleName(role.id, role.name), icon: role.id === 'owner' ? 'i-lucide-crown' : 'i-lucide-shield', onSelect: () => pick(role.id) }))

  return { busy, me, iAmOwner, resend, copyLink, revoke, reject, disable, enable, signOut, password, twoStep, bulk, menu, roleItems }
}
