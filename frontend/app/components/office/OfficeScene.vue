<script setup lang="ts">
import type { Activity, Agent, AgentStatus, TaskDetail } from '~/types/office'

const props = defineProps<{
  agents: Agent[]
  task: TaskDetail | null
  activities: Activity[]
  selectedAgentName?: string | null
}>()
const emit = defineEmits<{ selectAgent: [agentName: string] }>()

const selectedIndex = ref(0)
const stations = [
  { agentName: 'project_manager', department: 'REVIEW', x: 132, y: 126, home: [227, 260], work: [227, 244], handoff: [414, 462], color: '#54765d' },
  { agentName: 'researcher', department: 'RESEARCH', x: 668, y: 126, home: [773, 260], work: [773, 244], handoff: [586, 462], color: '#657d8a' },
  { agentName: 'designer', department: 'DESIGN', x: 132, y: 406, home: [227, 536], work: [227, 514], handoff: [460, 474], color: '#b66b4d' },
  { agentName: 'programmer', department: 'CODING', x: 668, y: 406, home: [773, 536], work: [773, 514], handoff: [540, 474], color: '#8c7953' },
]

const statusLabels: Record<AgentStatus, string> = {
  idle: 'Siap di meja',
  thinking: 'Menyusun rencana',
  working: 'Sedang bekerja',
  waiting: 'Menunggu proses',
  waiting_approval: 'Menunggu persetujuan',
  completed: 'Selesai',
  failed: 'Perlu perhatian',
  offline: 'Tidak terhubung',
}

const taskIsActive = computed(() =>
  ['thinking', 'working', 'waiting', 'waiting_approval'].includes(props.task?.status ?? ''),
)
const activeStep = computed(() =>
  [...(props.task?.steps ?? [])].reverse().find((step) =>
    ['working', 'thinking', 'waiting', 'waiting_approval'].includes(step.status),
  ),
)
const activeActivity = computed(() =>
  [...props.activities].reverse().find((activity) =>
    ['thinking', 'working', 'waiting', 'waiting_approval'].includes(activity.status),
  ),
)
const latestActivity = computed(() => props.activities.at(-1))
const handoffs = computed(() => {
  const transitions = props.activities.flatMap((activity, index) => {
    if (activity.status !== 'completed') return []
    const receiver = props.activities.slice(index + 1).find((nextActivity) =>
      ['thinking', 'working'].includes(nextActivity.status),
    )
    if (!receiver || receiver.agent_name === activity.agent_name) return []
    return [{
      id: `${activity.id}-${receiver.id}`,
      sender: activity.agent_name,
      receiver: receiver.agent_name,
      message: receiver.message,
    }]
  })
  return transitions.slice(-3).reverse()
})
const spotlightAgentName = computed(() => {
  if (taskIsActive.value) {
    return activeStep.value?.agent_name ?? activeActivity.value?.agent_name ?? 'project_manager'
  }
  return latestActivity.value?.agent_name
})
const spotlightMessage = computed(() => {
  if (taskIsActive.value) {
    return activeStep.value?.title ?? activeActivity.value?.message ?? 'Menyusun rencana kerja.'
  }
  return latestActivity.value?.message
})

const characters = computed(() =>
  stations.map((station, index) => {
    const agent = props.agents.find((item) => item.name === station.agentName) ?? props.agents[index]
    const agentSteps = props.task?.steps.filter((step) => step.agent_name === agent?.name) ?? []
    const latestStep = agentSteps.at(-1)
    const agentActivity = [...props.activities].reverse().find((activity) => activity.agent_name === agent?.name)
    const focused = !!agent && agent.name === spotlightAgentName.value
    const stepIsActive = !!latestStep && ['thinking', 'working'].includes(latestStep.status)
    const activityIsActive =
      taskIsActive.value &&
      agentActivity?.agent_name === agent?.name &&
      ['thinking', 'working', 'waiting', 'waiting_approval'].includes(agentActivity?.status ?? '')
    const active = taskIsActive.value ? stepIsActive || activityIsActive : false
    const atWorkstation =
      active ||
      (taskIsActive.value &&
        !!latestStep &&
        ['waiting', 'waiting_approval'].includes(latestStep.status) &&
        activeStep.value?.agent_name === agent?.name)
    const delivering = props.task?.status === 'completed' && latestStep?.status === 'completed'
    const taskStepStatus = latestStep?.status
    const status: AgentStatus | undefined = latestStep
      ? stepAgentStatus(taskStepStatus ?? '')
      : props.task
        ? taskIsActive.value && activityIsActive
          ? stepAgentStatus(agentActivity?.status ?? '')
          : props.task.status === 'failed' && focused
            ? 'failed'
            : 'idle'
        : agent?.status
    const position = delivering ? station.handoff : atWorkstation ? station.work : station.home

    return {
      agent,
      active,
      atWorkstation,
      delivering,
      focused,
      status,
      callout: focused
        ? (stepIsActive ? latestStep?.title : agentActivity?.message) ?? spotlightMessage.value
        : undefined,
      taskTitle: latestStep?.title,
      taskOutput: latestStep?.output,
      taskStepStatus,
      department: station.department,
      color: station.color,
      x: position[0],
      y: position[1],
    }
  }),
)

const selectedCharacter = computed(() => characters.value[selectedIndex.value])

watch(
  () => props.selectedAgentName,
  (name) => {
    if (!name) return
    const index = characters.value.findIndex((character) => character.agent?.name === name)
    if (index >= 0) selectedIndex.value = index
  },
)

function compactMessage(message: string | undefined) {
  if (!message) return ''
  return message.length > 42 ? `${message.slice(0, 39).trimEnd()}...` : message
}

function statusColor(status: AgentStatus | undefined) {
  if (status === 'working' || status === 'thinking') return '#b9f064'
  if (status === 'waiting' || status === 'waiting_approval') return '#e5bd72'
  if (status === 'failed') return '#d86f5a'
  if (status === 'completed') return '#91a29a'
  return '#52666d'
}

function stepStatusLabel(status: string) {
  if (status === 'pending') return 'menunggu'
  return status.replaceAll('_', ' ')
}

function stepAgentStatus(status: string): AgentStatus {
  switch (status) {
    case 'pending':
    case 'waiting':
      return 'waiting'
    case 'thinking':
    case 'working':
    case 'waiting_approval':
    case 'completed':
    case 'failed':
      return status
    default:
      return 'offline'
  }
}

function shortName(name: string | undefined, index: number) {
  return name?.replace(/_/g, ' ') ?? `Agent ${index + 1}`
}

function selectAgent(index: number) {
  selectedIndex.value = index
  const agentName = characters.value[index]?.agent?.name
  if (agentName) emit('selectAgent', agentName)
}
</script>

<template>
  <div class="office-experience">
    <div class="scene-frame">
      <svg
        class="office-map"
        viewBox="0 0 1000 620"
        role="group"
        aria-label="Denah interaktif kantor NF Office AI"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <pattern id="wood-floor" width="120" height="32" patternUnits="userSpaceOnUse">
            <rect width="120" height="32" fill="#b96e43" />
            <rect width="120" height="15" fill="#c57a4a" />
            <path d="M0 16H120M0 31H120M42 0V15M94 16V31" stroke="#a9623d" stroke-width="2" opacity=".7" />
            <path d="M5 5H31M51 21H80M101 5H116" stroke="#db9860" stroke-width="2" opacity=".7" />
          </pattern>
        </defs>

        <rect width="1000" height="620" fill="#202d30" />
        <rect x="34" y="34" width="932" height="552" fill="#7d4937" />
        <rect x="45" y="45" width="910" height="530" fill="url(#wood-floor)" />

        <path d="M45 45H955V104H45Z" fill="#39484a" />
        <path d="M45 99H955V110H45Z" fill="#d09357" />
        <g v-for="x in [125, 275, 425, 575, 725, 875]" :key="`window-${x}`">
          <rect :x="x - 54" y="56" width="108" height="34" fill="#91bec0" />
          <path :d="`M${x} 56V90M${x - 54} 73H${x + 54}`" stroke="#e6b878" stroke-width="4" />
        </g>
        <rect x="431" y="53" width="138" height="8" fill="#263637" />
        <rect x="444" y="69" width="112" height="19" fill="#263637" />
        <text x="500" y="83" text-anchor="middle" fill="#c3ef6a" font-size="11" font-family="monospace" font-weight="700" letter-spacing="2">
          NF OFFICE
        </text>
        <text x="500" y="121" text-anchor="middle" fill="#c9d0ba" font-size="8" font-family="monospace" letter-spacing="1.5">
          {{ task ? `TASK #${task.id} · ${task.status.toUpperCase()}` : 'RUANG KERJA · LIVE' }}
        </text>

        <g
          v-for="(station, index) in stations"
          :key="`route-${index}`"
          class="agent-route"
          :class="{
            'agent-route-active': characters[index]?.active,
            'agent-route-delivery': characters[index]?.delivering,
          }"
        >
          <path
            :d="`M${station.home[0]} ${station.home[1]} Q500 310 ${characters[index]?.x} ${characters[index]?.y}`"
            fill="none"
            stroke="#f0d29b"
            stroke-width="3"
            stroke-dasharray="4 10"
          />
        </g>

        <g
          v-for="(station, index) in stations"
          :key="`desk-${index}`"
          class="department-zone"
          :class="{ 'department-zone-selected': selectedIndex === index }"
          role="button"
          tabindex="0"
          :aria-label="`${station.department}: ${characters[index]?.agent?.display_name ?? station.agentName.replaceAll('_', ' ')}. Klik untuk melihat aktivitas.`"
          @click="selectAgent(index)"
          @keydown.enter.prevent="selectAgent(index)"
          @keydown.space.prevent="selectAgent(index)"
        >
          <rect :x="station.x - 8" :y="station.y - 8" width="216" height="142" fill="#76513d" opacity=".5" />
          <rect :x="station.x" :y="station.y" width="200" height="104" fill="#d99456" />
          <rect :x="station.x + 8" :y="station.y + 8" width="184" height="88" fill="#e2ae73" />
          <rect :x="station.x + 16" :y="station.y + 16" width="98" height="60" fill="#263638" />
          <rect :x="station.x + 22" :y="station.y + 22" width="86" height="47" :fill="station.color" />
          <path
            :d="`M${station.x + 31} ${station.y + 33}H${station.x + 96}M${station.x + 31} ${station.y + 42}H${station.x + 82}M${station.x + 31} ${station.y + 51}H${station.x + 96}`"
            stroke="#f3e5bd"
            stroke-width="3"
            opacity=".8"
          />
          <rect :x="station.x + 55" :y="station.y + 76" width="18" height="8" fill="#76513d" />
          <rect :x="station.x + 44" :y="station.y + 84" width="40" height="5" fill="#76513d" />
          <rect :x="station.x + 130" :y="station.y + 19" width="34" height="7" fill="#f0d29c" />
          <rect :x="station.x + 130" :y="station.y + 33" width="47" height="6" fill="#af7047" />
          <rect :x="station.x + 141" :y="station.y + 54" width="28" height="24" fill="#4f7452" />
          <rect :x="station.x + 147" :y="station.y + 46" width="15" height="14" fill="#78a75d" />
          <rect :x="station.x + 124" :y="station.y + 82" width="68" height="14" fill="#835839" />
          <text :x="station.x + 158" :y="station.y + 92" text-anchor="middle" fill="#f4e5c5" font-size="6" font-family="monospace" letter-spacing=".3">
            {{ station.department }}
          </text>
          <path :d="`M${station.x + 14} ${station.y + 103}V${station.y + 133}M${station.x + 186} ${station.y + 103}V${station.y + 133}`" stroke="#704633" stroke-width="8" />
          <path :d="`M${station.x + 12} ${station.y + 101}H${station.x + 188}`" stroke="#895638" stroke-width="7" />
        </g>

        <rect x="310" y="224" width="380" height="222" fill="#d5a067" />
        <rect x="322" y="236" width="356" height="198" fill="#44675b" />
        <rect x="340" y="254" width="320" height="162" fill="#c98650" />
        <ellipse cx="500" cy="342" rx="112" ry="59" fill="#78513c" opacity=".55" />
        <ellipse cx="500" cy="330" rx="112" ry="59" fill="#e0a45e" />
        <ellipse cx="500" cy="323" rx="98" ry="46" fill="#e8b77b" />
        <rect x="486" y="311" width="28" height="26" fill="#fff0cf" />
        <rect x="478" y="319" width="44" height="10" fill="#fff0cf" />
        <rect x="491" y="315" width="5" height="4" fill="#344449" />
        <rect x="504" y="315" width="5" height="4" fill="#344449" />
        <rect x="493" y="329" width="14" height="3" fill="#a8694c" />
        <g v-for="(seat, index) in [[500, 245], [500, 409], [378, 327], [622, 327]]" :key="`seat-${index}`">
          <rect :x="seat[0] - 18" :y="seat[1] - 8" width="36" height="16" fill="#26383b" />
          <rect :x="seat[0] - 12" :y="seat[1] - 4" width="24" height="4" fill="#b9f064" />
        </g>
        <rect x="423" y="424" width="154" height="14" fill="#26383b" />
        <text x="500" y="434" text-anchor="middle" fill="#f1d39b" font-size="7" font-family="monospace" letter-spacing="1.1">
          {{ task?.status === 'completed' ? 'HASIL TUGAS' : 'KOLABORASI' }}
        </text>
        <text x="500" y="455" text-anchor="middle" fill="#f5e7c8" font-size="7" font-family="monospace" letter-spacing=".8">
          RUANG KOLABORASI
        </text>

        <g aria-label="Papan status tugas">
          <rect x="814" y="278" width="122" height="92" fill="#76513d" />
          <rect x="820" y="272" width="110" height="88" fill="#dfc28e" />
          <rect x="826" y="278" width="98" height="15" fill="#394847" />
          <text x="875" y="289" text-anchor="middle" fill="#f5e7c8" font-size="7" font-family="monospace" letter-spacing=".7">
            PAPAN TUGAS
          </text>
          <text x="832" y="307" fill="#4b5146" font-size="6" font-family="monospace">
            LANGKAH {{ task?.steps.length ?? 0 }}
          </text>
          <text x="832" y="319" fill="#4b5146" font-size="6" font-family="monospace">
            SELESAI {{ task?.steps.filter((step) => step.status === 'completed').length ?? 0 }}
          </text>
          <g v-for="row in 3" :key="`board-line-${row}`">
            <rect
              x="832"
              :y="327 + row * 8"
              width="8"
              height="5"
              :fill="row <= (task?.steps.filter((step) => step.status === 'completed').length ?? 0) ? '#54765d' : '#a89a7d'"
            />
            <rect x="845" :y="327 + row * 8" :width="row === 1 ? 59 : 46" height="5" fill="#b5a47e" />
          </g>
        </g>

        <g aria-label="Jam dinding pixel art">
          <rect x="891" y="190" width="34" height="34" fill="#76513d" />
          <rect x="895" y="194" width="26" height="26" fill="#f0d9a8" />
          <path d="M908 198V207L915 211" fill="none" stroke="#394847" stroke-width="2" />
          <rect x="906" y="196" width="4" height="4" fill="#b66b4d" />
        </g>

        <g class="archive-corner" aria-label="Pustaka dokumen RAG">
          <rect x="58" y="274" width="116" height="78" fill="#76513d" />
          <rect x="64" y="266" width="104" height="78" fill="#d7a365" />
          <rect x="70" y="272" width="92" height="10" fill="#344344" />
          <text x="116" y="280" text-anchor="middle" fill="#f5e7c8" font-size="6" font-family="monospace" letter-spacing=".5">
            RAG ARCHIVE
          </text>
          <rect x="72" y="288" width="88" height="48" fill="#684c39" />
          <path d="M72 305H160M72 321H160" stroke="#d0a574" stroke-width="3" />
          <rect x="78" y="291" width="9" height="12" fill="#b66b4d" />
          <rect x="89" y="290" width="11" height="13" fill="#d4c390" />
          <rect x="102" y="292" width="9" height="11" fill="#6d8b6b" />
          <rect x="114" y="289" width="12" height="14" fill="#7d8e9a" />
          <rect x="130" y="291" width="10" height="12" fill="#c78d54" />
          <rect x="144" y="290" width="10" height="13" fill="#a68b61" />
          <rect x="78" y="307" width="12" height="12" fill="#79916a" />
          <rect x="94" y="307" width="9" height="12" fill="#bd7950" />
          <rect x="106" y="307" width="13" height="12" fill="#d4c390" />
          <rect x="123" y="307" width="10" height="12" fill="#798b9a" />
          <rect x="139" y="307" width="15" height="12" fill="#b66b4d" />
          <rect x="78" y="323" width="11" height="10" fill="#c78d54" />
          <rect x="95" y="323" width="12" height="10" fill="#738c71" />
          <rect x="113" y="323" width="10" height="10" fill="#b66b4d" />
          <rect x="130" y="323" width="10" height="10" fill="#d4c390" />
          <rect x="146" y="323" width="8" height="10" fill="#7d8e9a" />
          <path d="M72 344V357M156 344V357M68 357H160" stroke="#594332" stroke-width="5" />
        </g>

        <g v-for="(plant, index) in [[72, 151], [928, 151], [72, 500], [928, 500]]" :key="`plant-${index}`">
          <rect :x="plant[0] - 16" :y="plant[1] + 5" width="32" height="24" fill="#cc8750" />
          <rect :x="plant[0] - 11" :y="plant[1] - 16" width="9" height="24" fill="#578653" />
          <rect :x="plant[0] + 3" :y="plant[1] - 27" width="10" height="34" fill="#74a35b" />
          <rect :x="plant[0] - 24" :y="plant[1] - 17" width="17" height="11" fill="#77a85e" />
          <rect :x="plant[0] + 10" :y="plant[1] - 12" width="18" height="12" fill="#4d8054" />
          <rect :x="plant[0] - 7" :y="plant[1] - 34" width="18" height="13" fill="#86b362" />
        </g>

        <g
          v-for="(character, index) in characters"
          :key="character.agent?.name ?? `agent-${index}`"
          class="office-agent"
          :class="{
            'office-agent-selected': selectedIndex === index,
            'office-agent-active': character.active,
            'office-agent-delivering': character.delivering,
            'office-agent-focused': character.focused,
            [`office-agent-status-${character.status ?? 'offline'}`]: true,
          }"
          :transform="`translate(${character.x} ${character.y})`"
          role="button"
          tabindex="0"
          :aria-label="`${character.agent?.display_name ?? shortName(character.agent?.name, index)} — ${statusLabels[character.status ?? 'offline']}. Pilih untuk melihat detail.`"
          :aria-pressed="selectedIndex === index"
          @click="selectAgent(index)"
          @keydown.enter.prevent="selectAgent(index)"
          @keydown.space.prevent="selectAgent(index)"
        >
          <g class="agent-sprite">
          <rect class="agent-selection-ring" x="-34" y="-37" width="68" height="77" />
          <rect x="-16" y="31" width="32" height="5" fill="#263638" opacity=".28" />
          <rect x="-13" y="20" width="9" height="13" fill="#34474a" />
          <rect x="4" y="20" width="9" height="13" fill="#34474a" />
          <rect x="-17" y="2" width="34" height="20" fill="#263638" />
          <rect x="-15" y="1" width="30" height="18" :fill="character.color" />
          <rect x="-21" y="5" width="6" height="12" :fill="character.color" />
          <rect x="15" y="5" width="6" height="12" :fill="character.color" />
          <rect x="-12" y="-4" width="24" height="7" fill="#263638" />
          <rect x="-13" y="-19" width="26" height="17" fill="#e7c39d" />
          <rect x="-17" y="-16" width="4" height="10" fill="#e7c39d" />
          <rect x="13" y="-16" width="4" height="10" fill="#e7c39d" />
          <rect x="-15" y="-25" width="30" height="8" fill="#403d39" />
          <rect x="-11" y="-30" width="22" height="5" fill="#403d39" />
          <rect x="-10" y="-15" width="4" height="4" fill="#263638" />
          <rect x="6" y="-15" width="4" height="4" fill="#263638" />
          <rect x="-3" y="-5" width="6" height="3" fill="#aa6652" />
          <rect x="-12" y="6" width="24" height="3" fill="#ffffff" opacity=".32" />
          <rect class="agent-status-marker" x="22" y="-28" width="10" height="10" :fill="statusColor(character.status)" stroke="#f3efe6" stroke-width="2" />
          <g v-if="index === 0">
            <rect x="-15" y="-20" width="4" height="10" fill="#d2b783" />
            <rect x="-19" y="-18" width="4" height="6" fill="#d2b783" />
          </g>
          <g v-else-if="index === 1">
            <rect x="-11" y="-16" width="8" height="6" fill="none" stroke="#5e6c63" stroke-width="2" />
            <rect x="3" y="-16" width="8" height="6" fill="none" stroke="#5e6c63" stroke-width="2" />
          </g>
          <g v-else-if="index === 2">
            <rect x="-16" y="-26" width="32" height="6" fill="#81584a" />
            <rect x="-19" y="-21" width="5" height="13" fill="#81584a" />
          </g>
          <g v-else>
            <rect x="-17" y="-15" width="5" height="8" fill="#d2b783" />
            <rect x="12" y="-15" width="5" height="8" fill="#d2b783" />
            <rect x="-17" y="-20" width="5" height="5" fill="#d2b783" />
            <rect x="12" y="-20" width="5" height="5" fill="#d2b783" />
          </g>
          <g class="agent-nameplate">
            <rect x="-49" y="-57" width="98" height="17" fill="#263638" />
            <text x="0" y="-45" text-anchor="middle" fill="#fbf9f3" font-size="9" font-family="monospace" font-weight="600">
              {{ character.agent?.display_name ?? shortName(character.agent?.name, index) }}
            </text>
          </g>
          </g>
          <g v-if="character.focused && character.callout" class="agent-callout" :class="{ 'agent-callout-active': taskIsActive }">
            <path d="M-3 -40L4 -40L0 -34Z" fill="#263638" />
            <rect x="-82" y="-78" width="164" height="38" fill="#263638" />
            <rect x="-78" y="-74" width="156" height="30" fill="#fbf3df" />
            <rect x="-78" y="-74" width="4" height="30" :fill="character.color" />
            <text x="0" y="-61" text-anchor="middle" fill="#355748" font-size="6" font-family="monospace" font-weight="700" letter-spacing=".8">
              {{ taskIsActive ? 'AKSI SEKARANG' : 'INFO TERBARU' }}
            </text>
            <text x="0" y="-50" text-anchor="middle" fill="#3d4038" font-size="7" font-family="monospace">
              {{ compactMessage(character.callout) }}
            </text>
          </g>
        </g>

        <rect x="40" y="568" width="920" height="12" fill="#394847" />
        <rect x="450" y="566" width="100" height="14" fill="#b9f064" />
        <text x="500" y="557" text-anchor="middle" fill="#f5e7c8" font-size="10" font-family="monospace" letter-spacing="2">
          NF OFFICE · VISUAL WORKSPACE
        </text>
      </svg>
      <div class="scene-legend" aria-label="Keterangan status agent">
        <span><i class="legend-active" /> Aktif</span>
        <span><i class="legend-idle" /> Siap</span>
        <span><i class="legend-waiting" /> Menunggu</span>
        <span><i class="legend-alert" /> Gagal</span>
        <span><i class="legend-table" /> Hasil</span>
      </div>
    </div>
    <div v-if="selectedCharacter" class="scene-inspector" aria-live="polite">
      <span class="inspector-avatar" :style="{ '--agent-color': selectedCharacter.color }">
        {{ selectedCharacter.agent?.display_name.slice(0, 1) ?? 'A' }}
      </span>
      <span class="inspector-copy">
        <strong>{{ selectedCharacter.agent?.display_name ?? shortName(selectedCharacter.agent?.name, selectedIndex) }}</strong>
        <small>{{ selectedCharacter.department }} · {{ selectedCharacter.agent?.role ?? 'Menunggu status agent dari backend' }}</small>
        <small v-if="selectedCharacter.taskTitle" class="inspector-task">{{ selectedCharacter.taskTitle }}</small>
        <small v-if="selectedCharacter.taskOutput" class="inspector-result">Hasil: {{ compactMessage(selectedCharacter.taskOutput) }}</small>
      </span>
      <span class="inspector-status">
        <i :style="{ '--status-color': statusColor(selectedCharacter.status) }" />
        {{ statusLabels[selectedCharacter.status ?? 'offline'] }}
      </span>
      <span class="inspector-hint">
        {{ selectedCharacter.delivering
          ? 'Mengirim hasil ke meja utama'
          : (selectedCharacter.status === 'waiting' || selectedCharacter.status === 'waiting_approval') && selectedCharacter.atWorkstation
            ? 'Menunggu di ruang kerja'
            : selectedCharacter.status === 'waiting'
              ? 'Menunggu giliran'
            : selectedCharacter.active
              ? 'Bekerja di mejanya'
              : 'Pilih agent atau ruang' }}
      </span>
    </div>
    <section v-if="task" class="office-task-flow" aria-label="Urutan langkah tugas">
      <div class="office-task-flow-heading">
        <strong>ALUR TUGAS</strong>
        <span>{{ task.steps.filter((step) => step.status === 'completed').length }}/{{ task.steps.length }} langkah selesai</span>
      </div>
      <ol v-if="task.steps.length" class="office-task-steps">
        <li v-for="step in task.steps" :key="step.id" :class="`office-step-${step.status}`">
          <span class="office-step-marker" :aria-label="step.status.replaceAll('_', ' ')">
            {{ step.status === 'completed' ? '✓' : step.status === 'failed' ? '!' : step.position }}
          </span>
          <span class="office-step-copy">
            <strong>{{ step.title }}</strong>
            <small>{{ shortName(step.agent_name, 0) }} · {{ stepStatusLabel(step.status) }}</small>
          </span>
        </li>
      </ol>
      <p v-else class="office-flow-empty">Langkah agent akan muncul saat tugas dimulai.</p>
      <div v-if="handoffs.length" class="office-handoffs" aria-label="Serah-terima agent yang tercatat">
        <strong>SERAH-TERIMA TERCATAT</strong>
        <p v-for="handoff in handoffs" :key="handoff.id">
          {{ shortName(handoff.sender, 0) }} → {{ shortName(handoff.receiver, 0) }} · {{ compactMessage(handoff.message) }}
        </p>
      </div>
    </section>
  </div>
</template>
