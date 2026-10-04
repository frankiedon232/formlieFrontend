import type { UploadTicket } from '#shared/types/onboarding'
import type { FileAnswer, RendererUpload } from '#shared/types/public'

/**
 * Files on a public form (F10 M2): each picked file goes straight to storage through a short-lived
 * upload link (with progress); the answer keeps only the reference the API returns. The submission
 * is checked against these uploads on the server.
 */
export function usePublicUploads(key: string): { upload: RendererUpload } {
  const api = useApi()
  const base = `/public/forms/${encodeURIComponent(key)}/uploads`

  const upload: RendererUpload = async (field, file, onProgress, onAbort) => {
    const { data: ticket } = await api.post<UploadTicket>(base, {
      field,
      file_name: file.name,
      content_type: file.type || 'application/octet-stream',
      size: file.size,
    })
    await putFile(ticket, file, { onProgress, onRequest: request => onAbort(() => request.abort()) })
    const { data } = await api.post<FileAnswer>(`${base}/${encodeURIComponent(ticket.upload_id)}/complete`)
    return data
  }
  return { upload }
}
