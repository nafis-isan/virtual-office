import type {
  Activity,
  ArtifactComparison,
  ArtifactSaved,
  Agent,
  KnowledgeDocument,
  TaskArtifact,
  Task,
  TaskCreated,
  TaskDetail,
} from '~/types/office'

export function useOfficeApi() {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase

  function request<T>(path: string, options: Parameters<typeof $fetch<T>>[1] = {}) {
    return $fetch<T>(path, { baseURL: apiBase, ...options })
  }

  async function getAgents() {
    return request<Agent[]>('/api/agents')
  }

  async function getTasks(includeArchived = false) {
    return request<Task[]>('/api/tasks', { query: { include_archived: includeArchived } })
  }

  async function getTask(taskId: number) {
    return request<TaskDetail>(`/api/tasks/${taskId}`)
  }

  async function getActivities(taskId: number) {
    return request<Activity[]>(`/api/tasks/${taskId}/activities`)
  }

  async function getArtifacts(taskId: number) {
    return request<TaskArtifact[]>(`/api/tasks/${taskId}/artifacts`)
  }

  function getArtifactBundleUrl(taskId: number) {
    return new URL(`/api/tasks/${taskId}/artifacts/download`, apiBase).toString()
  }

  async function retryTask(taskId: number) {
    return request<TaskCreated>(`/api/tasks/${taskId}/retry`, { method: 'POST' })
  }

  async function cancelTask(taskId: number) {
    return request<{ status: string }>(`/api/tasks/${taskId}/cancel`, { method: 'POST' })
  }

  async function setTaskArchived(taskId: number, archived: boolean) {
    return request<{ archived: boolean }>(`/api/tasks/${taskId}/archive`, {
      method: 'POST',
      body: { archived },
    })
  }

  async function compareArtifact(taskId: number, artifactId: number, relativePath: string) {
    return request<ArtifactComparison>(
      `/api/tasks/${taskId}/artifacts/${artifactId}/compare`,
      { method: 'POST', body: { relative_path: relativePath } },
    )
  }

  async function saveArtifact(
    taskId: number,
    artifactId: number,
    relativePath: string,
    overwrite = false,
    expectedSha256: string | null = null,
  ) {
    return request<ArtifactSaved>(
      `/api/tasks/${taskId}/artifacts/${artifactId}/save`,
      {
        method: 'POST',
        body: {
          relative_path: relativePath,
          overwrite,
          expected_sha256: expectedSha256,
        },
      },
    )
  }

  async function createTask(instruction: string) {
    return request<TaskCreated>('/api/chat', {
      method: 'POST',
      body: { instruction },
    })
  }

  async function getHealth() {
    return request<{
      status: string
      database: string
      ai_provider: string
      ai_model: string | null
      ai_configured: boolean
      ai_configuration_error: string | null
      gemini_configured: boolean
      gemini_embedding_configured: boolean
      rag_mode: string
    }>('/api/health')
  }

  async function getKnowledgeDocuments() {
    return request<KnowledgeDocument[]>('/api/knowledge')
  }

  async function uploadKnowledgeDocument(file: File) {
    const body = new FormData()
    body.append('file', file)
    return request<KnowledgeDocument>('/api/knowledge', { method: 'POST', body })
  }

  async function deleteKnowledgeDocument(documentId: number) {
    return request<void>(`/api/knowledge/${documentId}`, { method: 'DELETE' })
  }

  return {
    getAgents,
    getTasks,
    getTask,
    getActivities,
    getArtifacts,
    getArtifactBundleUrl,
    retryTask,
    cancelTask,
    setTaskArchived,
    compareArtifact,
    saveArtifact,
    createTask,
    getHealth,
    getKnowledgeDocuments,
    uploadKnowledgeDocument,
    deleteKnowledgeDocument,
  }
}
