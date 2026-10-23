<script setup lang="ts">
import type { Activity, Agent, Task, TaskArtifact, TaskDetail } from '~/types/office'

type ActivityView = 'office' | 'agents' | 'tasks' | 'knowledge'
type OfficeRailView = 'team' | 'knowledge' | 'task'
type EditorTab = 'overview' | 'steps' | 'output' | 'sources'
type BottomTab = 'problems' | 'output' | 'terminal'

useHead({
  title: 'Virtual Office AI',
  meta: [{ name: 'description', content: 'Virtual Office AI — ruang kerja tim agent AI.' }],
})

const api = useOfficeApi()
const agents = ref<Agent[]>([])
const tasks = ref<Task[]>([])
const selectedTask = ref<TaskDetail | null>(null)
const activities = ref<Activity[]>([])
const taskArtifacts = ref<TaskArtifact[]>([])
const selectedId = ref<number | null>(null)
const openTaskIds = ref<number[]>([])
const activeEditorId = ref<number | 'office'>('office')
const activityView = ref<ActivityView>('office')
const officeRailView = ref<OfficeRailView>('team')
const editorTab = ref<EditorTab>('overview')
const bottomTab = ref<BottomTab>('problems')
const bottomOpen = ref(true)
const sidebarOpen = ref(true)
const composerOpen = ref(false)
const selectedAgentName = ref<string | null>(null)
const showArchivedTasks = ref(false)
const searchQuery = ref('')
const searchInput = ref<HTMLInputElement | null>(null)
const health = ref<{
  status: string
  database: string
  ai_provider: string
  ai_model: string | null
  ai_configured: boolean
  ai_configuration_error: string | null
  gemini_configured: boolean
  gemini_embedding_configured: boolean
  rag_mode: string
} | null>(null)
const loading = ref(true)
const sending = ref(false)
const errorMessage = ref('')
const officeNotice = ref('')
let pollTimer: ReturnType<typeof setInterval> | undefined
let noticeTimer: ReturnType<typeof setTimeout> | undefined

const isReady = computed(() => health.value?.database === 'connected')
const canCreateTask = computed(() =>
  isReady.value &&
  health.value?.ai_configured === true &&
  !!health.value.ai_model?.trim(),
)
const chatDisabledReason = computed(() => {
  if (!isReady.value) return 'Backend atau database belum siap. Jalankan layanan terlebih dahulu.'
  if (health.value?.ai_configuration_error) return health.value.ai_configuration_error
  if (!health.value?.ai_model?.trim()) {
    return 'Backend belum melaporkan model AI aktif. Restart backend dari folder backend agar konfigurasi terbaru dimuat.'
  }
  return 'Konfigurasi AI belum siap.'
})
const connectionLabel = computed(() => {
  if (!health.value) return 'Menghubungkan...'
  return health.value.database === 'connected' ? 'Backend terhubung' : 'Database terputus'
})
const activeTask = computed(() =>
  activeEditorId.value === 'office' || selectedTask.value?.id !== activeEditorId.value
    ? null
    : selectedTask.value,
)
const activeAgent = computed(() =>
  agents.value.find((agent) => agent.name === selectedAgentName.value) ?? null,
)
const filteredTasks = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase('id')
  if (!query) return tasks.value
  return tasks.value.filter((task) =>
    `${task.instruction} ${task.summary ?? ''} ${task.status}`.toLocaleLowerCase('id').includes(query),
  )
})
const activeTaskLabel = computed(() => {
  if (!selectedTask.value) return 'Tidak ada task aktif'
  const title = selectedTask.value.instruction.replace(/\s+/g, ' ').trim()
  return `#${selectedTask.value.id} ${title.length > 42 ? `${title.slice(0, 39)}...` : title}`
})
const problemCount = computed(() => {
  const taskErrors = tasks.value.filter((task) => task.status === 'failed').length
  const configError = health.value && !health.value.ai_configured ? 1 : 0
  return taskErrors + configError + (errorMessage.value ? 1 : 0)
})
const outputActivities = computed(() => [...activities.value].reverse().slice(0, 24))
const activeTaskCanCancel = computed(() =>
  !!selectedTask.value && ['thinking', 'working', 'waiting', 'waiting_approval'].includes(selectedTask.value.status),
)
const terminalLines = computed(() => [
  `[workspace] Backend: ${health.value?.status ?? 'menghubungkan'} · Database: ${health.value?.database ?? 'tidak diketahui'}`,
  `[provider] ${health.value?.ai_provider ?? 'AI'} ${health.value?.ai_model ?? ''}: ${health.value?.ai_configured ? 'siap' : health.value?.ai_configuration_error ?? 'belum diatur'}`,
  `[rag] ${health.value?.rag_mode === 'keyword_local' ? 'pencocokan kata kunci lokal' : 'Gemini embeddings'}`,
  selectedTask.value
    ? `[tugas #${selectedTask.value.id}] ${selectedTask.value.status} · ${selectedTask.value.instruction}`
    : '[tugas] Belum ada tugas yang dipilih.',
  '[status] Baca-saja. Agent tidak menjalankan perintah shell.',
])

function getErrorMessage(error: unknown) {
  if (typeof error === 'object' && error !== null && 'data' in error) {
    const data = error.data
    if (typeof data === 'object' && data !== null && 'detail' in data && typeof data.detail === 'string') {
      return data.detail
    }
  }
  return 'Tidak dapat menghubungi backend. Periksa server FastAPI dan alamat API di frontend/.env.'
}

async function loadTask(taskId: number) {
  const previousTask = selectedTask.value?.id === taskId ? selectedTask.value : null
  selectedId.value = taskId
  if (!previousTask) {
    selectedTask.value = null
    activities.value = []
    taskArtifacts.value = []
  }
  try {
    const [detail, taskActivities, artifacts] = await Promise.all([
      api.getTask(taskId),
      api.getActivities(taskId),
      api.getArtifacts(taskId),
    ])
    if (selectedId.value !== taskId) return
    selectedTask.value = detail
    activities.value = taskActivities
    taskArtifacts.value = artifacts
    if (
      previousTask &&
      ['thinking', 'working', 'waiting', 'waiting_approval'].includes(previousTask.status) &&
      ['completed', 'failed'].includes(detail.status)
    ) {
      const fileCount = artifacts.filter((artifact) => artifact.kind === 'file').length
      officeNotice.value = detail.status === 'completed'
        ? `Tugas #${detail.id} selesai${fileCount ? ` · ${fileCount} file siap diperiksa` : ' · hasil siap diperiksa'}.`
        : `Tugas #${detail.id} gagal: ${detail.error_message ?? detail.instruction}`
      if (noticeTimer) clearTimeout(noticeTimer)
      noticeTimer = setTimeout(() => { officeNotice.value = '' }, 9000)
    }
  } catch (error) {
    if (selectedId.value === taskId) {
      selectedTask.value = null
      activities.value = []
      taskArtifacts.value = []
      errorMessage.value = getErrorMessage(error)
    }
  }
}

async function refreshDashboard() {
  try {
    health.value = await api.getHealth()
    if (health.value.database !== 'connected') {
      agents.value = []
      tasks.value = []
      errorMessage.value = 'MySQL belum tersambung. Periksa DATABASE_URL dan jalankan migrasi Alembic.'
      return
    }
    const [agentsResult, tasksResult] = await Promise.all([
      api.getAgents(),
      api.getTasks(showArchivedTasks.value),
    ])
    agents.value = agentsResult
    tasks.value = tasksResult
    if (selectedId.value !== null) await loadTask(selectedId.value)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
    health.value = null
    agents.value = []
  } finally {
    loading.value = false
  }
}

async function retryTask(taskId: number) {
  const stayInOffice = activeEditorId.value === 'office' && activityView.value === 'office'
  errorMessage.value = ''
  try {
    const created = await api.retryTask(taskId)
    selectedId.value = created.id
    if (stayInOffice) {
      officeRailView.value = 'task'
    } else {
      activeEditorId.value = created.id
    }
    selectedAgentName.value = null
    if (!openTaskIds.value.includes(created.id)) openTaskIds.value.push(created.id)
    await refreshDashboard()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function cancelActiveTask() {
  if (!selectedTask.value) return
  errorMessage.value = ''
  try {
    await api.cancelTask(selectedTask.value.id)
    await refreshDashboard()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function archiveActiveTask(archived: boolean) {
  if (!selectedTask.value) return
  errorMessage.value = ''
  try {
    await api.setTaskArchived(selectedTask.value.id, archived)
    await refreshDashboard()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function toggleArchivedTasks() {
  showArchivedTasks.value = !showArchivedTasks.value
  await refreshDashboard()
}

async function selectTask(taskId: number) {
  const stayInOffice = activeEditorId.value === 'office' && activityView.value === 'office'
  errorMessage.value = ''
  if (stayInOffice) {
    officeRailView.value = 'task'
  } else {
    activeEditorId.value = taskId
  }
  editorTab.value = 'overview'
  selectedAgentName.value = null
  if (!openTaskIds.value.includes(taskId)) openTaskIds.value.push(taskId)
  await loadTask(taskId)
}

function closeTaskTab(taskId: number) {
  openTaskIds.value = openTaskIds.value.filter((id) => id !== taskId)
  if (activeEditorId.value === taskId) {
    activeEditorId.value = 'office'
    selectedAgentName.value = null
  }
}

async function submitInstruction(instruction: string) {
  const stayInOffice = activeEditorId.value === 'office' && activityView.value === 'office'
  sending.value = true
  errorMessage.value = ''
  try {
    const created = await api.createTask(instruction)
    selectedId.value = created.id
    if (!openTaskIds.value.includes(created.id)) openTaskIds.value.push(created.id)
    if (stayInOffice) {
      officeRailView.value = 'task'
    } else {
      activeEditorId.value = created.id
      activityView.value = 'tasks'
    }
    composerOpen.value = false
    editorTab.value = 'overview'
    await refreshDashboard()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    sending.value = false
  }
}

function startNewTask() {
  activityView.value = 'tasks'
  composerOpen.value = true
  sidebarOpen.value = true
  nextTick(() => document.querySelector<HTMLTextAreaElement>('#task-instruction')?.focus())
}

async function selectAgent(agentName: string) {
  const stayInOffice = activeEditorId.value === 'office' && activityView.value === 'office'
  selectedAgentName.value = agentName
  if (!stayInOffice) activityView.value = 'agents'
  const firstTask = tasks.value[0]
  if (!selectedTask.value && firstTask) {
    if (stayInOffice) {
      await loadTask(firstTask.id)
      selectedAgentName.value = agentName
      editorTab.value = 'steps'
      return
    }
    await selectTask(firstTask.id)
    selectedAgentName.value = agentName
    editorTab.value = 'steps'
    return
  }
  if (selectedTask.value) {
    const taskId = selectedTask.value.id
    if (!stayInOffice) activeEditorId.value = taskId
    if (!openTaskIds.value.includes(taskId)) {
      openTaskIds.value.push(taskId)
    }
    editorTab.value = 'steps'
  }
}

function handleShortcut(event: KeyboardEvent) {
  const key = event.key.toLowerCase()
  if ((event.ctrlKey || event.metaKey) && key === 'n') {
    event.preventDefault()
    startNewTask()
  } else if ((event.ctrlKey || event.metaKey) && key === 'b') {
    event.preventDefault()
    sidebarOpen.value = !sidebarOpen.value
  } else if ((event.ctrlKey || event.metaKey) && key === 'j') {
    event.preventDefault()
    bottomOpen.value = !bottomOpen.value
  } else if ((event.ctrlKey || event.metaKey) && key === 'k') {
    event.preventDefault()
    if (activityView.value !== 'knowledge') activityView.value = 'tasks'
    sidebarOpen.value = true
    nextTick(() => searchInput.value?.focus())
  } else if (event.key === 'Escape' && composerOpen.value) {
    composerOpen.value = false
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleShortcut)
  if (window.matchMedia('(max-width: 680px)').matches) sidebarOpen.value = false
  await refreshDashboard()
  pollTimer = setInterval(refreshDashboard, 2500)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleShortcut)
  if (pollTimer) clearInterval(pollTimer)
  if (noticeTimer) clearTimeout(noticeTimer)
})
</script>

<template>
  <main class="ide-shell">
    <header class="ide-titlebar">
      <NuxtLink class="brand ide-brand" to="/" aria-label="Virtual Office AI beranda">
        <span class="brand-wordmark-nf">Virtual Office AI</span>
      </NuxtLink>
      <div class="titlebar-center"><span>Ruang kerja lokal</span></div>
      <div class="titlebar-actions">
        <span class="connection-pill" :class="{ 'connection-offline': !isReady }"><i />{{ connectionLabel }}</span>
        <button class="titlebar-new-task" type="button" @click="startNewTask"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 3v10M3 8h10" /></svg> Tugas baru <kbd>Ctrl N</kbd></button>
      </div>
    </header>

    <div v-if="errorMessage" class="ide-error" role="alert">
      <span class="error-icon">!</span><span>{{ errorMessage }}</span>
      <button type="button" aria-label="Tutup pesan" @click="errorMessage = ''">×</button>
    </div>
    <div v-if="officeNotice" class="office-notice" role="status" aria-live="polite">
      <span>{{ officeNotice }}</span>
      <button type="button" aria-label="Tutup notifikasi hasil" @click="officeNotice = ''">Tutup</button>
    </div>

    <div class="ide-layout" :class="{ 'sidebar-collapsed': !sidebarOpen, 'ide-layout-visual-office': activeEditorId === 'office' && activityView === 'office' }">
      <nav v-if="activityView !== 'office' || activeEditorId !== 'office'" class="activity-bar" aria-label="Workspace navigation">
        <button
          v-for="item in [
            { id: 'office', label: 'Kantor' },
            { id: 'agents', label: 'Agent' },
            { id: 'tasks', label: 'Tugas' },
            { id: 'knowledge', label: 'Dokumen' },
          ] as const"
          :key="item.id"
          type="button"
          class="activity-button"
          :class="{ 'activity-button-active': activityView === item.id }"
          :aria-label="item.label"
          :title="item.label"
          @click="activityView = item.id; sidebarOpen = true"
        >
          <svg v-if="item.id === 'office'" viewBox="0 0 20 20" aria-hidden="true"><rect x="3" y="3" width="14" height="14" rx="1" /><path d="M7 3v14M13 3v14M3 8h14M3 13h14" /></svg>
          <svg v-else-if="item.id === 'agents'" viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="6.5" r="3" /><path d="M4.5 17c.4-3.1 2.4-4.8 5.5-4.8s5.1 1.7 5.5 4.8" /></svg>
          <svg v-else-if="item.id === 'tasks'" viewBox="0 0 20 20" aria-hidden="true"><path d="M7 5h9M7 10h9M7 15h9" /><path d="m3.5 5 .8.8L5.7 4M3.5 10l.8.8 1.4-1.8M3.5 15l.8.8 1.4-1.8" /></svg>
          <svg v-else viewBox="0 0 20 20" aria-hidden="true"><path d="M3.5 4.5h5l1.5 1.8h6.5v9.2H3.5z" /><path d="M3.5 7.5h13" /></svg>
          <small>{{ item.label }}</small>
        </button>
        <button
          class="activity-bottom-toggle"
          type="button"
          :aria-label="sidebarOpen ? 'Sembunyikan sidebar' : 'Tampilkan sidebar'"
          title="Toggle sidebar (Ctrl+B)"
          @click="sidebarOpen = !sidebarOpen"
        ><svg viewBox="0 0 16 16" aria-hidden="true"><rect x="2.5" y="2.5" width="11" height="11" rx="2" /><path d="M6 3v10" /></svg></button>
      </nav>

      <aside v-if="sidebarOpen && (activityView !== 'office' || activeEditorId !== 'office')" class="ide-sidebar">
        <div class="sidebar-heading">
          <strong>{{ activityView === 'office' ? 'OFFICE' : activityView.toUpperCase() }}</strong>
          <button type="button" aria-label="Sembunyikan sidebar" title="Sembunyikan sidebar (Ctrl+B)" @click="sidebarOpen = false"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="m10 3-5 5 5 5" /></svg></button>
        </div>

        <template v-if="activityView === 'office'">
          <div class="sidebar-workspace">
            <span class="sidebar-section-label">RUANG KERJA</span>
            <button class="sidebar-entry sidebar-entry-current" type="button" @click="activeEditorId = 'office'">
              <span class="sidebar-entry-icon">01</span><span>Lantai kantor</span><i class="sidebar-live-dot" />
            </button>
            <button class="sidebar-entry" type="button" @click="startNewTask">
              <span class="sidebar-entry-icon sidebar-entry-plus"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 3v10M3 8h10" /></svg></span><span>Tugas baru</span><kbd>Ctrl N</kbd>
            </button>
          </div>
          <div class="sidebar-quick-status">
            <span class="sidebar-section-label">STATUS LAYANAN</span>
            <div><i :class="{ 'is-offline': !isReady }" /><span>{{ isReady ? 'Backend tersambung' : 'Backend offline' }}</span></div>
            <div><i :class="{ 'is-offline': !health?.ai_configured }" /><span>{{ health?.ai_provider ?? 'AI' }} {{ health?.ai_configured ? 'siap' : 'belum diatur' }}</span></div>
            <div><i /><span>Dokumen RAG {{ health?.rag_mode === 'keyword_local' ? 'aktif · kata kunci lokal' : 'aktif · Gemini embeddings' }}</span></div>
            <p>Pergerakan agent mengikuti aktivitas tugas.</p>
          </div>
        </template>

        <template v-else-if="activityView === 'agents'">
          <div class="sidebar-section-title"><span class="sidebar-section-label">TIM AGENT</span><small>{{ agents.length }} terdaftar</small></div>
          <AgentsAgentStatusPanel :agents="agents" :loading="loading" :selected-agent-name="selectedAgentName" @select="selectAgent" />
          <p class="sidebar-hint">Pilih agent untuk melihat langkah dan hasil tugasnya.</p>
        </template>

        <template v-else-if="activityView === 'tasks'">
          <div class="sidebar-section-title"><span class="sidebar-section-label">DAFTAR TUGAS</span><button type="button" @click="startNewTask"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 3v10M3 8h10" /></svg> Baru</button></div>
          <label class="sidebar-search"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5" /><path d="m12.2 12.2 4 4" /></svg><input ref="searchInput" v-model="searchQuery" type="search" placeholder="Cari tugas..." aria-label="Cari tugas"><kbd>Ctrl K</kbd></label>
          <ChatPanel v-if="composerOpen" :sending="sending" :disabled="!canCreateTask" :disabled-reason="chatDisabledReason" @submit="submitInstruction" />
          <TasksTaskConsole
            :tasks="filteredTasks"
            :selected-id="selectedId"
            :loading="loading"
            :show-archived="showArchivedTasks"
            @select="selectTask"
            @toggle-archived="toggleArchivedTasks"
          />
        </template>

        <template v-else>
          <div class="sidebar-section-title"><span class="sidebar-section-label">PUSTAKA DOKUMEN</span><small>RAG</small></div>
          <label class="sidebar-search"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5" /><path d="m12.2 12.2 4 4" /></svg><input ref="searchInput" v-model="searchQuery" type="search" placeholder="Cari dokumen..." aria-label="Cari dokumen"><kbd>Ctrl K</kbd></label>
          <KnowledgeLibrary :search="searchQuery" />
        </template>
      </aside>

      <section class="ide-main" :class="{ 'ide-main-office': activeEditorId === 'office' }">
        <div v-show="activeEditorId !== 'office'" class="editor-tabs" role="tablist" aria-label="Open editors">
          <div
            class="editor-tab"
            :class="{ 'editor-tab-active': activeEditorId === 'office' }"
          ><button class="editor-tab-main" role="tab" :aria-selected="activeEditorId === 'office'" type="button" @click="activeEditorId = 'office'"><span class="tab-pixel-icon" aria-hidden="true"><svg viewBox="0 0 16 16"><rect x="2.5" y="2.5" width="11" height="11" rx="2" /><path d="M6 3v10M10 3v10M3 6h10M3 10h10" /></svg></span><span>Lantai kantor</span></button></div>
          <div
            v-for="taskId in openTaskIds"
            :key="taskId"
            class="editor-tab"
            :class="{ 'editor-tab-active': activeEditorId === taskId }"
          >
            <button class="editor-tab-main" role="tab" :aria-selected="activeEditorId === taskId" type="button" @click="selectTask(taskId)">
              <span class="tab-task-mark" :class="`task-mark-${tasks.find((task) => task.id === taskId)?.status ?? 'pending'}`" />
              <span>{{ tasks.find((task) => task.id === taskId)?.instruction.slice(0, 24) ?? `Tugas #${taskId}` }}{{ (tasks.find((task) => task.id === taskId)?.instruction.length ?? 0) > 24 ? '…' : '' }}</span>
            </button>
            <button class="tab-close" :aria-label="`Tutup tugas ${taskId}`" type="button" @click="closeTaskTab(taskId)"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="m4 4 8 8M12 4l-8 8" /></svg></button>
          </div>
          <span class="editor-tabs-spacer" />
          <button class="icon-button" type="button" title="Tugas baru (Ctrl+N)" aria-label="Buat task baru" @click="startNewTask"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 3v10M3 8h10" /></svg></button>
        </div>

        <div class="editor-content">
          <template v-if="activeEditorId === 'office'">
            <div class="office-workspace">
              <section class="office-floor">
                <div class="office-floor-heading">
                  <div>
                    <span class="office-floor-kicker">VIRTUAL OFFICE AI</span>
                    <h1>Ruang kerja tim</h1>
                    <p>Aktivitas agent mengikuti progres tugas.</p>
                  </div>
                  <span class="office-live-badge" :class="{ 'office-live-badge-offline': !isReady }"><i />{{ isReady ? 'LIVE' : 'OFFLINE' }}</span>
                </div>
                <OfficeScene
                  :agents="agents"
                  :task="selectedTask"
                  :activities="activities"
                  :selected-agent-name="selectedAgentName"
                  @select-agent="selectAgent"
                />
                <div class="office-floor-footer">
                  <span><i />{{ selectedTask ? activeTaskLabel : 'Pilih tugas untuk melihat progres' }}</span>
                  <span>{{ agents.filter((agent) => ['thinking', 'working', 'waiting', 'waiting_approval'].includes(agent.status)).length }} / {{ agents.length }} agent aktif</span>
                </div>
              </section>
              <aside
                class="office-control-rail"
                :class="{ 'office-control-rail-task': officeRailView === 'task' }"
                :aria-label="officeRailView === 'team'
                  ? 'Kontrol tim kantor'
                  : officeRailView === 'knowledge'
                    ? 'Pustaka dokumen kantor'
                    : `Detail tugas ${selectedTask?.id ?? selectedId ?? ''}`"
              >
                <div class="office-rail-top">
                  <div>
                    <span class="office-rail-kicker">{{ officeRailView === 'team' ? 'TIM KAMU' : officeRailView === 'knowledge' ? 'RUANG KERJA' : `TUGAS #${selectedTask?.id ?? selectedId ?? ''}` }}</span>
                    <strong :class="{ 'office-rail-task-title': officeRailView === 'task' }">
                      {{ officeRailView === 'team' ? 'AI Agents' : officeRailView === 'knowledge' ? 'Dokumen' : selectedTask?.instruction ?? 'Memuat tugas...' }}
                    </strong>
                  </div>
                  <button
                    type="button"
                    :aria-label="officeRailView === 'team' ? 'Buka pustaka dokumen di panel kanan' : 'Kembali ke panel tim dan tugas'"
                    @click="officeRailView = officeRailView === 'team' ? 'knowledge' : 'team'"
                  >{{ officeRailView === 'team' ? 'Dokumen' : 'Tim & tugas' }}</button>
                </div>
                <template v-if="officeRailView === 'team'">
                  <AgentsAgentStatusPanel :agents="agents" :loading="loading" :selected-agent-name="selectedAgentName" @select="selectAgent" />
                  <TasksTaskConsole
                    :tasks="filteredTasks"
                    :selected-id="selectedId"
                    :loading="loading"
                    :show-archived="showArchivedTasks"
                    @select="selectTask"
                    @toggle-archived="toggleArchivedTasks"
                  />
                  <ChatPanel :sending="sending" :disabled="!canCreateTask" :disabled-reason="chatDisabledReason" @submit="submitInstruction" />
                  <div class="office-rail-status">
                    <i :class="{ 'office-status-offline': !isReady }" />
                    <span>{{ isReady ? 'Backend tersambung' : 'Menunggu backend' }}</span>
                    <small>{{ health?.ai_provider ?? 'AI' }}</small>
                  </div>
                </template>
                <template v-else>
                  <label v-if="officeRailView === 'knowledge'" class="office-knowledge-search">
                    <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5" /><path d="m12.2 12.2 4 4" /></svg>
                    <input v-model="searchQuery" type="search" placeholder="Cari dokumen..." aria-label="Cari dokumen">
                  </label>
                  <KnowledgeLibrary v-if="officeRailView === 'knowledge'" class="office-knowledge-library" :search="searchQuery" />
                  <template v-else>
                    <div v-if="selectedTask" class="office-task-actions">
                      <span class="task-editor-status" :class="`task-status-${selectedTask.status}`"><i />{{ selectedTask.status.replaceAll('_', ' ') }}</span>
                      <button v-if="activeTaskCanCancel" class="task-action-button" type="button" @click="cancelActiveTask">Batalkan</button>
                      <button v-if="selectedTask.status === 'failed'" class="task-action-button" type="button" @click="retryTask(selectedTask.id)">Coba lagi</button>
                      <button
                        v-if="['completed', 'failed', 'cancelled'].includes(selectedTask.status)"
                        class="task-action-button"
                        type="button"
                        @click="archiveActiveTask(!selectedTask.archived)"
                      >{{ selectedTask.archived ? 'Keluarkan dari arsip' : 'Arsipkan' }}</button>
                    </div>
                    <TasksTaskDetails
                      class="office-task-details"
                      :task="selectedTask"
                      :activities="activities"
                      :artifacts="taskArtifacts"
                      :loading="selectedTask?.id !== selectedId"
                      :active-tab="editorTab"
                      :selected-agent-name="selectedAgentName"
                      @update:active-tab="editorTab = $event"
                      @select-agent="selectAgent"
                    />
                  </template>
                </template>
              </aside>
            </div>
          </template>
          <template v-else>
            <div class="task-editor-title">
              <div><p class="editor-breadcrumb">TASKS <span>/</span> TASK #{{ activeTask?.id ?? activeEditorId }}</p><h1>{{ activeTask?.instruction ?? 'Loading task...' }}</h1></div>
              <div v-if="activeTask" class="task-editor-actions">
                <span class="task-editor-status" :class="`task-status-${activeTask.status}`"><i />{{ activeTask.status.replaceAll('_', ' ') }}</span>
                <button v-if="activeTaskCanCancel" class="task-action-button" type="button" @click="cancelActiveTask">Batalkan</button>
                <button v-if="activeTask.status === 'failed'" class="task-action-button" type="button" @click="retryTask(activeTask.id)">Coba lagi</button>
                <button
                  v-if="['completed', 'failed', 'cancelled'].includes(activeTask.status)"
                  class="task-action-button"
                  type="button"
                  @click="archiveActiveTask(!activeTask.archived)"
                >{{ activeTask.archived ? 'Keluarkan dari arsip' : 'Arsipkan' }}</button>
              </div>
            </div>
            <TasksTaskDetails
              :task="activeTask"
              :activities="activeTask ? activities : []"
              :artifacts="activeTask ? taskArtifacts : []"
              :loading="false"
              :active-tab="editorTab"
              :selected-agent-name="selectedAgentName"
              @update:active-tab="editorTab = $event"
              @select-agent="selectedAgentName = $event"
            />
          </template>
        </div>

        <section v-if="activeEditorId !== 'office'" class="bottom-panel" :class="{ 'bottom-panel-closed': !bottomOpen }" aria-label="Diagnostics panel">
          <div class="bottom-panel-heading">
            <div class="bottom-tabs" role="tablist">
              <button v-for="tab in [
                  { id: 'problems', label: 'MASALAH', count: problemCount },
                  { id: 'output', label: 'AKTIVITAS', count: 0 },
                  { id: 'terminal', label: 'STATUS', count: 0 },
              ] as const" :key="tab.id" type="button" role="tab" :aria-selected="bottomTab === tab.id" :class="{ 'bottom-tab-active': bottomTab === tab.id }" @click="bottomTab = tab.id; bottomOpen = true">
                {{ tab.label }}<span v-if="tab.count" class="problem-count">{{ tab.count }}</span>
              </button></div>
            <button class="bottom-collapse" type="button" :title="bottomOpen ? 'Tutup panel (Ctrl+J)' : 'Buka panel (Ctrl+J)'" :aria-label="bottomOpen ? 'Tutup panel bawah' : 'Buka panel bawah'" @click="bottomOpen = !bottomOpen"><svg viewBox="0 0 16 16" :class="{ 'icon-flipped': !bottomOpen }" aria-hidden="true"><path d="m4 6 4 4 4-4" /></svg></button>
          </div>
          <div v-if="bottomOpen" class="bottom-panel-content">
            <template v-if="bottomTab === 'problems'">
              <div v-if="!problemCount" class="diagnostic-empty">Tidak ada masalah terdeteksi</div>
              <button v-if="health && !health.ai_configured" class="diagnostic-row diagnostic-warning" type="button" @click="activityView = 'office'"><span>!</span><span>{{ health.ai_provider }} belum dikonfigurasi</span><small>Periksa API key dan model provider di backend/.env</small></button>
              <button v-for="task in tasks.filter((item) => item.status === 'failed')" :key="task.id" class="diagnostic-row diagnostic-error" type="button" @click="selectTask(task.id)"><span>×</span><span>Tugas #{{ task.id }} gagal</span><small>{{ task.error_message ?? task.instruction }}</small></button>
              <div v-if="errorMessage" class="diagnostic-row diagnostic-error"><span>×</span><span>Koneksi workspace</span><small>{{ errorMessage }}</small></div>
            </template>
            <template v-else-if="bottomTab === 'output'">
              <p v-if="!outputActivities.length" class="diagnostic-empty">Belum ada aktivitas untuk tugas yang dipilih.</p>
              <button v-for="activity in outputActivities" :key="activity.id" class="output-row" type="button" @click="selectAgent(activity.agent_name)">
                <time>{{ new Date(activity.created_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }) }}</time>
                <strong>{{ activity.agent_name.replaceAll('_', ' ') }}</strong><span>{{ activity.message }}</span><small>{{ activity.status }}</small>
              </button>
            </template>
            <pre v-else class="readonly-terminal">{{ terminalLines.join('\n') }}</pre>
          </div>
        </section>
      </section>
    </div>

    <footer class="ide-statusbar">
      <div class="statusbar-left"><span class="statusbar-connection"><i />{{ connectionLabel }}</span><span>VIRTUAL OFFICE AI</span><span>UTF-8</span></div>
      <div class="statusbar-right"><span>{{ health?.ai_provider ?? 'AI' }} · {{ health?.ai_configured ? 'siap' : 'belum diatur' }}</span><span>{{ activeTaskLabel }}</span><button type="button" @click="bottomOpen = !bottomOpen">MASALAH {{ problemCount }}</button></div>
    </footer>
  </main>
</template>
