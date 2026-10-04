import type { UploadedFile, UploadPurpose, UploadTicket } from '#shared/types/onboarding'

/**
 * File upload per SECURITY-PROTOCOL.md: ask the API (enveloped, CSRF) for a pre-signed URL,
 * PUT the file straight to storage with real progress (utils/api/upload.ts), then confirm it
 * with the API. `progress` is 0–100 for <UProgress>.
 */
export function useUpload() {
  const api = useApi()
  const progress = ref(0)
  const uploading = ref(false)
  let xhr: XMLHttpRequest | null = null

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
      await putFile(ticket, file, { onProgress: percent => (progress.value = percent), onRequest: request => (xhr = request) })
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
