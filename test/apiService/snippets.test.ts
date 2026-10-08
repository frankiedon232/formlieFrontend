import { describe, expect, it } from 'vitest'
import type { ApiEndpointDetail } from '../../shared/types/apiService'
import { CALL_HEADERS, endpointCalls, fieldSchema, NEW_KEY, openApiFor, snippetFor } from '../../shared/utils/apiService/snippets'

const f = (key: string, type: string, extra: Record<string, unknown> = {}) => ({ key, name: key, label: key, type, page: 0, form_required: false, acceptable: true, accept: true, required: false, returned: true, filterable: true, filter: false, ...extra })
const endpoint = {
  id: 'e1',
  name: 'job-applications',
  description: null,
  url: 'https://api.formalie.dev/ab12cd/job-applications',
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  page_size: 50,
  headers: [],
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
    expect(calls.POST!.headers).toEqual({ Authorization: 'Bearer <token>', 'Content-Type': 'application/json', 'Formalie-Key': NEW_KEY })
    for (const method of ['GET', 'PUT', 'DELETE'] as const) expect(calls[method]!.headers).toEqual({ Authorization: 'Bearer <token>', 'Content-Type': 'application/json' })
    expect(Object.keys(calls.POST!.headers)).toEqual([...CALL_HEADERS])
    expect(calls.POST!.body).toEqual({ full_name: expect.any(String), position: 'Designer', cv: ['FILE_ID_FROM_FILES_UPLOAD'] })
    expect(calls.PUT!.url).toBe(`${endpoint.url}/<record id>`)
    expect(calls.DELETE!.body).toBeUndefined()
  })

  it('come out as code in every language', () => {
    const post = endpointCalls(endpoint).find(call => call.method === 'POST')!
    expect(snippetFor('curl', post)).toContain('-H "Formalie-Key: $(uuidgen)"')
    expect(snippetFor('javascript', post)).toContain('"Formalie-Key": crypto.randomUUID()')
    expect(snippetFor('python', post)).toContain('"Formalie-Key": str(uuid.uuid4())')
    expect(snippetFor('php', post)).toContain('"Formalie-Key: " . bin2hex(random_bytes(16))')
    expect(snippetFor('csharp', post)).toContain('"Formalie-Key", Guid.NewGuid().ToString()')
    expect(snippetFor('php', post)).toContain('"position" => "Designer"')
    for (const language of ['curl', 'javascript', 'python', 'php', 'csharp'] as const) expect(snippetFor(language, post)).not.toContain(NEW_KEY)
  })

  it('leave the Formalie-Key out of a GET (optional there) and show the masked token', () => {
    const get = endpointCalls(endpoint, 'formalie_live_…a1b2').find(call => call.method === 'GET')!
    const curl = snippetFor('curl', get)
    expect(curl).toContain('-H "Authorization: Bearer formalie_live_…a1b2"')
    expect(curl).toContain('-H "Content-Type: application/json"')
    expect(curl).not.toContain('Formalie-Key')
  })
})

describe('OpenAPI', () => {
  it('describes questions with their real values', () => {
    expect(fieldSchema(endpoint.fields[1]!)).toMatchObject({ type: 'string', enum: ['Designer', 'Engineer'] })
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
    const get = doc.paths['/job-applications']!.get as { parameters: { name: string; required?: boolean }[] }
    expect(get.parameters.find(item => item.name === 'Formalie-Key')).toMatchObject({ required: false })
    const created = doc.paths['/job-applications']!.post as { parameters: { name: string; required?: boolean }[] }
    expect(created.parameters.find(item => item.name === 'Formalie-Key')).toMatchObject({ required: true })
  })
})
