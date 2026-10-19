<script setup lang="ts">
import type { Activity, Agent, Task, TaskDetail } from '~/types/office'

useHead({
  title: 'Visual Office AI',
  meta: [{ name: 'description', content: 'Kantor virtual untuk tim AI multi-agent.' }],
})

const api = useOfficeApi()
const agents = ref<Agent[]>([])
const tasks = ref<Task[]>([])
const selectedTask = ref<TaskDetail | null>(null)
const activities = ref<Activity[]>([])
const selectedId = ref<number | null>(null)
const health = ref<{ status: string; database: string; gemini_configured: boolean } | null>(null)
const loading = ref(true)
const sending = ref(false)
const errorMessage = ref('')
let pollTimer: ReturnType<typeof setInterval> | undefined

const isReady = computed(() => health.value?.database === 'connected')
const connectionLabel = computed(() => {
  if (!health.value) return 'Menghubungkan...'
  return health.value.database === 'connected' ? 'Backend terhubung' : 'Database terputus'
})

function getErrorMessage(error: unknown) {
  if (typeof error === 'object' && error !== null && 'data' in error) {
    const data = error.data
    if (typeof data === 'object' && data !== null && 'detail' in data && typeof data.detail === 'string') {
      return data.detail
    }
  }
  return 'Tidak dapat menghubungi backend. Pastikan FastAPI berjalan di localhost:8000.'
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
    const [agentsResult, tasksResult] = await Promise.all([api.getAgents(), api.getTasks()])
    agents.value = agentsResult
    tasks.value = tasksResult
    if (selectedId.value !== null) {
      const detail = await api.getTask(selectedId.value)
      selectedTask.value = detail
      activities.value = await api.getActivities(selectedId.value)
    }
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
    health.value = null
    agents.value = []
  } finally {
    loading.value = false
  }
}

async function selectTask(taskId: number) {
  selectedId.value = taskId
  errorMessage.value = ''
  try {
    selectedTask.value = await api.getTask(taskId)
    activities.value = await api.getActivities(taskId)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function submitInstruction(instruction: string) {
  sending.value = true
  errorMessage.value = ''
  try {
    const created = await api.createTask(instruction)
    selectedId.value = created.id
    await refreshDashboard()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    sending.value = false
  }
}

onMounted(async () => {
  await refreshDashboard()
  pollTimer = setInterval(refreshDashboard, 2500)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <NuxtLink class="brand" to="/" aria-label="Visual Office AI beranda">
        <span class="brand-mark"><i /><i /><i /><i /></span>
        <span>visual<span class="brand-light">office</span><small>AI WORKSPACE</small></span>
      </NuxtLink>
      <div class="topbar-right">
        <span class="connection-pill" :class="{ 'connection-offline': !isReady }">
          <i />{{ connectionLabel }}
        </span>
        <span class="date-label">WORKSPACE · LOKAL</span>
        <div class="user-mark">VA</div>
      </div>
    </header>

    <section class="welcome-row">
      <div>
        <p class="eyebrow">SENIN · AI PROJECT STUDIO</p>
        <h1>Selamat datang di <span>kantor.</span></h1>
        <p class="welcome-subtitle">Ruang kolaborasi digital untuk ide yang jadi kenyataan.</p>
      </div>
      <div class="welcome-note"><span>✳</span><div><strong>Empat peran.</strong><small>Satu tim yang fokus.</small></div></div>
    </section>

    <div v-if="errorMessage" class="connection-error" role="alert">
      <span>{{ errorMessage }}</span>
      <button type="button" aria-label="Tutup pesan" @click="errorMessage = ''">×</button>
    </div>

    <section class="dashboard-grid">
      <div class="scene-column">
        <div class="section-heading">
          <div><p class="eyebrow">THE VIRTUAL FLOOR</p><h2>Office floor</h2></div>
          <span class="scene-caption"><i /> AGENT AKTIF → AREA KOLABORASI</span>
        </div>
        <OfficeScene :agents="agents" />
        <AgentsAgentStatusPanel :agents="agents" :loading="loading" />
      </div>
      <div class="workspace-column">
        <ChatPanel :sending="sending" :disabled="!isReady" @submit="submitInstruction" />
        <TasksTaskConsole
          :tasks="tasks"
          :selected-id="selectedId"
          :loading="loading"
          @select="selectTask"
        />
        <TasksTaskDetails :task="selectedTask" :activities="activities" :loading="false" />
      </div>
    </section>
    <footer class="app-footer">
      <span>VISUAL OFFICE AI <i>·</i> LOKAL</span>
      <span v-if="health && !health.gemini_configured" class="footer-warning">
        Gemini belum dikonfigurasi — tambahkan GEMINI_API_KEY dan GEMINI_MODEL di backend/.env.
      </span>
      <span v-else>API key tersimpan di backend, tidak di browser.</span>
    </footer>
  </main>
</template>
