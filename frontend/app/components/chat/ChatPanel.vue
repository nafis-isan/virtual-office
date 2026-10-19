<script setup lang="ts">
const props = defineProps<{ sending: boolean; disabled: boolean }>()
const emit = defineEmits<{ submit: [instruction: string] }>()
const instruction = ref('')

function submit() {
  const value = instruction.value.trim()
  if (!value || props.sending || props.disabled) return
  emit('submit', value)
  instruction.value = ''
}
</script>

<template>
  <section class="panel chat-panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">MULAI PROYEK</p>
        <h2>Instruksi untuk tim</h2>
      </div>
      <span class="chat-spark">✳</span>
    </div>
    <p class="muted chat-hint">
      Project Manager akan menyusun langkah dan mendelegasikan pekerjaan kepada specialist.
    </p>
    <form class="chat-form" @submit.prevent="submit">
      <label class="sr-only" for="task-instruction">Instruksi tugas</label>
      <textarea
        id="task-instruction"
        v-model="instruction"
        maxlength="4000"
        rows="3"
        placeholder="Contoh: Riset ide landing page untuk aplikasi belajar bahasa..."
        :disabled="disabled || sending"
        required
      />
      <div class="chat-form-footer">
        <span>{{ instruction.length }}/4000</span>
        <button class="primary-button" type="submit" :disabled="disabled || sending || !instruction.trim()">
          <span>{{ sending ? 'Mengirim...' : 'Kirim instruksi' }}</span>
          <span aria-hidden="true">↗</span>
        </button>
      </div>
    </form>
    <p v-if="disabled" class="form-note">
      Backend atau database belum siap. Lengkapi konfigurasi dan jalankan layanan terlebih dahulu.
    </p>
  </section>
</template>
