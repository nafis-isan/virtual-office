export type AgentStatus =
  | 'idle'
  | 'thinking'
  | 'working'
  | 'waiting'
  | 'waiting_approval'
  | 'completed'
  | 'failed'
  | 'offline'

export interface Agent {
  name: string
  display_name: string
  role: string
  status: AgentStatus
}

export interface TaskStep {
  id: number
  position: number
  agent_name: string
  title: string
  expected_output: string
  status: string
  output: string | null
}

export interface TaskMessage {
  id: number
  sender: string
  content: string
  created_at: string
}

export interface Task {
  id: number
  instruction: string
  status: string
  archived: boolean
  summary: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface TaskArtifact {
  id: number
  step_id: number
  name: string
  kind: 'output' | 'file'
  content: string
  created_at: string
}

export interface ArtifactComparison {
  path: string
  exists: boolean
  current_content: string | null
  current_sha256: string | null
}

export interface ArtifactSaved {
  path: string
}

export interface TaskDetail extends Task {
  steps: TaskStep[]
  messages: TaskMessage[]
}

export interface Activity {
  id: number
  agent_name: string
  status: string
  message: string
  created_at: string
}

export interface TaskCreated {
  id: number
  status: string
}

export interface KnowledgeDocument {
  id: number
  filename: string
  content_type: string
  chunk_count: number
  created_at: string
}
