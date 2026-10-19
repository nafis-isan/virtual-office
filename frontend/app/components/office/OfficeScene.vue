<script setup lang="ts">
import type { Agent, AgentStatus } from '~/types/office'

type Position = [number, number, number]

const props = defineProps<{ agents: Agent[] }>()

const desks = [
  { x: -4.05, z: -2.72, color: '#49b98a' },
  { x: 4.05, z: -2.72, color: '#ba83e8' },
  { x: -4.05, z: 2.76, color: '#f3a35d' },
  { x: 4.05, z: 2.76, color: '#62b6df' },
]
const homes: Position[] = [
  [-4.05, 0, -1.58],
  [4.05, 0, -1.58],
  [-4.05, 0, 1.55],
  [4.05, 0, 1.55],
]
const meetingPoints: Position[] = [
  [-1.26, 0, -0.84],
  [1.26, 0, -0.84],
  [-1.26, 0, 0.84],
  [1.26, 0, 0.84],
]
const floorboards = Array.from({ length: 24 }, (_, index) => ({
  z: -4.14 + index * 0.36,
  color: index % 2 === 0 ? '#b96e43' : '#c57a4a',
}))
const windows = [-3.75, -1.25, 1.25, 3.75]
const plants = [
  { x: -5.55, z: -3.15 },
  { x: 5.55, z: -3.15 },
  { x: -5.55, z: 3.2 },
  { x: 5.55, z: 3.2 },
]

const actorPositions = ref<Position[]>(homes.map((position) => [...position] as Position))
const actorRotations = ref<number[]>(homes.map(([x, , z]) => Math.atan2(-x, -z)))
const gaitCycles = ref<number[]>([0, 0, 0, 0])

const characters = computed(() =>
  desks.map((desk, index) => ({
    ...desk,
    agent: props.agents[index],
    position: actorPositions.value[index] ?? homes[index],
    rotation: actorRotations.value[index] ?? 0,
    gait: gaitCycles.value[index] ?? 0,
  })),
)

function statusColor(status: AgentStatus | undefined) {
  if (status === 'working' || status === 'thinking') return '#b9f064'
  if (status === 'waiting' || status === 'waiting_approval') return '#ffc463'
  if (status === 'failed') return '#f47171'
  if (status === 'completed') return '#91a29b'
  return '#52666d'
}

function animateAgents({ delta, elapsed }: { delta: number; elapsed: number }) {
  const nextPositions = actorPositions.value.map((position) => [...position] as Position)
  const nextRotations = [...actorRotations.value]
  const nextGaits = [...gaitCycles.value]

  characters.value.forEach((character, index) => {
    const status = character.agent?.status
    const active =
      status === 'thinking' ||
      status === 'working' ||
      status === 'waiting' ||
      status === 'waiting_approval'
    const target = active ? meetingPoints[index] : homes[index]
    const current = actorPositions.value[index]
    const currentRotation = actorRotations.value[index]
    if (!target || !current || currentRotation === undefined) return

    const dx = target[0] - current[0]
    const dz = target[2] - current[2]
    const moving = Math.hypot(dx, dz) > 0.035
    const easing = Math.min(1, delta * 1.8)

    nextPositions[index] = [
      current[0] + dx * easing,
      moving ? Math.abs(Math.sin(elapsed * 9 + index)) * 0.075 : 0,
      current[2] + dz * easing,
    ]
    nextGaits[index] = moving ? Math.sin(elapsed * 9 + index) * 0.48 : 0

    const direction = moving ? Math.atan2(dx, dz) : Math.atan2(-current[0], -current[2])
    const rotationDelta = Math.atan2(
      Math.sin(direction - currentRotation),
      Math.cos(direction - currentRotation),
    )
    nextRotations[index] = currentRotation + rotationDelta * easing
  })

  actorPositions.value = nextPositions
  actorRotations.value = nextRotations
  gaitCycles.value = nextGaits
}
</script>

<template>
  <div class="scene-frame">
    <div class="scene-legend" aria-hidden="true">
      <span><i class="legend-active" /> Agent aktif</span>
      <span><i class="legend-meeting" /> Meja kolaborasi</span>
    </div>
    <ClientOnly>
      <TresCanvas
        clear-color="#202d30"
        :shadows="true"
        :dpr="[0.8, 1]"
        :antialias="false"
        @loop="animateAgents"
      >
        <TresPerspectiveCamera
          :position="[0, 14.5, 16.2]"
          :rotation="[-0.72, 0, 0]"
          :fov="40"
          :near="0.1"
          :far="100"
        />
        <TresAmbientLight :intensity="1.65" />
        <TresDirectionalLight :position="[-5, 12, 7]" :intensity="2.55" cast-shadow />
        <TresDirectionalLight :position="[6, 8, -3]" :intensity="0.65" color="#ffc783" />

        <TresMesh :position="[0, -0.35, 0]" receive-shadow>
          <TresBoxGeometry :args="[12.8, 0.58, 9]" />
          <TresMeshStandardMaterial color="#7d4937" roughness="1" flat-shading />
        </TresMesh>
        <TresMesh :position="[0, -0.035, 0]" receive-shadow>
          <TresBoxGeometry :args="[12.45, 0.09, 8.65]" />
          <TresMeshStandardMaterial color="#bb7547" roughness="1" flat-shading />
        </TresMesh>
        <TresMesh v-for="(plank, index) in floorboards" :key="`plank-${index}`" :position="[0, 0.014, plank.z]" receive-shadow>
          <TresBoxGeometry :args="[12.38, 0.025, 0.325]" />
          <TresMeshStandardMaterial :color="plank.color" roughness="1" flat-shading />
        </TresMesh>
        <TresMesh :position="[0, 0.037, 0]" receive-shadow>
          <TresBoxGeometry :args="[4.5, 0.018, 3.4]" />
          <TresMeshStandardMaterial color="#d5a067" roughness="1" flat-shading />
        </TresMesh>
        <TresMesh :position="[0, 0.05, 0]" receive-shadow>
          <TresBoxGeometry :args="[4.14, 0.014, 3.04]" />
          <TresMeshStandardMaterial color="#44675b" roughness="1" flat-shading />
        </TresMesh>

        <TresMesh :position="[0, 1.2, -4.33]" cast-shadow receive-shadow>
          <TresBoxGeometry :args="[12.75, 2.75, 0.28]" />
          <TresMeshStandardMaterial color="#39484a" roughness="1" flat-shading />
        </TresMesh>
        <TresMesh :position="[0, 2.54, -4.16]" cast-shadow>
          <TresBoxGeometry :args="[12.78, 0.16, 0.54]" />
          <TresMeshStandardMaterial color="#d09357" roughness="1" flat-shading />
        </TresMesh>
        <TresMesh v-for="(x, index) in windows" :key="`window-${index}`" :position="[x, 1.58, -4.165]">
          <TresBoxGeometry :args="[2.05, 1.23, 0.045]" />
          <TresMeshBasicMaterial color="#91bec0" />
        </TresMesh>
        <TresMesh v-for="x in [-2.5, 0, 2.5]" :key="`window-mullion-${x}`" :position="[x, 1.58, -4.115]">
          <TresBoxGeometry :args="[0.1, 1.32, 0.08]" />
          <TresMeshStandardMaterial color="#e6b878" roughness="1" flat-shading />
        </TresMesh>
        <TresMesh :position="[0, 1.58, -4.11]">
          <TresBoxGeometry :args="[10.4, 0.09, 0.08]" />
          <TresMeshStandardMaterial color="#e6b878" roughness="1" flat-shading />
        </TresMesh>
        <TresMesh :position="[0, 1.04, -4.075]">
          <TresBoxGeometry :args="[12.2, 0.12, 0.25]" />
          <TresMeshStandardMaterial color="#c07b49" roughness="1" flat-shading />
        </TresMesh>
        <TresMesh :position="[0, 2.32, -4.08]">
          <TresBoxGeometry :args="[1.9, 0.38, 0.05]" />
          <TresMeshStandardMaterial color="#263637" roughness="1" flat-shading />
        </TresMesh>
        <TresMesh :position="[0, 2.34, -4.045]">
          <TresBoxGeometry :args="[1.66, 0.16, 0.025]" />
          <TresMeshBasicMaterial color="#c3ef6a" />
        </TresMesh>

        <TresGroup v-for="(desk, index) in desks" :key="`desk-${index}`" :position="[desk.x, 0, desk.z]">
          <TresMesh :position="[0, -0.14, 0]" receive-shadow>
            <TresBoxGeometry :args="[2.8, 0.12, 1.95]" />
            <TresMeshStandardMaterial color="#202d30" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0, 0.68, 0]" cast-shadow receive-shadow>
            <TresBoxGeometry :args="[2.2, 0.17, 1.22]" />
            <TresMeshStandardMaterial color="#d99456" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh v-for="x in [-0.9, 0.9]" :key="`desk-leg-${x}`" :position="[x, 0.31, 0]">
            <TresBoxGeometry :args="[0.11, 0.62, 0.12]" />
            <TresMeshStandardMaterial color="#704633" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0, 0.95, -0.42]" cast-shadow>
            <TresBoxGeometry :args="[1.02, 0.51, 0.1]" />
            <TresMeshStandardMaterial color="#18282d" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0, 0.96, -0.36]">
            <TresBoxGeometry :args="[0.83, 0.34, 0.024]" />
            <TresMeshBasicMaterial :color="desk.color" />
          </TresMesh>
          <TresMesh :position="[0, 0.76, -0.24]">
            <TresBoxGeometry :args="[0.2, 0.08, 0.18]" />
            <TresMeshStandardMaterial color="#d9bd86" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0, 0.79, 0.3]">
            <TresBoxGeometry :args="[0.73, 0.035, 0.29]" />
            <TresMeshStandardMaterial color="#35454a" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0.76, 0.81, 0.27]">
            <TresCylinderGeometry :args="[0.075, 0.085, 0.16, 6]" />
            <TresMeshStandardMaterial color="#eee2bf" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0.76, 0.93, 0.27]">
            <TresBoxGeometry :args="[0.075, 0.12, 0.07]" />
            <TresMeshStandardMaterial color="#629764" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[-0.75, 0.82, 0.27]">
            <TresBoxGeometry :args="[0.14, 0.08, 0.12]" />
            <TresMeshStandardMaterial color="#e6bd7b" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0, 0.31, 0.72]">
            <TresCylinderGeometry :args="[0.24, 0.28, 0.48, 6]" />
            <TresMeshStandardMaterial color="#41545a" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0, 0.56, 0.72]" cast-shadow>
            <TresBoxGeometry :args="[0.43, 0.09, 0.13]" />
            <TresMeshStandardMaterial color="#d5a067" roughness="1" flat-shading />
          </TresMesh>
        </TresGroup>

        <TresGroup>
          <TresMesh :position="[0, 0.47, 0]" cast-shadow receive-shadow>
            <TresCylinderGeometry :args="[0.82, 0.9, 0.18, 8]" />
            <TresMeshStandardMaterial color="#e0a45e" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0, 0.2, 0]" cast-shadow>
            <TresBoxGeometry :args="[0.28, 0.46, 0.28]" />
            <TresMeshStandardMaterial color="#7a4c38" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[-0.31, 0.6, -0.11]" cast-shadow>
            <TresBoxGeometry :args="[0.42, 0.05, 0.28]" />
            <TresMeshStandardMaterial color="#26383b" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[-0.31, 0.64, -0.1]">
            <TresBoxGeometry :args="[0.32, 0.018, 0.19]" />
            <TresMeshBasicMaterial color="#b9f064" />
          </TresMesh>
          <TresMesh :position="[0.34, 0.6, 0.12]" cast-shadow>
            <TresBoxGeometry :args="[0.42, 0.05, 0.28]" />
            <TresMeshStandardMaterial color="#26383b" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0.34, 0.64, 0.13]">
            <TresBoxGeometry :args="[0.32, 0.018, 0.19]" />
            <TresMeshBasicMaterial color="#b9f064" />
          </TresMesh>
          <TresMesh :position="[0, 0.73, -0.04]">
            <TresBoxGeometry :args="[0.1, 0.07, 0.12]" />
            <TresMeshStandardMaterial color="#fff0cf" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0, 0.79, 0]">
            <TresBoxGeometry :args="[0.045, 0.025, 0.05]" />
            <TresMeshBasicMaterial color="#ef6e58" />
          </TresMesh>
        </TresGroup>

        <TresGroup
          v-for="(character, index) in characters"
          :key="character.agent?.name ?? index"
          :position="character.position"
          :rotation="[0, character.rotation, 0]"
        >
          <TresMesh :position="[0, 0.075, 0]" cast-shadow>
            <TresBoxGeometry :args="[0.38, 0.12, 0.32]" />
            <TresMeshStandardMaterial color="#26363b" roughness="1" flat-shading />
          </TresMesh>
          <TresGroup :position="[-0.105, 0.22, 0]" :rotation="[character.gait, 0, 0]">
            <TresMesh :position="[0, 0.13, 0]" cast-shadow>
              <TresBoxGeometry :args="[0.13, 0.3, 0.17]" />
              <TresMeshStandardMaterial color="#41545c" roughness="1" flat-shading />
            </TresMesh>
            <TresMesh :position="[0, 0.29, 0.025]" cast-shadow>
              <TresBoxGeometry :args="[0.16, 0.075, 0.25]" />
              <TresMeshStandardMaterial color="#ead1a5" roughness="1" flat-shading />
            </TresMesh>
          </TresGroup>
          <TresGroup :position="[0.105, 0.22, 0]" :rotation="[-character.gait, 0, 0]">
            <TresMesh :position="[0, 0.13, 0]" cast-shadow>
              <TresBoxGeometry :args="[0.13, 0.3, 0.17]" />
              <TresMeshStandardMaterial color="#41545c" roughness="1" flat-shading />
            </TresMesh>
            <TresMesh :position="[0, 0.29, 0.025]" cast-shadow>
              <TresBoxGeometry :args="[0.16, 0.075, 0.25]" />
              <TresMeshStandardMaterial color="#ead1a5" roughness="1" flat-shading />
            </TresMesh>
          </TresGroup>
          <TresMesh :position="[0, 0.58, 0]" cast-shadow>
            <TresBoxGeometry :args="[0.46, 0.47, 0.3]" />
            <TresMeshStandardMaterial :color="character.color" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0, 0.47, 0.158]">
            <TresBoxGeometry :args="[0.13, 0.075, 0.018]" />
            <TresMeshBasicMaterial color="#f6e6bd" />
          </TresMesh>
          <TresGroup :position="[-0.28, 0.68, 0]" :rotation="[0, 0, -0.12 + character.gait * 0.7]">
            <TresMesh :position="[0, 0.02, 0]" cast-shadow>
              <TresBoxGeometry :args="[0.14, 0.34, 0.17]" />
              <TresMeshStandardMaterial :color="character.color" roughness="1" flat-shading />
            </TresMesh>
            <TresMesh :position="[0, -0.17, 0.025]">
              <TresBoxGeometry :args="[0.12, 0.1, 0.15]" />
              <TresMeshStandardMaterial color="#efc99c" roughness="1" flat-shading />
            </TresMesh>
          </TresGroup>
          <TresGroup :position="[0.28, 0.68, 0]" :rotation="[0, 0, 0.12 - character.gait * 0.7]">
            <TresMesh :position="[0, 0.02, 0]" cast-shadow>
              <TresBoxGeometry :args="[0.14, 0.34, 0.17]" />
              <TresMeshStandardMaterial :color="character.color" roughness="1" flat-shading />
            </TresMesh>
            <TresMesh :position="[0, -0.17, 0.025]">
              <TresBoxGeometry :args="[0.12, 0.1, 0.15]" />
              <TresMeshStandardMaterial color="#efc99c" roughness="1" flat-shading />
            </TresMesh>
          </TresGroup>
          <TresMesh :position="[0, 0.99, 0.015]" cast-shadow>
            <TresBoxGeometry :args="[0.39, 0.39, 0.34]" />
            <TresMeshStandardMaterial color="#e9bb89" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0, 1.17, -0.005]" cast-shadow>
            <TresBoxGeometry :args="[0.43, 0.16, 0.38]" />
            <TresMeshStandardMaterial color="#493d3a" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[-0.085, 1.01, 0.19]">
            <TresBoxGeometry :args="[0.055, 0.055, 0.025]" />
            <TresMeshBasicMaterial color="#203236" />
          </TresMesh>
          <TresMesh :position="[0.085, 1.01, 0.19]">
            <TresBoxGeometry :args="[0.055, 0.055, 0.025]" />
            <TresMeshBasicMaterial color="#203236" />
          </TresMesh>
          <TresMesh :position="[0, 0.86, 0.185]">
            <TresBoxGeometry :args="[0.11, 0.035, 0.025]" />
            <TresMeshBasicMaterial :color="statusColor(character.agent?.status)" />
          </TresMesh>
          <TresMesh :position="[0, 1.4, 0]">
            <TresBoxGeometry :args="[0.3, 0.035, 0.08]" />
            <TresMeshBasicMaterial :color="statusColor(character.agent?.status)" />
          </TresMesh>
        </TresGroup>

        <TresGroup v-for="(plant, index) in plants" :key="`plant-${index}`" :position="[plant.x, 0, plant.z]">
          <TresMesh :position="[0, 0.16, 0]">
            <TresCylinderGeometry :args="[0.24, 0.31, 0.32, 6]" />
            <TresMeshStandardMaterial color="#d89455" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0, 0.56, 0]">
            <TresBoxGeometry :args="[0.09, 0.58, 0.09]" />
            <TresMeshStandardMaterial color="#507e53" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[-0.17, 0.61, 0]">
            <TresBoxGeometry :args="[0.27, 0.19, 0.21]" />
            <TresMeshStandardMaterial color="#72a85e" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0.18, 0.73, 0.015]">
            <TresBoxGeometry :args="[0.29, 0.2, 0.22]" />
            <TresMeshStandardMaterial color="#508c58" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh :position="[0, 0.91, -0.025]">
            <TresBoxGeometry :args="[0.28, 0.23, 0.25]" />
            <TresMeshStandardMaterial color="#8ab65f" roughness="1" flat-shading />
          </TresMesh>
        </TresGroup>

        <TresGroup v-for="(x, index) in [-5.2, 5.2]" :key="`shelf-${index}`" :position="[x, 0, -0.3]">
          <TresMesh :position="[0, 0.73, 0]" cast-shadow>
            <TresBoxGeometry :args="[0.6, 1.48, 0.8]" />
            <TresMeshStandardMaterial color="#704b3d" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh v-for="y in [0.38, 0.82, 1.26]" :key="`shelf-${y}`" :position="[0, y, 0.41]">
            <TresBoxGeometry :args="[0.56, 0.055, 0.08]" />
            <TresMeshStandardMaterial color="#e2a15c" roughness="1" flat-shading />
          </TresMesh>
          <TresMesh v-for="(item, itemIndex) in [0, 1, 2]" :key="`books-${itemIndex}`" :position="[-0.16 + itemIndex * 0.14, 0.52 + (itemIndex % 2) * 0.44, 0.33]">
            <TresBoxGeometry :args="[0.1, 0.2 + (itemIndex % 2) * 0.08, 0.1]" />
            <TresMeshStandardMaterial :color="itemIndex === 1 ? '#c46c52' : '#78a49a'" roughness="1" flat-shading />
          </TresMesh>
        </TresGroup>
      </TresCanvas>
      <template #fallback>
        <div class="scene-loading">Membuka ruang kerja NF...</div>
      </template>
    </ClientOnly>
  </div>
</template>
