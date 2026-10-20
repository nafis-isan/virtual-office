<script setup lang="ts">
import type { Task } from '~/types/office'

defineProps<{ tasks: Task[]; selectedId: number | null; loading: boolean }>()
defineEmits<{ select: [taskId: number] }>()

const taskStatus: Record<string, string> = {
  thinking: 'Menyusun rencana',
  working: 'Berjalan',
  waiting: 'Menunggu',
  waiting_approval: 'Perlu persetujuan',
  completed: 'Selesai',
  failed: 'Gagal',
}

function shortDate(date: string) {
  return new Intl.DateTimeFormat('id-ID', { dateStyle: 'short', timeStyle: 'short' }).format(
    new Date(date),
  )
}
</script>

<template>
  <section class="panel task-console">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">RIWAYAT</p>
        <h2>Riwayat tugas</h2>
      </div>
      <span class="count-badge">{{ tasks.length }}</span>
    </div>
    <p v-if="loading && tasks.length === 0" class="muted small-copy">Memuat tugas...</p>
    <div v-else-if="tasks.length" class="task-list">
      <button
        v-for="task in tasks"
        :key="task.id"
        class="task-row"
        :class="{ 'task-row-selected': task.id === selectedId }"
        type="button"
        @click="$emit('select', task.id)"
      >
        <span class="task-mark" :class="`task-mark-${task.status}`">
          <i />
        </span>
        <span class="task-row-copy">
          <strong>{{ task.instruction }}</strong>
          <small>{{ shortDate(task.created_at) }} · {{ taskStatus[task.status] ?? task.status }}</small>
        </span>
        <span class="task-arrow" aria-hidden="true">›</span>
      </button>
    </div>
    <p v-else class="empty-state">Belum ada tugas. Kirim instruksi untuk memulai.</p>
  </section>
</template>
