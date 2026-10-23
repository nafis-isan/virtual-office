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
const idleWalkTick = ref(0)
let idleWalkTimer: ReturnType<typeof setInterval> | undefined
let deliveryTimer: ReturnType<typeof setTimeout> | undefined
const stations = [
  { agentName: 'project_manager', department: 'REVIEW', x: 132, y: 126, home: [227, 260], work: [227, 260], handoff: [414, 462], meeting: [500, 207], returnStops: [[350, 207], [350, 292], [115, 292], [115, 110], [350, 110], [350, 292], [227, 260]], idleStops: [[200, 292], [200, 370], [350, 370], [350, 292], [350, 370], [200, 370], [200, 292], [350, 292]], color: '#bf854c', skin: '#efb879', hair: '#c28a4d', hairLight: '#e4b76d', shirt: '#161d27', shirtLight: '#f1ede0', trousers: '#111821', spriteRow: 1 },
  { agentName: 'researcher', department: 'RESEARCH', x: 668, y: 126, home: [773, 260], work: [773, 260], handoff: [586, 462], meeting: [500, 452], returnStops: [[646, 452], [646, 292], [890, 292], [890, 110], [646, 110], [646, 292], [773, 260]], idleStops: [[890, 292], [890, 96], [646, 96], [890, 96], [890, 292], [890, 292], [890, 96], [890, 96]], color: '#8b6938', skin: '#efb879', hair: '#9e302c', hairLight: '#d66a55', shirt: '#87702d', shirtLight: '#d1b94e', trousers: '#554528', spriteRow: 4 },
  { agentName: 'designer', department: 'DESIGN', x: 132, y: 406, home: [227, 536], work: [227, 536], handoff: [460, 474], meeting: [328, 330], returnStops: [[350, 330], [350, 570], [115, 570], [115, 370], [350, 370], [350, 570], [227, 536]], idleStops: [[355, 545], [355, 500], [500, 500], [500, 545], [620, 545], [500, 545], [500, 500], [355, 500]], color: '#4b85c3', skin: '#efb879', hair: '#c58c4a', hairLight: '#e0b66d', shirt: '#3584de', shirtLight: '#80b9fa', trousers: '#171a24', spriteRow: 2 },
  { agentName: 'programmer', department: 'CODING', x: 668, y: 406, home: [773, 536], work: [773, 536], handoff: [540, 474], meeting: [672, 330], returnStops: [[646, 330], [646, 570], [890, 570], [890, 370], [646, 370], [646, 570], [773, 536]], idleStops: [[890, 375], [890, 545], [890, 470], [890, 545], [890, 375], [890, 375], [890, 545], [890, 545]], color: '#487eaf', skin: '#efb879', hair: '#29232a', hairLight: '#514653', shirt: '#397fce', shirtLight: '#75b2fa', trousers: '#171a24', spriteRow: 3 },
]
const idleWalkStopCount = Math.max(...stations.map((station) => station.idleStops.length))
const returnRouteStopCount = Math.max(...stations.map((station) => station.returnStops.length))
const returnRouteStage = ref<number | null>(null)
let returnRouteTimer: ReturnType<typeof setInterval> | undefined
const idleChatPair = computed(() => {
  if (!officeIsIdle.value) return []
  const phase = idleWalkTick.value % 8
  if (phase === 7 || phase === 0) return [0, 2]
  if (phase === 4 || phase === 5) return [1, 3]
  return []
})

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
const teamMeeting = computed(() => taskIsActive.value && props.task?.status === 'thinking')
const officeIsIdle = computed(() =>
  !taskIsActive.value &&
  props.agents.length > 0 &&
  props.agents.every((agent) => ['idle', 'completed', 'failed'].includes(agent.status)),
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
const deliveryTaskId = ref<number | null>(null)
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

const characters = computed(() => {
  const positionedCharacters = stations.map((station, index) => {
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
    const delivering =
      deliveryTaskId.value === props.task?.id && latestStep?.status === 'completed'
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
    const idleWaypoint = station.idleStops[idleWalkTick.value % station.idleStops.length] ?? station.home
    const idleChatting = idleChatPair.value.includes(index)
    const routeStage = returnRouteStage.value
    const returning = routeStage !== null && taskIsActive.value
    const returnWaypoint =
      routeStage === null || !taskIsActive.value ? undefined : station.returnStops[routeStage]
    const position = delivering
      ? station.handoff
      : teamMeeting.value
        ? station.meeting
        : returnWaypoint
          ? returnWaypoint
        : atWorkstation
          ? station.work
          : officeIsIdle.value
            ? idleWaypoint
            : station.home
    const walking =
      (returning && taskIsActive.value) ||
      (officeIsIdle.value && !idleChatting && !delivering && status !== 'failed')

    return {
      agent,
      active,
      atWorkstation,
      delivering,
      chatting: teamMeeting.value || idleChatting,
      focused,
      meeting: teamMeeting.value,
      status,
      callout: focused
        ? (stepIsActive ? latestStep?.title : agentActivity?.message) ?? spotlightMessage.value
        : undefined,
      taskTitle: latestStep?.title,
      taskOutput: latestStep?.output,
      taskStepStatus,
      department: station.department,
      color: station.color,
      skin: station.skin,
      hair: station.hair,
      hairLight: station.hairLight,
      shirt: station.shirt,
      shirtLight: station.shirtLight,
      trousers: station.trousers,
      spriteRow: station.spriteRow,
      walking,
      returning,
      x: position[0],
      y: position[1],
    }
  })

  return positionedCharacters
})

const selectedCharacter = computed(() => characters.value[selectedIndex.value])

watch(teamMeeting, (meeting, wasMeeting) => {
  if (returnRouteTimer) clearInterval(returnRouteTimer)
  returnRouteTimer = undefined
  returnRouteStage.value = null

  if (!meeting && wasMeeting && taskIsActive.value) {
    returnRouteStage.value = 0
    returnRouteTimer = setInterval(() => {
      const nextStage = (returnRouteStage.value ?? 0) + 1
      if (nextStage >= returnRouteStopCount) {
        if (returnRouteTimer) clearInterval(returnRouteTimer)
        returnRouteTimer = undefined
        returnRouteStage.value = null
        return
      }
      returnRouteStage.value = nextStage
    }, 720)
  }
})

watch(
  () => [props.task?.id ?? null, props.task?.status ?? null] as const,
  ([taskId, status], [previousTaskId, previousStatus]) => {
    if (deliveryTimer) clearTimeout(deliveryTimer)
    if (
      taskId !== null &&
      taskId === previousTaskId &&
      status === 'completed' &&
      previousStatus !== 'completed'
    ) {
      deliveryTaskId.value = taskId
      deliveryTimer = setTimeout(() => {
        deliveryTaskId.value = null
      }, 3500)
    } else if (taskId !== deliveryTaskId.value) {
      deliveryTaskId.value = null
    }
  },
)

onMounted(() => {
  idleWalkTimer = setInterval(() => {
    idleWalkTick.value = (idleWalkTick.value + 1) % idleWalkStopCount
  }, 4200)
})

onUnmounted(() => {
  if (idleWalkTimer) clearInterval(idleWalkTimer)
  if (returnRouteTimer) clearInterval(returnRouteTimer)
  if (deliveryTimer) clearTimeout(deliveryTimer)
})

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
        aria-label="Denah interaktif kantor Virtual Office AI"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <pattern id="office-tiles" width="48" height="48" patternUnits="userSpaceOnUse">
            <rect width="48" height="48" fill="#b9b9a8" />
            <rect x="1" y="1" width="46" height="46" fill="#c5c5b3" />
            <path d="M0 0H48M0 0V48" stroke="#dedbc9" stroke-width="2" />
            <path d="M4 44H44M44 4V44" stroke="#a8a99a" stroke-width="1" opacity=".75" />
          </pattern>
        </defs>

        <rect width="1000" height="620" fill="#172329" />
        <rect x="24" y="25" width="952" height="568" fill="#26353a" />
        <rect x="34" y="34" width="932" height="552" fill="#657067" />
        <rect x="45" y="45" width="910" height="530" fill="url(#office-tiles)" />
        <path d="M45 110H955M45 565H955M45 45V575M955 45V575" fill="none" stroke="#4e5c58" stroke-width="11" />
        <path d="M51 114H949M51 559H949" fill="none" stroke="#e2d7bc" stroke-width="2" opacity=".8" />
        <path d="M45 110H955V116H45ZM45 554H955V560H45Z" fill="#778078" />

        <path d="M45 45H955V104H45Z" fill="#39484a" />
        <path d="M45 99H955V110H45Z" fill="#d09357" />
        <g v-for="x in [125, 275, 425, 575, 725, 875]" :key="`window-${x}`">
          <rect :x="x - 54" y="56" width="108" height="34" fill="#91bec0" />
          <path :d="`M${x} 56V90M${x - 54} 73H${x + 54}`" stroke="#e6b878" stroke-width="4" />
        </g>
        <rect x="431" y="53" width="138" height="8" fill="#263637" />
        <rect x="444" y="69" width="112" height="19" fill="#263637" />
        <text x="500" y="83" text-anchor="middle" fill="#c3ef6a" font-size="11" font-family="monospace" font-weight="700" letter-spacing="2">
          VIRTUAL OFFICE AI
        </text>
        <text x="500" y="121" text-anchor="middle" fill="#c9d0ba" font-size="8" font-family="monospace" letter-spacing="1.5">
          {{ task ? `TASK #${task.id} · ${task.status.toUpperCase()}` : 'RUANG KERJA · LIVE' }}
        </text>
        <g aria-label="Pintu masuk kantor">
          <rect x="454" y="96" width="92" height="23" fill="#314247" />
          <rect x="460" y="100" width="38" height="18" fill="#6f9ba0" />
          <rect x="502" y="100" width="38" height="18" fill="#6f9ba0" />
          <path d="M500 100V118" stroke="#d9bd8d" stroke-width="2" />
          <text x="500" y="94" text-anchor="middle" fill="#f1e6c9" font-size="6" font-family="monospace" letter-spacing="1">
            LOBI / MASUK
          </text>
        </g>

        <g aria-label="Panel area kantor">
          <rect x="48" y="117" width="38" height="22" fill="#32464b" />
          <rect x="52" y="120" width="30" height="16" fill="#6a9da8" />
          <path d="M55 132L61 128L66 130L77 123" fill="none" stroke="#d6dda9" stroke-width="1.5" />
          <rect x="879" y="117" width="38" height="22" fill="#32464b" />
          <rect x="883" y="120" width="30" height="16" fill="#6a9da8" />
          <path d="M886 131H909M886 127H905M886 123H900" stroke="#e5d8b6" stroke-width="1.5" />
        </g>

        <g aria-label="Karpet ruang kolaborasi">
          <rect x="310" y="224" width="380" height="222" fill="#d5a067" />
          <rect x="322" y="236" width="356" height="198" fill="#44675b" />
          <rect x="340" y="254" width="320" height="162" fill="#c98650" />
        </g>

        <g
          v-for="(station, index) in stations"
          :key="`desk-rug-${index}`"
          aria-hidden="true"
        >
          <rect :x="station.x - 18" :y="station.y - 18" width="236" height="184" fill="#76513d" />
          <rect :x="station.x - 13" :y="station.y - 13" width="226" height="174" fill="#44675b" />
          <rect :x="station.x - 8" :y="station.y - 8" width="216" height="164" fill="#bd865a" />
          <rect :x="station.x - 3" :y="station.y - 3" width="206" height="154" fill="none" stroke="#e0b77e" stroke-width="2" stroke-dasharray="2 6" />
        </g>

        <g
          v-for="(station, index) in stations"
          :key="`route-${index}`"
          class="agent-route"
          :class="{
            'agent-route-active': characters[index]?.active,
            'agent-route-delivery': characters[index]?.delivering,
            'agent-route-idle': officeIsIdle,
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
          <rect :x="station.x" :y="station.y" width="200" height="128" :fill="station.color" opacity=".14" :stroke="station.color" stroke-width="2" />
          <path :d="`M${station.x} ${station.y + 108}H${station.x + 200}`" :stroke="station.color" stroke-width="2" opacity=".5" />
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
          <rect :x="station.x + 36" :y="station.y + 72" width="58" height="4" fill="#fbefcf" opacity=".9" />
          <rect :x="station.x + 124" :y="station.y + 70" width="8" height="7" fill="#f6edda" />
          <rect :x="station.x + 135" :y="station.y + 69" width="8" height="8" fill="#6c88a0" />
          <rect :x="station.x + 147" :y="station.y + 70" width="8" height="7" fill="#c57c54" />
          <rect :x="station.x + 164" :y="station.y + 60" width="15" height="17" fill="#557b54" />
          <rect :x="station.x + 168" :y="station.y + 54" width="8" height="11" fill="#87aa64" />
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

        <g
          v-for="(station, index) in stations"
          :key="`fixed-chair-${index}`"
          class="office-desk-chair"
          :transform="`translate(${station.home[0]} ${station.home[1]})`"
          aria-hidden="true"
        >
          <rect x="-13" y="-2" width="26" height="15" fill="#27383b" />
          <rect x="-9" y="1" width="18" height="9" fill="#52665f" />
          <rect x="-17" y="12" width="34" height="6" fill="#34484a" />
          <path d="M-10 18L-13 24M10 18L13 24M0 18V24M-18 25H18" fill="none" stroke="#34484a" stroke-width="2" />
          <path d="M-18 7H-14M14 7H18" stroke="#53625b" stroke-width="2" />
        </g>

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
          {{ teamMeeting ? 'DISKUSI TIM' : taskIsActive ? 'TIM BEKERJA' : task?.status === 'completed' ? 'HASIL TUGAS' : 'KOLABORASI' }}
        </text>
        <text x="500" y="455" text-anchor="middle" fill="#f5e7c8" font-size="7" font-family="monospace" letter-spacing=".8">
          {{ teamMeeting ? 'PEMBAGIAN TUGAS' : 'RUANG KOLABORASI' }}
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
            'office-agent-chatting': character.chatting,
            'office-agent-walking': character.walking,
            'office-agent-returning': character.returning,
            'office-agent-meeting': character.meeting,
            'office-agent-focused': character.focused,
            [`office-agent-status-${character.status ?? 'offline'}`]: true,
          }"
          :transform="`translate(${character.x} ${character.y})`"
          :style="{ '--agent-accent': character.color }"
          role="button"
          tabindex="0"
          :aria-label="`${character.agent?.display_name ?? shortName(character.agent?.name, index)} — ${character.meeting ? 'berdiskusi di meja tengah' : character.chatting ? 'mengobrol sambil berjalan' : statusLabels[character.status ?? 'offline']}. Pilih untuk melihat detail.`"
          :aria-pressed="selectedIndex === index"
          @click="selectAgent(index)"
          @keydown.enter.prevent="selectAgent(index)"
          @keydown.space.prevent="selectAgent(index)"
        >
          <g class="agent-sprite">
          <ellipse cx="0" cy="31" rx="23" ry="6" fill="#182326" opacity=".35" />
          <rect class="agent-selection-ring" x="-36" y="-39" width="72" height="78" />
          <g v-if="character.delivering" class="agent-delivery-shadow">
            <rect x="-14" y="29" width="28" height="4" fill="#263638" opacity=".45" />
          </g>
          <g class="agent-body">
            <path d="M-11 9H-2V24H-15V20H-18V17H-11ZM11 9H2V24H15V20H18V17H11Z" :fill="character.trousers" />
            <rect x="-16" y="23" width="12" height="4" fill="#171a20" />
            <rect x="4" y="23" width="12" height="4" fill="#171a20" />
            <rect x="-15" y="-9" width="30" height="23" :fill="character.shirt" />
            <path d="M-13 -7H13V13H-13Z" :fill="character.shirt" />
            <path v-if="character.spriteRow === 1" d="M-11 -8H-4L0 -4L4 -8H11V13H5V-1H-5V13H-11Z" fill="#f1ede0" />
            <path v-if="character.spriteRow === 1" d="M0 -3L3 0L2 7L0 10L-2 7L-3 0Z" fill="#b7463c" />
            <path v-if="character.spriteRow === 4" d="M-13 -5H13M-13 1H13M-13 7H13" stroke="#d2b94e" stroke-width="2" />
            <path v-if="character.spriteRow === 2" d="M-13 -7H13V-3H-13Z" fill="#2872c6" />
            <path v-if="character.spriteRow === 3" d="M-13 7H13V13H-13Z" fill="#3675bd" />
            <g class="agent-arms">
              <path d="M-13 -6H-19V2H-16V8H-10V4H-14V-1H-10ZM13 -6H19V2H16V8H10V4H14V-1H10Z" :fill="character.shirt" />
              <path d="M-16 8H-10V11H-15ZM16 8H10V11H15Z" :fill="character.skin" />
            </g>
            <rect x="-7" y="-12" width="14" height="6" :fill="character.skin" />
            <rect x="-11" y="-31" width="22" height="20" :fill="character.skin" />
            <rect x="-14" y="-26" width="4" height="8" :fill="character.skin" />
            <rect x="10" y="-26" width="4" height="8" :fill="character.skin" />
            <rect x="-8" y="-22" width="3" height="3" fill="#292e31" />
            <rect x="5" y="-22" width="3" height="3" fill="#292e31" />
            <path d="M-4 -15H4" stroke="#9f5947" stroke-width="2" />
            <g v-if="character.spriteRow === 1">
              <path d="M-12 -25V-31H-8V-36H5V-33H12V-27H7V-30H-4V-27H-10V-23H-13Z" :fill="character.hair" />
              <path d="M-7 -34H4M-11 -29V-26" :stroke="character.hairLight" stroke-width="2" />
            </g>
            <g v-else-if="character.spriteRow === 2">
              <path d="M-13 -25V-33H-7V-36H5V-32H12V-25H8V-28H-7V-24Z" :fill="character.hair" />
              <path d="M-6 -34H3M-11 -30V-27" :stroke="character.hairLight" stroke-width="2" />
            </g>
            <g v-else-if="character.spriteRow === 3">
              <path d="M-13 -24V-32L-8 -30L-7 -36L-1 -32L3 -37L7 -31L13 -33V-25H8V-28H-7V-24Z" :fill="character.hair" />
              <path d="M-5 -34L-3 -32M5 -33L7 -31" :stroke="character.hairLight" stroke-width="2" />
            </g>
            <g v-else>
              <path d="M-13 -25V-32H-7V-36H3V-33H10V-29H14V-24H7V-28H-5V-25L-10 -21Z" :fill="character.hair" />
              <path d="M-6 -34H2M-10 -29V-26" :stroke="character.hairLight" stroke-width="2" />
            </g>
            <rect class="agent-status-marker" x="21" y="-34" width="9" height="9" :fill="statusColor(character.status)" stroke="#f3efe6" stroke-width="2" />
          </g>
          <g class="agent-nameplate">
            <rect x="-49" y="-59" width="98" height="17" fill="#172630" stroke="#435b61" stroke-width="1" />
            <rect x="-49" y="-59" width="4" height="17" :fill="character.color" />
            <text x="0" y="-47" text-anchor="middle" fill="#fbf9f3" font-size="9" font-family="monospace" font-weight="600">
              {{ character.agent?.display_name ?? shortName(character.agent?.name, index) }}
            </text>
          </g>
          </g>
          <g v-if="character.chatting" class="agent-chat-bubble" aria-hidden="true">
            <rect x="-24" y="-83" width="48" height="21" fill="#f7f0dc" stroke="#263638" stroke-width="2" />
            <path d="M-4 -62L1 -56L5 -62Z" fill="#f7f0dc" stroke="#263638" stroke-width="1.5" />
            <text x="0" y="-69" text-anchor="middle" fill="#355748" font-size="8" font-family="monospace" font-weight="700" letter-spacing="1">
              .....
            </text>
          </g>
          <g v-if="taskIsActive && !teamMeeting && character.focused && character.callout" class="agent-callout" :class="{ 'agent-callout-active': taskIsActive }">
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
          VIRTUAL OFFICE AI · VISUAL WORKSPACE
        </text>
      </svg>
      <div class="scene-legend" aria-label="Keterangan status agent">
        <span><i class="legend-active" /> Aktif</span>
        <span><i class="legend-idle" /> Siap</span>
        <span><i class="legend-waiting" /> Menunggu</span>
        <span><i class="legend-alert" /> Gagal</span>
        <span><i class="legend-table" /> Hasil</span>
        <span><i class="legend-chat" /> Mengobrol</span>
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
