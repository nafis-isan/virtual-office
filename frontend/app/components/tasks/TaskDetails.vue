<script setup lang="ts">
import MarkdownIt from 'markdown-it'
import type { Activity, TaskDetail } from '~/types/office'

const props = defineProps<{
  task: TaskDetail | null
  activities: Activity[]
  loading: boolean
  activeTab: 'overview' | 'steps' | 'output' | 'sources'
  selectedAgentName: string | null
}>()
const emit = defineEmits<{
  'update:activeTab': [tab: 'overview' | 'steps' | 'output' | 'sources']
  'select-agent': [agentName: string]
}>()

const statusLabels: Record<string, string> = {
  pending: 'Dalam antrean',
  thinking: 'Menyusun rencana',
  working: 'Berjalan',
  waiting: 'Menunggu',
  waiting_approval: 'Perlu persetujuan',
  completed: 'Selesai',
  failed: 'Gagal',
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
const sourceCitations = computed(() => {
  const summary = props.task?.summary ?? ''
  const match = summary.match(/Sumber dokumen:\s*([\s\S]*)$/i)
  if (!match) return []
  return [...(match[1] ?? '').matchAll(/\[(S\d+)\]\s*([^;]+)/g)].map((item) => ({
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
        <div class="document-section-label">HASIL AGENT</div>
        <article v-for="step in outputSteps" :key="step.id" class="output-document">
          <header><span class="output-file-icon">TXT</span><strong>{{ step.title }}</strong><button type="button" @click="emit('select-agent', step.agent_name)">{{ agentName(step.agent_name) }}</button></header>
          <div class="markdown-body output-markdown" v-html="step.outputHtml" />
        </article>
        <p v-if="!outputSteps.length" class="document-placeholder">Hasil kerja agent akan muncul di sini setelah setiap langkah selesai.</p>
      </div>

      <div v-else class="task-document-body">
        <div class="document-section-label">SUMBER PENGETAHUAN</div>
        <p class="sources-intro">Referensi dari pustaka dokumen yang dikutip dalam ringkasan project manager.</p>
        <article v-for="source in sourceCitations" :key="`${source.label}-${source.citation}`" class="source-document">
          <span class="source-reference">{{ source.label }}</span>
          <div><strong>{{ source.citation }}</strong><small>Dirujuk dalam ringkasan tugas</small></div>
        </article>
        <p v-if="!sourceCitations.length" class="document-placeholder">Belum ada sumber dokumen yang dikutip. Tambahkan dokumen ke Pustaka agar agent dapat mengambil konteks.</p>
      </div>
    </template>
    <p v-else class="document-placeholder task-no-selection">Pilih tugas dari sidebar untuk membuka detail pekerjaannya.</p>
  </section>
</template>
