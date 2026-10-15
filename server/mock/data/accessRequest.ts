/**
 * DEVELOPMENT ONLY. The notice for a request to join (owner 2026-10-15, event `access_requested`): sent to the
 * workspace's admins (their notification rule) when a sign-up ends waiting for approval. Kept apart from the route so
 * tests can check it.
 */
export type JoinVia = 'link' | 'invite' | 'sso'

export interface AccessRequestNotice {
  params: { name: string; email: string; via: JoinVia }
  link: string
}

/**
 * What the admins are told after a sign-up: the workspace's shared link and a personal sign-up link end `pending`
 * (a request); an activation link makes the account active at once, so nobody is asked.
 */
export function accessRequestNotice(kind: 'link' | 'invite' | 'activation', name: string, email: string): AccessRequestNotice | null {
  if (kind === 'activation') return null
  return { params: { name: name || email, email, via: kind }, link: '/people?status=pending' }
}
