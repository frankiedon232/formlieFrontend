/**
 * GET /api-service/connections?type=service|endpoint|token|rule&id= (owner 2026-10-08): what an API item
 * is connected to, for the Connections block of every detail panel, so nothing is hidden:
 *   service  → its endpoints, the tokens that can call it, the access rules on it
 *   endpoint → its service and form, the tokens that can call it, the access rules on it
 *   token    → the services and endpoints it can call
 *   rule     → the service or endpoints it applies to
 * Tokens and rules say how they reach the item (`reach`): made for this endpoint, for its service, or
 * for everything (the workspace's tokens and rules without a chosen service or endpoint).
 */
import { z } from 'zod'
import type { ApiConnections, ApiReach } from '#shared/types/apiService'
import { rulesFor } from '#shared/utils/apiService/access'
import { scopeAllows, tokenReach, tokenStatusOf } from '#shared/utils/apiService/tokens'
import { requireAdmin } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { apiOf, type StoredAccessRule, type StoredApiEndpoint, type StoredApiToken } from '../data/apiStore'
import { formsOf } from '../data/formStore'

const query = z.object({ type: z.enum(['service', 'endpoint', 'token', 'rule']), id: z.string().min(1).max(64) })

export const apiConnections = defineMockRoute(({ event, query: raw }) => {
  const { tenant } = requireAdmin(event)
  const { type, id } = parseBody(query, raw)
  const api = apiOf(tenant)
  const forms = formsOf(tenant).forms
  const serviceName = new Map(api.services.map(item => [item.id, item.name]))
  const callers = api.tokens.filter(token => token.kind !== 'webhook' && !['revoked', 'expired'].includes(tokenStatusOf(token)))
  const canCall = (token: StoredApiToken, endpoint: StoredApiEndpoint) => endpoint.methods.some(method => scopeAllows(token.scopes, { endpoint_id: endpoint.id, service_id: endpoint.service_id, method }))
  const endpointLink = (endpoint: StoredApiEndpoint) => ({ id: endpoint.id, name: endpoint.name, status: endpoint.status, service: serviceName.get(endpoint.service_id) ?? '' })
  const tokenLink = (token: StoredApiToken, reach: ApiReach) => ({ id: token.id, name: token.name, mode: token.mode, status: tokenStatusOf(token), reach })
  const ruleLink = (rule: StoredAccessRule, reach: ApiReach) => ({ id: rule.id, action: rule.action, kind: rule.kind, values: rule.values.slice(0, 3), enabled: rule.enabled, reach })
  const ruleReach = (rule: StoredAccessRule): ApiReach => (rule.scope.type === 'all' ? 'all' : rule.scope.type)
  /** The narrowest way a token reaches any of these endpoints. */
  const bestReach = (token: StoredApiToken, endpoints: StoredApiEndpoint[]): ApiReach => {
    const reaches = endpoints.filter(endpoint => canCall(token, endpoint)).map(endpoint => tokenReach(token.scopes, endpoint))
    return reaches.includes('endpoint') ? 'endpoint' : reaches.includes('service') ? 'service' : 'all'
  }
  const out: ApiConnections = { service: null, form: null, endpoints: [], tokens: [], rules: [] }

  if (type === 'service' || type === 'endpoint') {
    const endpoint = type === 'endpoint' ? api.endpoints.find(item => item.id === id) : undefined
    const service = api.services.find(item => item.id === (endpoint ? endpoint.service_id : id))
    if (!service || (type === 'endpoint' && !endpoint)) throw new MockError('FRM-GEN-1004')
    const endpoints = endpoint ? [endpoint] : api.endpoints.filter(item => item.service_id === service.id)
    if (endpoint) {
      out.service = { id: service.id, name: service.name, status: service.status }
      const form = forms.find(item => item.id === endpoint.form_id)
      out.form = form ? { id: form.id, name: form.name, status: form.status } : null
    } else {
      out.endpoints = endpoints.map(endpointLink)
    }
    out.tokens = callers.filter(token => endpoints.some(item => canCall(token, item))).map(token => tokenLink(token, bestReach(token, endpoints)))
    out.rules = api.rules
      .filter(rule => (endpoint ? rulesFor([rule], endpoint).length : rule.scope.type === 'all' || (rule.scope.type === 'service' && rule.scope.id === service.id) || (rule.scope.type === 'endpoint' && endpoints.some(item => item.id === rule.scope.id))))
      .map(rule => ruleLink(rule, ruleReach(rule)))
  } else if (type === 'token') {
    const token = api.tokens.find(item => item.id === id)
    if (!token) throw new MockError('FRM-GEN-1004')
    const reachable = token.kind === 'webhook' ? [] : api.endpoints.filter(endpoint => canCall(token, endpoint))
    out.endpoints = reachable.map(endpointLink)
    const services = [...new Set(reachable.map(item => item.service_id))]
    // One service named on the token: shown as its service
    if (token.scopes.services.length === 1 && serviceName.has(token.scopes.services[0]!)) {
      const service = api.services.find(item => item.id === token.scopes.services[0])!
      out.service = { id: service.id, name: service.name, status: service.status }
    } else if (services.length === 1) {
      const service = api.services.find(item => item.id === services[0])!
      out.service = { id: service.id, name: service.name, status: service.status }
    }
  } else {
    const rule = api.rules.find(item => item.id === id)
    if (!rule) throw new MockError('FRM-GEN-1004')
    if (rule.scope.type === 'service') {
      const service = api.services.find(item => item.id === rule.scope.id)
      if (service) out.service = { id: service.id, name: service.name, status: service.status }
      out.endpoints = api.endpoints.filter(item => item.service_id === rule.scope.id).map(endpointLink)
    } else {
      out.endpoints = api.endpoints.filter(item => rule.scope.type === 'all' || item.id === rule.scope.id).map(endpointLink)
    }
  }
  return ok(out)
})
