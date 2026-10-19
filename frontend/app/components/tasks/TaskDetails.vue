<script setup lang="ts">
import type { Activity, TaskDetail } from '~/types/office'

defineProps<{ task: TaskDetail | null; activities: Activity[]; loading: boolean }>()

const statusLabels: Record<string, string> = {
  pending: 'Menunggu',
  thinking: 'Menganalisis',
  working: 'Berjalan',
  completed: 'Selesai',
  failed: 'Gagal',
}

function agentName(name: string) {
  return name.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}
</script>

<template>
  <section class="panel task-details">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">RUANG KERJA</p>
        <h2>Detail aktivitas</h2>
      </div>
      <span v-if="task" class="detail-task-id">TASK #{{ task.id }}</span>
    </div>
    <p v-if="loading" class="muted small-copy">Memuat detail...</p>
    <template v-else-if="task">
      <div class="detail-status" :class="`detail-${task.status}`">
        <span class="detail-status-dot" />
        <strong>{{ statusLabels[task.status] ?? task.status }}</strong>
      </div>
      <p v-if="task.summary" class="task-summary">{{ task.summary }}</p>
      <p v-else class="task-instruction">{{ task.instruction }}</p>
      <div v-if="task.error_message" class="error-banner" role="alert">
        {{ task.error_message }}
      </div>
      <div v-if="task.steps.length" class="steps-list">
        <h3>Langkah kerja</h3>
        <article v-for="step in task.steps" :key="step.id" class="step-card">
          <span class="step-number">{{ String(step.position).padStart(2, '0') }}</span>
          <div class="step-content">
            <div class="step-title-row">
              <strong>{{ step.title }}</strong>
              <span class="step-status">{{ statusLabels[step.status] ?? step.status }}</span>
            </div>
            <small>{{ agentName(step.agent_name) }} · {{ step.expected_output }}</small>
            <p v-if="step.output" class="step-output">{{ step.output }}</p>
          </div>
        </article>
      </div>
      <div class="activity-list">
        <h3>Aktivitas terbaru</h3>
        <p v-if="activities.length === 0" class="muted small-copy">Belum ada aktivitas.</p>
        <article v-for="activity in [...activities].reverse().slice(0, 6)" :key="activity.id" class="activity-row">
          <i :class="`activity-${activity.status}`" />
          <span><strong>{{ agentName(activity.agent_name) }}</strong> {{ activity.message }}</span>
        </article>
      </div>
    </template>
    <p v-else class="empty-state">Pilih tugas untuk melihat progres dan hasil agent.</p>
  </section>
</template>
