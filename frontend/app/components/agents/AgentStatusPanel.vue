<script setup lang="ts">
import type { Agent, AgentStatus } from '~/types/office'

defineProps<{ agents: Agent[]; loading: boolean; selectedAgentName?: string | null }>()
defineEmits<{ select: [agentName: string] }>()

const labels: Record<AgentStatus, string> = {
  idle: 'Siap',
  thinking: 'Berpikir',
  working: 'Bekerja',
  waiting: 'Menunggu',
  waiting_approval: 'Menunggu persetujuan',
  completed: 'Selesai',
  failed: 'Gagal',
  offline: 'API belum terhubung',
}
</script>

<template>
  <section class="panel agent-panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">TIM AI</p>
        <h2>Status agent</h2>
      </div>
      <span class="live-indicator"><i /> LIVE</span>
    </div>
    <p v-if="loading" class="muted small-copy">Memuat status dari backend...</p>
    <div v-else class="agent-list">
      <button
        v-for="agent in agents"
        :key="agent.name"
        class="agent-row"
        :class="{
          'agent-row-selected': agent.name === selectedAgentName || agent.status === 'working' || agent.status === 'thinking',
        }"
        type="button"
        @click="$emit('select', agent.name)"
      >
        <div class="agent-avatar" :class="`avatar-${agent.name}`">
          {{ agent.display_name.slice(0, 1) }}
        </div>
        <div class="agent-meta">
          <strong>{{ agent.display_name }}</strong>
          <span>{{ agent.role }}</span>
        </div>
        <span class="status-pill" :class="`status-${agent.status}`">
          <i />{{ labels[agent.status] }}
        </span>
      </button>
      <p v-if="agents.length === 0" class="muted small-copy">
        Status agent belum tersedia. Pastikan backend dan database berjalan.
      </p>
    </div>
  </section>
</template>
