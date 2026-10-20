import type {
  Activity,
  Agent,
  KnowledgeDocument,
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

  async function getTasks() {
    return request<Task[]>('/api/tasks')
  }

  async function getTask(taskId: number) {
    return request<TaskDetail>(`/api/tasks/${taskId}`)
  }

  async function getActivities(taskId: number) {
    return request<Activity[]>(`/api/tasks/${taskId}/activities`)
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
      gemini_configured: boolean
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
    createTask,
    getHealth,
    getKnowledgeDocuments,
    uploadKnowledgeDocument,
    deleteKnowledgeDocument,
  }
}
