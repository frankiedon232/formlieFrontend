/**
 * Code samples and the OpenAPI description of an endpoint (F13 M5): what the Docs page shows and
 * downloads. Built from the endpoint's own choices (methods, questions, required headers) and the
 * form's real answer values; tokens are placeholders, never real ones.
 */
import type { ApiEndpointDetail, ApiEndpointField } from '#shared/types/apiService'
import { exampleRecord, exampleRequestBody, sampleValue } from '#shared/utils/apiService/endpoints'
import type { ApiMethod } from '#shared/utils/urls/public'

export type SnippetLanguage = 'curl' | 'javascript' | 'python' | 'php' | 'csharp'
export interface SnippetCall {
  method: ApiMethod
  url: string
  headers: Record<string, string>
  body?: unknown
}

/** One call in a language, ready to copy. */
export function snippetFor(language: SnippetLanguage, call: SnippetCall): string {
  const json = call.body === undefined ? null : JSON.stringify(call.body, null, 2)
  const headers = Object.entries(call.headers)
  const generated = KEY_CODE[language]
  const fresh = (value: string) => value === NEW_KEY
  switch (language) {
    case 'curl':
      return [`curl -X ${call.method} "${call.url}"`, ...headers.map(([name, value]) => `  -H "${name}: ${fresh(value) ? generated : value}"`), ...(json ? [`  -d '${json.replace(/'/g, "'\\''")}'`] : [])].join(' \\\n')
    case 'javascript':
      return `const response = await fetch("${call.url}", {\n  method: "${call.method}",\n  headers: ${indent(JSON.stringify(Object.fromEntries(headers), null, 2).replace(`"${NEW_KEY}"`, generated), 2)},${json ? `\n  body: JSON.stringify(${indent(json, 2)}),` : ''}\n})\nconst result = await response.json()`
    case 'python':
      return `import requests, uuid\n\nresponse = requests.request(\n    "${call.method}",\n    "${call.url}",\n    headers=${indent(pyDict(Object.fromEntries(headers)).replace(`"${NEW_KEY}"`, generated), 4)},${json ? `\n    json=${indent(toPython(call.body), 4)},` : ''}\n)\nresult = response.json()`
    case 'php':
      return `<?php\n$ch = curl_init("${call.url}");\ncurl_setopt_array($ch, [\n    CURLOPT_CUSTOMREQUEST => "${call.method}",\n    CURLOPT_RETURNTRANSFER => true,\n    CURLOPT_HTTPHEADER => [\n${headers.map(([name, value]) => (fresh(value) ? `        "${name}: " . ${generated},` : `        "${name}: ${value}",`)).join('\n')}\n    ],${json ? `\n    CURLOPT_POSTFIELDS => json_encode(${indent(toPhp(call.body), 4)}),` : ''}\n]);\n$result = json_decode(curl_exec($ch), true);`
    case 'csharp':
      return `using var client = new HttpClient();\nvar request = new HttpRequestMessage(HttpMethod.${call.method === 'DELETE' ? 'Delete' : call.method[0] + call.method.slice(1).toLowerCase()}, "${call.url}");\n${headers
        .filter(([name]) => name.toLowerCase() !== 'content-type')
        .map(([name, value]) => `request.Headers.TryAddWithoutValidation("${name}", ${fresh(value) ? generated : `"${value}"`});`)
        .join('\n')}${json ? `\nrequest.Content = new StringContent(${JSON.stringify(json.replace(/\n\s*/g, ' '))}, System.Text.Encoding.UTF8, "application/json");` : ''}\nvar response = await client.SendAsync(request);\nvar result = await response.Content.ReadAsStringAsync();`
  }
}

/** The calls an endpoint answers, with the headers and an example body each needs. */
/** The only headers a call sends (owner, 2026-10-06): Formalie-Key required on POST, optional on the other methods. */
export const CALL_HEADERS = ['Authorization', 'Content-Type', 'Formalie-Key'] as const
/** Placeholder the code samples turn into a generated id in each language. */
export const NEW_KEY = '<new unique id>'

export function endpointCalls(endpoint: Pick<ApiEndpointDetail, 'methods' | 'url' | 'fields' | 'page_size'>, token = '<token>'): SnippetCall[] {
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
  const body = exampleRequestBody(endpoint.fields)
  return endpoint.methods.map(method => {
    if (method === 'GET') return { method, url: `${endpoint.url}?page=1&per_page=${Math.min(20, endpoint.page_size)}`, headers }
    if (method === 'POST') return { method, url: endpoint.url, headers: { ...headers, 'Formalie-Key': NEW_KEY }, body }
    if (method === 'PUT') return { method, url: `${endpoint.url}/<record id>`, headers, body }
    return { method, url: `${endpoint.url}/<record id>`, headers }
  })
}

/** A question as JSON Schema (OpenAPI 3.1). */
export function fieldSchema(field: Pick<ApiEndpointField, 'type' | 'options' | 'label' | 'key'>): Record<string, unknown> {
  const values = field.options?.map(option => option.value)
  const base: Record<string, unknown> = { description: field.label }
  switch (field.type) {
    case 'number':
    case 'slider':
    case 'percentage':
    case 'rating':
    case 'scale':
    case 'currency':
      return { ...base, type: 'number' }
    case 'toggle':
    case 'consent':
      return { ...base, type: 'boolean' }
    case 'email':
      return { ...base, type: 'string', format: 'email' }
    case 'url':
      return { ...base, type: 'string', format: 'uri' }
    case 'date':
      return { ...base, type: 'string', format: 'date' }
    case 'datetime':
      return { ...base, type: 'string', format: 'date-time' }
    case 'dropdown':
    case 'radio':
      return { ...base, type: 'string', ...(values?.length ? { enum: values } : {}) }
    case 'multi_select':
    case 'checkbox':
    case 'ranking':
      return { ...base, type: 'array', items: { type: 'string', ...(values?.length ? { enum: values } : {}) } }
    case 'file_upload':
    case 'image_upload':
      return { ...base, type: 'array', items: { type: 'string', description: 'id from …/files' } }
    case 'full_name':
    case 'address':
    case 'duration':
    case 'date_range':
    case 'matrix':
      return { ...base, type: 'object', example: sampleValue(field) }
    default:
      return { ...base, type: 'string' }
  }
}

/** OpenAPI 3.1 for the endpoints of one service. */
export function openApiFor(service: { name: string; description: string | null }, endpoints: ApiEndpointDetail[]) {
  const paths: Record<string, Record<string, unknown>> = {}
  const base = endpoints[0] ? endpoints[0].url.replace(/\/[^/]+$/, '') : ''
  for (const endpoint of endpoints) {
    const accepted = endpoint.fields.filter(field => field.accept)
    const record = { type: 'object', properties: { id: { type: 'string' }, submitted_at: { type: 'string', format: 'date-time' }, status: { type: 'string' }, data: { type: 'object', properties: Object.fromEntries(endpoint.fields.filter(field => field.returned).map(field => [field.name, fieldSchema(field)])) } } }
    const input = { type: 'object', properties: Object.fromEntries(accepted.map(field => [field.name, fieldSchema(field)])), required: accepted.filter(field => field.required).map(field => field.name), additionalProperties: false }
    const key = (required: boolean) => ({ name: 'Formalie-Key', in: 'header', required, schema: { type: 'string', minLength: 16, maxLength: 100, pattern: '^[A-Za-z0-9._:-]+$' }, description: required ? 'A new unique id (a UUID) for every POST. The same key and body within 24 hours answer with the first record; the same key with another body is refused (409).' : 'Optional: an id to find this call in Request logs.' })
    const headers = [key(false)]
    const errors = { '401': { description: 'FRM-API-1010' }, '403': { description: 'FRM-API-1009, FRM-API-1015' }, '422': { description: 'FRM-RESP-1001, FRM-API-1014' }, '429': { description: 'FRM-GEN-1029' } }
    const one = `/${endpoint.name}/{id}`
    const list = `/${endpoint.name}`
    for (const method of endpoint.methods) {
      if (method === 'GET') {
        paths[list] = { ...paths[list], get: { summary: endpoint.description ?? endpoint.form.name, parameters: [...headers, { name: 'page', in: 'query', schema: { type: 'integer' } }, { name: 'per_page', in: 'query', schema: { type: 'integer', maximum: endpoint.page_size } }, ...endpoint.fields.filter(field => field.filter).map(field => ({ name: field.name, in: 'query', schema: fieldSchema(field) }))], responses: { '200': { description: 'OK', content: { 'application/json': { schema: { type: 'object', properties: { data: { type: 'array', items: record } } }, example: { data: [exampleRecord(endpoint.fields)] } } } }, ...errors } } }
        paths[one] = { ...paths[one], get: { parameters: [...headers, { name: 'id', in: 'path', required: true, schema: { type: 'string' } }], responses: { '200': { description: 'OK', content: { 'application/json': { schema: { type: 'object', properties: { data: record } } } } }, '404': { description: 'FRM-API-1013' }, ...errors } } }
      }
      if (method === 'POST') paths[list] = { ...paths[list], post: { parameters: [key(true)], requestBody: { required: true, content: { 'application/json': { schema: input, example: exampleRequestBody(endpoint.fields) } } }, responses: { '201': { description: 'Created', content: { 'application/json': { schema: { type: 'object', properties: { data: record } } } } }, ...errors } } }
      if (method === 'PUT') paths[one] = { ...paths[one], put: { parameters: [...headers, { name: 'id', in: 'path', required: true, schema: { type: 'string' } }], requestBody: { content: { 'application/json': { schema: { ...input, required: [] } } } }, responses: { '200': { description: 'OK' }, '404': { description: 'FRM-API-1013' }, ...errors } } }
      if (method === 'DELETE') paths[one] = { ...paths[one], delete: { parameters: [...headers, { name: 'id', in: 'path', required: true, schema: { type: 'string' } }], responses: { '200': { description: 'Deleted' }, '404': { description: 'FRM-API-1013' }, ...errors } } }
    }
  }
  return {
    openapi: '3.1.0',
    info: { title: service.name, description: service.description ?? '', version: '1' },
    servers: [{ url: base }],
    components: { securitySchemes: { bearer: { type: 'http', scheme: 'bearer' } } },
    security: [{ bearer: [] }],
    paths,
  }
}

/** A new unique id for the Formalie-Key, written in each language. */
const KEY_CODE: Record<SnippetLanguage, string> = { curl: '$(uuidgen)', javascript: 'crypto.randomUUID()', python: 'str(uuid.uuid4())', php: 'bin2hex(random_bytes(16))', csharp: 'Guid.NewGuid().ToString()' }

const indent = (text: string, spaces: number) => text.replace(/\n/g, `\n${' '.repeat(spaces)}`)
const pyDict = (value: Record<string, string>) => `{\n${Object.entries(value).map(([k, v]) => `    "${k}": "${v}",`).join('\n')}\n}`
function toPython(value: unknown): string {
  return JSON.stringify(value, null, 4).replace(/\btrue\b/g, 'True').replace(/\bfalse\b/g, 'False').replace(/\bnull\b/g, 'None')
}
function toPhp(value: unknown): string {
  return JSON.stringify(value, null, 4).replace(/\{/g, '[').replace(/\}/g, ']').replace(/":/g, '" =>')
}
