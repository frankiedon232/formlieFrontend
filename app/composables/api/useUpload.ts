import type { UploadedFile, UploadPurpose, UploadTicket } from '#shared/types/onboarding'

/**
 * File upload per SECURITY-PROTOCOL.md: ask the API (enveloped, CSRF) for a pre-signed URL,
 * PUT the file straight to storage with real progress (XHR — fetch has no upload progress),
 * then confirm it with the API. `progress` is 0–100 for <UProgress>.
 */
export function useUpload() {
  const api = useApi()
  const progress = ref(0)
  const uploading = ref(false)
  let xhr: XMLHttpRequest | null = null

  function put(ticket: UploadTicket, file: File): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = new XMLHttpRequest()
      xhr = request
      request.open(ticket.method, ticket.upload_url)
      for (const [name, value] of Object.entries(ticket.headers)) request.setRequestHeader(name, value)
      request.upload.onprogress = event => {
        if (event.lengthComputable) progress.value = Math.round((event.loaded / event.total) * 100)
      }
      request.onload = () =>
        request.status >= 200 && request.status < 300
          ? resolve()
          : reject(new ApiError('FRM-GEN-1002', 'The file was refused.', request.status))
      request.onerror = () => reject(new ApiError(NETWORK_ERROR, "Can't reach the server."))
      request.onabort = () => reject(new ApiError(ABORTED_ERROR, 'Upload cancelled.'))
      request.send(file)
    })
  }

  async function upload(file: File, purpose: UploadPurpose): Promise<UploadedFile> {
    uploading.value = true
    progress.value = 0
    try {
      const { data: ticket } = await api.post<UploadTicket>('/uploads', {
        purpose,
        file_name: file.name,
        content_type: file.type,
        size: file.size,
      })
      await put(ticket, file)
      const { data } = await api.post<UploadedFile>(`/uploads/${ticket.upload_id}/complete`)
      progress.value = 100
      return data
    } finally {
      uploading.value = false
      xhr = null
    }
  }

  const cancel = () => xhr?.abort()
  onScopeDispose(cancel)

  return { upload, cancel, progress: readonly(progress), uploading: readonly(uploading) }
}
