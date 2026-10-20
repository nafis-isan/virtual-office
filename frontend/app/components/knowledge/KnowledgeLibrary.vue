<script setup lang="ts">
import type { KnowledgeDocument } from '~/types/office'

const props = withDefaults(defineProps<{ search?: string }>(), { search: '' })
const api = useOfficeApi()
const documents = ref<KnowledgeDocument[]>([])
const loading = ref(true)
const uploading = ref(false)
const deletingId = ref<number | null>(null)
const errorMessage = ref('')
const successMessage = ref('')
const filteredDocuments = computed(() => {
  const query = props.search.trim().toLocaleLowerCase('id')
  if (!query) return documents.value
  return documents.value.filter((document) =>
    `${document.filename} ${document.content_type}`.toLocaleLowerCase('id').includes(query),
  )
})

function errorText(error: unknown) {
  if (typeof error === 'object' && error !== null && 'data' in error) {
    const data = error.data
    if (typeof data === 'object' && data !== null && 'detail' in data && typeof data.detail === 'string') {
      return data.detail
    }
  }
  return 'Permintaan dokumen gagal. Pastikan backend dan koneksi Gemini tersedia.'
}

async function refreshDocuments() {
  try {
    documents.value = await api.getKnowledgeDocuments()
  } catch (error) {
    errorMessage.value = errorText(error)
  } finally {
    loading.value = false
  }
}

async function uploadDocument(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || uploading.value) return

  uploading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const document = await api.uploadKnowledgeDocument(file)
    documents.value = [document, ...documents.value]
    successMessage.value = `${document.filename} siap digunakan sebagai sumber RAG.`
  } catch (error) {
    errorMessage.value = errorText(error)
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function deleteDocument(document: KnowledgeDocument) {
  if (deletingId.value !== null) return
  deletingId.value = document.id
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await api.deleteKnowledgeDocument(document.id)
    documents.value = documents.value.filter((item) => item.id !== document.id)
  } catch (error) {
    errorMessage.value = errorText(error)
  } finally {
    deletingId.value = null
  }
}

onMounted(refreshDocuments)
</script>

<template>
  <section class="panel knowledge-panel" aria-labelledby="knowledge-heading">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">PIXEL ARCHIVE <span class="heading-divider">/</span> RAG</p>
        <h2 id="knowledge-heading">Pustaka dokumen</h2>
      </div>
      <span class="knowledge-count">{{ documents.length }} FILE</span>
    </div>
    <p class="muted knowledge-hint">
      Teks dokumen dikirim ke Gemini untuk embedding dan jawaban; hanya teks serta embedding yang disimpan.
      Jangan unggah informasi sensitif.
    </p>
    <label class="knowledge-upload">
      <input
        type="file"
        accept=".pdf,.txt,.md,.docx,application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        :disabled="uploading"
        @change="uploadDocument"
      >
      <span class="upload-icon" aria-hidden="true"><svg viewBox="0 0 16 16"><path d="M8 3v10M3 8h10" /></svg></span>
      <span><strong>{{ uploading ? 'Mengindeks dokumen...' : 'Tambah dokumen' }}</strong><small>PDF, TXT, MD, DOCX · maks. 5 MB</small></span>
    </label>
    <p v-if="errorMessage" class="knowledge-message knowledge-error" role="alert">{{ errorMessage }}</p>
    <p v-else-if="successMessage" class="knowledge-message knowledge-success" role="status">{{ successMessage }}</p>
    <p v-if="loading" class="muted small-copy">Memuat pustaka...</p>
    <div v-else-if="filteredDocuments.length" class="knowledge-list">
      <article v-for="document in filteredDocuments" :key="document.id" class="knowledge-row">
        <span class="document-pixel" aria-hidden="true"><svg viewBox="0 0 18 18"><path d="M4 2.5h6.5l3.5 3.4v9.6H4z" /><path d="M10.5 2.8v3.5h3.2M6.5 9h5M6.5 12h5" /></svg></span>
        <span class="knowledge-file">
          <strong>{{ document.filename }}</strong>
          <small>{{ document.chunk_count }} potongan · {{ new Date(document.created_at).toLocaleDateString('id-ID') }}</small>
        </span>
        <button
          class="knowledge-delete"
          type="button"
          :aria-label="`Hapus ${document.filename}`"
          :disabled="deletingId !== null"
          @click="deleteDocument(document)"
        ><svg v-if="deletingId !== document.id" viewBox="0 0 16 16" aria-hidden="true"><path d="m4 4 8 8M12 4l-8 8" /></svg><span v-else class="sr-only">Menghapus</span></button>
      </article>
    </div>
    <p v-else-if="documents.length" class="knowledge-empty">Tidak ada dokumen yang cocok dengan pencarian.</p>
    <p v-else class="knowledge-empty">Belum ada dokumen. Tambahkan sumber untuk memberi agent konteks khusus.</p>
  </section>
</template>
