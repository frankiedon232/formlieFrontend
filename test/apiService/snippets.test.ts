import { describe, expect, it } from 'vitest'
import type { ApiEndpointDetail } from '../../shared/types/apiService'
import { endpointCalls, fieldSchema, openApiFor, snippetFor } from '../../shared/utils/apiService/snippets'

const f = (key: string, type: string, extra: Record<string, unknown> = {}) => ({ key, name: key, label: key, type, page: 0, form_required: false, acceptable: true, accept: true, required: false, returned: true, filterable: true, filter: false, ...extra })
const endpoint = {
  id: 'e1',
  name: 'job-applications',
  description: null,
  url: 'https://api.formalie.dev/ab12cd/job-applications',
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  page_size: 50,
  headers: [{ name: 'X-Partner', preview: '••••' }],
  form: { id: 'f1', name: 'Job application', status: 'published' },
  fields: [
    f('full_name', 'short_text', { required: true }),
    f('position', 'dropdown', { options: [{ value: 'designer', label: 'Designer' }, { value: 'engineer', label: 'Engineer' }], filter: true }),
    f('cv', 'file_upload'),
    f('total', 'calculated', { acceptable: false, accept: false }),
  ],
} as unknown as ApiEndpointDetail

describe('calls', () => {
  it('give each method its address, headers and body', () => {
    const calls = Object.fromEntries(endpointCalls(endpoint).map(call => [call.method, call]))
    expect(calls.GET!.url).toBe(`${endpoint.url}?page=1&per_page=20`)
    expect(calls.POST!.headers).toMatchObject({ 'Authorization': 'Bearer <token>', 'Formalie-Key': '<unique id>', 'X-Partner': '<X-Partner>' })
    expect(calls.POST!.body).toEqual({ full_name: expect.any(String), position: 'designer', cv: ['FILE_ID_FROM_FILES_UPLOAD'] })
    expect(calls.PUT!.url).toBe(`${endpoint.url}/<record id>`)
    expect(calls.DELETE!.body).toBeUndefined()
  })

  it('come out as code in every language', () => {
    const post = endpointCalls(endpoint).find(call => call.method === 'POST')!
    expect(snippetFor('curl', post)).toContain('-H "Formalie-Key: <unique id>"')
    expect(snippetFor('javascript', post)).toContain('method: "POST"')
    expect(snippetFor('python', post)).toContain('requests.request(')
    expect(snippetFor('php', post)).toContain('"position" => "designer"')
    expect(snippetFor('csharp', post)).toContain('HttpMethod.Post')
  })
})

describe('OpenAPI', () => {
  it('describes questions with their real values', () => {
    expect(fieldSchema(endpoint.fields[1]!)).toMatchObject({ type: 'string', enum: ['designer', 'engineer'] })
    expect(fieldSchema(endpoint.fields[2]!)).toMatchObject({ type: 'array' })
  })

  it('lists every path and method, with only accepted questions in the body', () => {
    const doc = openApiFor({ name: 'Careers', description: null }, [endpoint])
    expect(doc.servers[0]!.url).toBe('https://api.formalie.dev/ab12cd')
    expect(Object.keys(doc.paths)).toEqual(['/job-applications', '/job-applications/{id}'])
    const post = doc.paths['/job-applications']!.post as { requestBody: { content: { 'application/json': { schema: { properties: object; required: string[] } } } } }
    const schema = post.requestBody.content['application/json'].schema
    expect(Object.keys(schema.properties)).toEqual(['full_name', 'position', 'cv'])
    expect(schema.required).toEqual(['full_name'])
    expect(Object.keys(doc.paths['/job-applications/{id}']!)).toEqual(['get', 'put', 'delete'])
  })
})
