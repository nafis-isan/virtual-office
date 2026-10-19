<script setup lang="ts">
import type { Agent, AgentStatus } from '~/types/office'

type Position = [number, number, number]
type Point = { x: number; z: number; color: string }

const props = defineProps<{ agents: Agent[] }>()

const desks: Point[] = [
  { x: -4.15, z: -2.8, color: '#35a98d' },
  { x: 4.15, z: -2.8, color: '#8b75d8' },
  { x: -4.15, z: 2.8, color: '#e49a5c' },
  { x: 4.15, z: 2.8, color: '#5d91ca' },
]
const homes: Position[] = [
  [-4.15, 0.08, -1.55],
  [4.15, 0.08, -1.55],
  [-4.15, 0.08, 1.55],
  [4.15, 0.08, 1.55],
]
const meetingPoints: Position[] = [
  [-1.55, 0.08, -1.1],
  [1.55, 0.08, -1.1],
  [-1.55, 0.08, 1.1],
  [1.55, 0.08, 1.1],
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
  if (status === 'working' || status === 'thinking') return '#55d6a1'
  if (status === 'waiting' || status === 'waiting_approval') return '#f1bb63'
  if (status === 'failed') return '#ed7377'
  if (status === 'completed') return '#7f8ba2'
  return '#aab5c4'
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
    const distance = Math.hypot(dx, dz)
    const moving = distance > 0.035
    const easing = Math.min(1, delta * 1.8)
    const stepHeight = moving ? Math.abs(Math.sin(elapsed * 9 + index)) * 0.055 : 0

    nextPositions[index] = [
      current[0] + dx * easing,
      0.08 + stepHeight,
      current[2] + dz * easing,
    ]
    nextGaits[index] = moving ? Math.sin(elapsed * 9 + index) * 0.48 : 0

    const direction = moving
      ? Math.atan2(dx, dz)
      : Math.atan2(-current[0], -current[2])
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
    <ClientOnly>
      <TresCanvas
        clear-color="#e9f0ef"
        :shadows="true"
        :dpr="[1, 1.5]"
        :antialias="true"
        @loop="animateAgents"
      >
        <TresPerspectiveCamera
          :position="[0, 13, 15]"
          :rotation="[-0.68, 0, 0]"
          :fov="42"
          :near="0.1"
          :far="100"
        />
        <TresAmbientLight :intensity="1.9" />
        <TresDirectionalLight :position="[-6, 11, 8]" :intensity="2.7" cast-shadow />
        <TresDirectionalLight :position="[5, 7, -4]" :intensity="0.75" color="#d6ecff" />

        <TresMesh :position="[0, -0.26, 0]" receive-shadow>
          <TresBoxGeometry :args="[12.5, 0.34, 8.7]" />
          <TresMeshStandardMaterial color="#e3e9e5" roughness="0.92" />
        </TresMesh>
        <TresMesh :position="[0, -0.075, 0]" receive-shadow>
          <TresBoxGeometry :args="[5.3, 0.06, 3.45]" />
          <TresMeshStandardMaterial color="#bed9d0" roughness="0.96" />
        </TresMesh>

        <TresGroup v-for="desk in desks" :key="`desk-${desk.x}-${desk.z}`" :position="[desk.x, 0, desk.z]">
          <TresMesh :position="[0, -0.15, 0]" receive-shadow>
            <TresBoxGeometry :args="[2.65, 0.08, 1.75]" />
            <TresMeshStandardMaterial color="#f1f4f1" roughness="0.9" />
          </TresMesh>
          <TresMesh :position="[0, 0.7, 0]" cast-shadow receive-shadow>
            <TresBoxGeometry :args="[1.95, 0.14, 1.13]" />
            <TresMeshStandardMaterial color="#ba8966" roughness="0.78" />
          </TresMesh>
          <TresMesh v-for="x in [-0.78, 0.78]" :key="`leg-x-${x}`" :position="[x, 0.33, 0]">
            <TresBoxGeometry :args="[0.09, 0.67, 0.1]" />
            <TresMeshStandardMaterial color="#8b654c" />
          </TresMesh>
          <TresMesh :position="[0, 1.05, -0.23]" cast-shadow>
            <TresBoxGeometry :args="[0.82, 0.52, 0.08]" />
            <TresMeshStandardMaterial color="#344f61" roughness="0.35" />
          </TresMesh>
          <TresMesh :position="[0, 1.06, -0.18]">
            <TresBoxGeometry :args="[0.68, 0.38, 0.025]" />
            <TresMeshStandardMaterial color="#91d8c5" emissive="#246255" emissive-intensity="0.35" />
          </TresMesh>
          <TresMesh :position="[0, 0.82, 0.3]">
            <TresBoxGeometry :args="[0.52, 0.035, 0.2]" />
            <TresMeshStandardMaterial color="#55697a" />
          </TresMesh>
          <TresMesh :position="[0.72, 0.89, 0.28]">
            <TresCylinderGeometry :args="[0.08, 0.07, 0.16, 12]" />
            <TresMeshStandardMaterial color="#f0d2a8" />
          </TresMesh>
          <TresMesh :position="[0.72, 0.99, 0.28]">
            <TresCylinderGeometry :args="[0.045, 0.045, 0.05, 12]" />
            <TresMeshStandardMaterial color="#679c83" />
          </TresMesh>
        </TresGroup>

        <TresMesh :position="[0, 0.46, 0]" cast-shadow receive-shadow>
          <TresCylinderGeometry :args="[1.15, 1.2, 0.16, 32]" />
          <TresMeshStandardMaterial color="#b98664" roughness="0.7" />
        </TresMesh>
        <TresMesh :position="[0, 0.16, 0]" cast-shadow>
          <TresCylinderGeometry :args="[0.2, 0.27, 0.48, 16]" />
          <TresMeshStandardMaterial color="#82978e" />
        </TresMesh>
        <TresMesh :position="[-0.43, 0.58, -0.12]" cast-shadow>
          <TresBoxGeometry :args="[0.45, 0.06, 0.32]" />
          <TresMeshStandardMaterial color="#526b78" />
        </TresMesh>
        <TresMesh :position="[-0.43, 0.63, -0.11]">
          <TresBoxGeometry :args="[0.35, 0.015, 0.22]" />
          <TresMeshStandardMaterial color="#a9e2d5" emissive="#2c7566" emissive-intensity="0.25" />
        </TresMesh>
        <TresMesh :position="[0.43, 0.58, 0.12]" cast-shadow>
          <TresBoxGeometry :args="[0.45, 0.06, 0.32]" />
          <TresMeshStandardMaterial color="#526b78" />
        </TresMesh>
        <TresMesh :position="[0.43, 0.63, 0.13]">
          <TresBoxGeometry :args="[0.35, 0.015, 0.22]" />
          <TresMeshStandardMaterial color="#a9e2d5" emissive="#2c7566" emissive-intensity="0.25" />
        </TresMesh>

        <TresGroup
          v-for="(character, index) in characters"
          :key="character.agent?.name ?? index"
          :position="character.position"
          :rotation="[0, character.rotation, 0]"
        >
          <TresMesh :position="[0, 0.11, 0]" cast-shadow>
            <TresCylinderGeometry :args="[0.2, 0.22, 0.18, 16]" />
            <TresMeshStandardMaterial color="#425469" />
          </TresMesh>
          <TresMesh :position="[0, 0.62, 0]" cast-shadow>
            <TresCapsuleGeometry :args="[0.23, 0.4, 4, 10]" />
            <TresMeshStandardMaterial
              :color="character.agent?.status === 'offline' ? '#a6b2ba' : character.color"
              :emissive="statusColor(character.agent?.status)"
              :emissive-intensity="character.agent?.status === 'working' ? 0.16 : 0.025"
              roughness="0.55"
            />
          </TresMesh>
          <TresGroup :position="[-0.24, 0.72, 0]" :rotation="[character.gait * 0.65, 0, -0.16]">
            <TresMesh :position="[0, -0.17, 0]" cast-shadow>
              <TresCapsuleGeometry :args="[0.075, 0.3, 3, 8]" />
              <TresMeshStandardMaterial color="#e9b88f" />
            </TresMesh>
            <TresMesh :position="[0, -0.34, 0.02]">
              <TresSphereGeometry :args="[0.08, 12, 8]" />
              <TresMeshStandardMaterial color="#efc39f" />
            </TresMesh>
          </TresGroup>
          <TresGroup :position="[0.24, 0.72, 0]" :rotation="[-character.gait * 0.65, 0, 0.16]">
            <TresMesh :position="[0, -0.17, 0]" cast-shadow>
              <TresCapsuleGeometry :args="[0.075, 0.3, 3, 8]" />
              <TresMeshStandardMaterial color="#e9b88f" />
            </TresMesh>
            <TresMesh :position="[0, -0.34, 0.02]">
              <TresSphereGeometry :args="[0.08, 12, 8]" />
              <TresMeshStandardMaterial color="#efc39f" />
            </TresMesh>
          </TresGroup>
          <TresGroup :position="[-0.095, 0.42, 0]" :rotation="[character.gait, 0, 0]">
            <TresMesh :position="[0, -0.18, 0]" cast-shadow>
              <TresCapsuleGeometry :args="[0.085, 0.29, 3, 8]" />
              <TresMeshStandardMaterial color="#526577" />
            </TresMesh>
            <TresMesh :position="[0, -0.34, 0.06]">
              <TresBoxGeometry :args="[0.16, 0.08, 0.25]" />
              <TresMeshStandardMaterial color="#d6e1dd" />
            </TresMesh>
          </TresGroup>
          <TresGroup :position="[0.095, 0.42, 0]" :rotation="[-character.gait, 0, 0]">
            <TresMesh :position="[0, -0.18, 0]" cast-shadow>
              <TresCapsuleGeometry :args="[0.085, 0.29, 3, 8]" />
              <TresMeshStandardMaterial color="#526577" />
            </TresMesh>
            <TresMesh :position="[0, -0.34, 0.06]">
              <TresBoxGeometry :args="[0.16, 0.08, 0.25]" />
              <TresMeshStandardMaterial color="#d6e1dd" />
            </TresMesh>
          </TresGroup>
          <TresMesh :position="[0, 1.04, 0]" cast-shadow>
            <TresSphereGeometry :args="[0.22, 18, 14]" />
            <TresMeshStandardMaterial color="#f2c9a8" roughness="0.72" />
          </TresMesh>
          <TresMesh :position="[0, 1.17, -0.025]" cast-shadow>
            <TresSphereGeometry :args="[0.2, 16, 10]" />
            <TresMeshStandardMaterial color="#574439" roughness="0.92" />
          </TresMesh>
          <TresMesh :position="[-0.075, 1.055, 0.193]">
            <TresSphereGeometry :args="[0.023, 8, 8]" />
            <TresMeshBasicMaterial color="#263844" />
          </TresMesh>
          <TresMesh :position="[0.075, 1.055, 0.193]">
            <TresSphereGeometry :args="[0.023, 8, 8]" />
            <TresMeshBasicMaterial color="#263844" />
          </TresMesh>
        </TresGroup>

        <TresGroup v-for="plant in [{ x: -5.1, z: -3.25 }, { x: 5.1, z: -3.25 }, { x: -5.1, z: 3.25 }, { x: 5.1, z: 3.25 }]" :key="`${plant.x}-${plant.z}`" :position="[plant.x, 0, plant.z]">
          <TresMesh :position="[0, 0.16, 0]">
            <TresCylinderGeometry :args="[0.22, 0.3, 0.32, 12]" />
            <TresMeshStandardMaterial color="#bb8c6a" />
          </TresMesh>
          <TresMesh :position="[0, 0.68, 0]">
            <TresCylinderGeometry :args="[0.035, 0.04, 0.78, 8]" />
            <TresMeshStandardMaterial color="#648c72" />
          </TresMesh>
          <TresMesh :position="[-0.21, 0.62, 0]">
            <TresSphereGeometry :args="[0.27, 12, 10]" />
            <TresMeshStandardMaterial color="#6eaa85" />
          </TresMesh>
          <TresMesh :position="[0.2, 0.78, 0.04]">
            <TresSphereGeometry :args="[0.28, 12, 10]" />
            <TresMeshStandardMaterial color="#579676" />
          </TresMesh>
          <TresMesh :position="[0, 1.02, -0.04]">
            <TresSphereGeometry :args="[0.28, 12, 10]" />
            <TresMeshStandardMaterial color="#79b58f" />
          </TresMesh>
        </TresGroup>

        <TresMesh :position="[0, 1.05, -4.27]">
          <TresBoxGeometry :args="[12.45, 2.6, 0.15]" />
          <TresMeshStandardMaterial color="#dce7e6" />
        </TresMesh>
        <TresMesh v-for="x in [-3.8, -1.3, 1.3, 3.8]" :key="`window-${x}`" :position="[x, 1.08, -4.17]">
          <TresBoxGeometry :args="[2.15, 1.55, 0.035]" />
          <TresMeshStandardMaterial color="#a9d7dc" emissive="#4b8d91" emissive-intensity="0.13" />
        </TresMesh>
        <TresMesh :position="[0, 1.08, -4.12]">
          <TresBoxGeometry :args="[0.09, 1.72, 0.05]" />
          <TresMeshStandardMaterial color="#f2f5f0" />
        </TresMesh>
        <TresMesh :position="[0, 1.1, -4.11]">
          <TresBoxGeometry :args="[9.7, 0.1, 0.05]" />
          <TresMeshStandardMaterial color="#f2f5f0" />
        </TresMesh>
      </TresCanvas>
      <template #fallback>
        <div class="scene-loading">Menyiapkan kantor 3D...</div>
      </template>
    </ClientOnly>
  </div>
</template>
