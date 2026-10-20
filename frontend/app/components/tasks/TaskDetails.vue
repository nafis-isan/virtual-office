<script setup lang="ts">
import MarkdownIt from 'markdown-it'
import type { Activity, TaskArtifact, TaskDetail } from '~/types/office'

const props = defineProps<{
  task: TaskDetail | null
  activities: Activity[]
  artifacts: TaskArtifact[]
  loading: boolean
  activeTab: 'overview' | 'steps' | 'output' | 'sources'
  selectedAgentName: string | null
}>()
const emit = defineEmits<{
  'update:activeTab': [tab: 'overview' | 'steps' | 'output' | 'sources']
  'select-agent': [agentName: string]
}>()

const api = useOfficeApi()
const saveDialogArtifact = ref<TaskArtifact | null>(null)
const savePath = ref('')
const comparison = ref<{
  path: string
  exists: boolean
  current_content: string | null
  current_sha256: string | null
} | null>(null)
const saveError = ref('')
const saveNotice = ref('')
const comparing = ref(false)
const saving = ref(false)

const statusLabels: Record<string, string> = {
  pending: 'Dalam antrean',
  thinking: 'Menyusun rencana',
  working: 'Berjalan',
  waiting: 'Menunggu',
  waiting_approval: 'Perlu persetujuan',
  completed: 'Selesai',
  failed: 'Gagal',
  cancelled: 'Dibatalkan',
}

const markdown = new MarkdownIt({ html: false, linkify: false, breaks: false })
const summaryHtml = computed(() => {
  const summary = props.task?.summary?.replace(/\n\nSumber dokumen:[\s\S]*$/i, '').trim()
  return summary ? markdown.render(summary) : ''
})
const outputSteps = computed(() =>
  (props.task?.steps ?? [])
    .filter((step) => step.output)
    .map((step) => ({ ...step, outputHtml: markdown.render(step.output ?? '') })),
)
const fileArtifacts = computed(() =>
  props.artifacts
    .filter((artifact) => artifact.kind === 'file')
    .map((artifact) => ({
      ...artifact,
      agent_name: props.task?.steps.find((step) => step.id === artifact.step_id)?.agent_name ?? '',
    })),
)
const sourceCitations = computed(() => {
  const summary = props.task?.summary ?? ''
  const match = summary.match(/Sumber dokumen:\s*([\s\S]*)$/i)
  if (!match) return []
  const citedSources = new Set(
    [summary.replace(/\n\nSumber dokumen:[\s\S]*$/i, ''), ...(props.task?.steps.map((step) => step.output ?? '') ?? [])]
      .flatMap((text) => [...text.matchAll(/\[(S\d+)\]/g)].map((item) => item[1] ?? '')),
  )
  return [...(match[1] ?? '').matchAll(/\[(S\d+)\]\s*([^;]+)/g)]
    .filter((item) => citedSources.has(item[1] ?? ''))
    .map((item) => ({
    label: item[1] ?? '',
    citation: item[2]?.trim() ?? '',
  }))
})
const visibleSteps = computed(() => {
  if (!props.task) return []
  if (!props.selectedAgentName) return props.task.steps
  return props.task.steps.filter((step) => step.agent_name === props.selectedAgentName)
})

function agentName(name: string) {
  return name.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function errorText(error: unknown) {
  if (typeof error === 'object' && error !== null && 'data' in error) {
    const data = error.data
    if (typeof data === 'object' && data !== null && 'detail' in data && typeof data.detail === 'string') {
      return data.detail
    }
  }
  return 'Permintaan file gagal. Periksa koneksi backend lalu coba lagi.'
}

function downloadArtifact(artifact: TaskArtifact) {
  const blob = new Blob([artifact.content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = artifact.name.split('/').at(-1) ?? artifact.name
  link.click()
  URL.revokeObjectURL(url)
}

function downloadProject() {
  if (!props.task || !fileArtifacts.value.length) return
  const link = document.createElement('a')
  link.href = api.getArtifactBundleUrl(props.task.id)
  link.download = `nf-office-task-${props.task.id}.zip`
  link.click()
}

function openSaveDialog(artifact: TaskArtifact) {
  saveDialogArtifact.value = artifact
  savePath.value = artifact.name
  comparison.value = null
  saveError.value = ''
  saveNotice.value = ''
}

function closeSaveDialog() {
  if (comparing.value || saving.value) return
  saveDialogArtifact.value = null
  comparison.value = null
  saveError.value = ''
}

async function compareFile() {
  if (!props.task || !saveDialogArtifact.value) return
  comparing.value = true
  saveError.value = ''
  try {
    comparison.value = await api.compareArtifact(
      props.task.id,
      saveDialogArtifact.value.id,
      savePath.value,
    )
  } catch (error) {
    comparison.value = null
    saveError.value = errorText(error)
  } finally {
    comparing.value = false
  }
}

async function saveFile() {
  if (!props.task || !saveDialogArtifact.value || !comparison.value) return
  saving.value = true
  saveError.value = ''
  try {
    const saved = await api.saveArtifact(
      props.task.id,
      saveDialogArtifact.value.id,
      comparison.value.path,
      comparison.value.exists,
      comparison.value.current_sha256,
    )
    saveNotice.value = `File tersimpan di workspace/${saved.path}`
    saveDialogArtifact.value = null
  } catch (error) {
    comparison.value = null
    saveError.value = errorText(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="task-document">
    <nav class="task-document-tabs" role="tablist" aria-label="Task document sections">
      <button
        v-for="tab in [
          { id: 'overview', label: 'Overview' },
          { id: 'steps', label: 'Agent Steps' },
          { id: 'output', label: 'Output' },
          { id: 'sources', label: 'Sources' },
        ] as const"
        :key="tab.id"
        type="button"
        role="tab"
        :aria-selected="activeTab === tab.id"
        :class="{ 'task-document-tab-active': activeTab === tab.id }"
        @click="emit('update:activeTab', tab.id)"
      >{{ tab.label }}<span v-if="tab.id === 'steps' && task">{{ task.steps.length }}</span><span v-if="tab.id === 'sources' && sourceCitations.length">{{ sourceCitations.length }}</span></button>
    </nav>

    <p v-if="loading" class="muted small-copy">Loading task document...</p>
    <template v-else-if="task">
      <div v-if="activeTab === 'overview'" class="task-document-body">
        <div class="document-section-label">INSTRUKSI</div>
        <p class="document-instruction">{{ task.instruction }}</p>
        <div class="document-meta-grid">
          <div><small>STATUS</small><strong :class="`text-status-${task.status}`">{{ statusLabels[task.status] ?? task.status }}</strong></div>
          <div><small>DIBUAT</small><strong>{{ new Date(task.created_at).toLocaleString('id-ID') }}</strong></div>
          <div><small>LANGKAH AGENT</small><strong>{{ task.steps.length }}</strong></div>
        </div>
        <div v-if="task.error_message" class="document-error" role="alert">
          <strong>Tugas gagal</strong><p>{{ task.error_message }}</p>
        </div>
        <section class="document-prose">
          <div class="document-section-label">RINGKASAN PROJECT MANAGER</div>
          <div v-if="summaryHtml" class="markdown-body summary-markdown" v-html="summaryHtml" />
          <p v-else class="document-placeholder">Ringkasan akan muncul setelah tugas selesai.</p>
        </section>
        <section v-if="activities.length" class="document-activity-preview">
          <div class="document-section-label">AKTIVITAS TERBARU</div>
          <button v-for="activity in [...activities].reverse().slice(0, 4)" :key="activity.id" type="button" @click="emit('select-agent', activity.agent_name)">
            <time>{{ new Date(activity.created_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }) }}</time>
            <strong>{{ agentName(activity.agent_name) }}</strong><span>{{ activity.message }}</span>
          </button>
        </section>
      </div>

      <div v-else-if="activeTab === 'steps'" class="task-document-body">
        <div class="document-toolbar">
          <div><div class="document-section-label">LANGKAH AGENT</div><p>{{ selectedAgentName ? `Difilter ke ${agentName(selectedAgentName)}` : 'Urutan kerja dari project manager ke agent specialist.' }}</p></div>
          <button v-if="selectedAgentName" type="button" @click="emit('select-agent', '')">Hapus filter</button>
        </div>
        <div v-if="visibleSteps.length" class="document-steps">
          <article v-for="step in visibleSteps" :key="step.id" class="document-step">
            <div class="document-step-rail"><span>{{ String(step.position).padStart(2, '0') }}</span><i /></div>
            <div class="document-step-copy">
              <div class="document-step-heading">
                <button type="button" @click="emit('select-agent', step.agent_name)">{{ agentName(step.agent_name) }}</button>
                <span class="document-step-status" :class="`text-status-${step.status}`">{{ statusLabels[step.status] ?? step.status }}</span>
              </div>
              <h2>{{ step.title }}</h2>
              <p>{{ step.expected_output }}</p>
            </div>
          </article>
        </div>
        <p v-else class="document-placeholder">{{ selectedAgentName ? 'Tidak ada langkah agent ini pada tugas yang dipilih.' : 'Project manager belum membuat langkah kerja.' }}</p>
      </div>

      <div v-else-if="activeTab === 'output'" class="task-document-body">
        <div class="document-toolbar">
          <div><div class="document-section-label">HASIL AGENT</div><p>{{ fileArtifacts.length }} file siap diunduh</p></div>
          <button v-if="fileArtifacts.length" type="button" @click="downloadProject">Unduh semua sebagai ZIP</button>
        </div>
        <section v-if="fileArtifacts.length" class="generated-files">
          <div class="document-section-label">FILE HASIL AGENT</div>
          <article v-for="file in fileArtifacts" :key="file.id" class="generated-file">
            <header>
              <span class="output-file-icon">FILE</span>
              <div><strong>{{ file.name }}</strong><small>{{ agentName(file.agent_name) }}</small></div>
              <button type="button" @click="downloadArtifact(file)">Unduh</button>
              <button type="button" @click="openSaveDialog(file)">Simpan ke proyek</button>
            </header>
            <details>
              <summary>Pratinjau file</summary>
              <pre><code>{{ file.content }}</code></pre>
            </details>
          </article>
        </section>
        <p v-if="saveNotice" class="save-success-message" role="status">{{ saveNotice }}</p>
        <article v-for="step in outputSteps" :key="step.id" class="output-document">
          <header><span class="output-file-icon">TXT</span><strong>{{ step.title }}</strong><button type="button" @click="emit('select-agent', step.agent_name)">{{ agentName(step.agent_name) }}</button></header>
          <div class="markdown-body output-markdown" v-html="step.outputHtml" />
        </article>
        <p v-if="!outputSteps.length && !fileArtifacts.length" class="document-placeholder">Hasil kerja agent akan muncul di sini setelah setiap langkah selesai.</p>
      </div>

      <div v-else class="task-document-body">
        <div class="document-section-label">SUMBER PENGETAHUAN</div>
        <p class="sources-intro">Dokumen yang benar-benar dirujuk oleh agent pada hasil dan ringkasan tugas.</p>
        <article v-for="source in sourceCitations" :key="`${source.label}-${source.citation}`" class="source-document">
          <span class="source-reference">{{ source.label }}</span>
          <div><strong>{{ source.citation }}</strong><small>Dirujuk dalam ringkasan tugas</small></div>
        </article>
        <p v-if="!sourceCitations.length" class="document-placeholder">Belum ada sumber dokumen yang dikutip. Tambahkan dokumen ke Pustaka agar agent dapat mengambil konteks.</p>
      </div>

      <div v-if="saveDialogArtifact" class="file-save-backdrop" role="presentation" @click.self="closeSaveDialog">
        <section class="file-save-dialog" role="dialog" aria-modal="true" aria-labelledby="save-dialog-title">
          <header><div><p class="document-section-label">WORKSPACE TERBATAS</p><h2 id="save-dialog-title">Simpan file ke proyek</h2></div><button type="button" aria-label="Tutup dialog" @click="closeSaveDialog">×</button></header>
          <p class="save-dialog-note">File hanya disimpan di dalam folder workspace yang dikonfigurasi backend. Pilih lokasi relatif, lalu tinjau perubahan sebelum menyimpan.</p>
          <label class="save-path-label">Lokasi relatif di workspace
            <div><span>workspace/</span><input v-model="savePath" type="text" :disabled="comparing || saving" @input="comparison = null"></div>
          </label>
          <p v-if="saveError" class="save-dialog-message" role="status">{{ saveError }}</p>
          <section v-if="comparison" class="file-comparison">
            <p>{{ comparison.exists ? 'File tujuan sudah ada. Tinjau perubahan sebelum mengonfirmasi penimpaan.' : 'File baru akan dibuat di lokasi ini.' }}</p>
            <div v-if="comparison.exists" class="file-comparison-columns">
              <div><strong>Versi saat ini</strong><pre><code>{{ comparison.current_content }}</code></pre></div>
              <div><strong>Versi agent</strong><pre><code>{{ saveDialogArtifact.content }}</code></pre></div>
            </div>
            <pre v-else class="new-file-preview"><code>{{ saveDialogArtifact.content }}</code></pre>
          </section>
          <footer>
            <button type="button" :disabled="comparing || saving || !savePath.trim()" @click="compareFile">{{ comparing ? 'Memeriksa...' : 'Tinjau perubahan' }}</button>
            <button v-if="comparison" class="save-confirm-button" type="button" :disabled="saving" @click="saveFile">
              {{ saving ? 'Menyimpan...' : comparison.exists ? 'Konfirmasi dan timpa' : 'Konfirmasi dan simpan' }}
            </button>
          </footer>
        </section>
      </div>
    </template>
    <p v-else class="document-placeholder task-no-selection">Pilih tugas dari sidebar untuk membuka detail pekerjaannya.</p>
  </section>
</template>
