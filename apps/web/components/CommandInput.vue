<template>
  <div class="input-area">
    <!-- Attached files -->
    <div class="file-list" v-if="attachedFiles.length">
      <div class="file-chip" v-for="(f, i) in attachedFiles" :key="i">
        <span class="file-name">📎 {{ f.name }}</span>
        <span class="file-size">({{ fmtSize(f.size) }})</span>
        <button class="file-remove" @click="removeFile(i)" aria-label="ลบไฟล์">✕</button>
      </div>
    </div>

    <!-- Input row -->
    <div class="input-row">
      <!-- Hidden file input -->
      <input
        ref="fileInputRef"
        type="file"
        multiple
        class="hidden-file-input"
        accept=".txt,.md,.log,.json,.yaml,.yml,.csv,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.jpg,.jpeg,.png,.webp,.gif"
        @change="onFilesSelected"
      />

      <!-- Attach button -->
      <button
        class="attach-btn"
        title="แนบไฟล์"
        aria-label="แนบไฟล์"
        @click="fileInputRef?.click()"
        :disabled="isSending"
      >
        📎
      </button>

      <!-- Text input -->
      <input
        ref="inputRef"
        v-model="localText"
        class="text-input"
        type="text"
        placeholder="พิมพ์คำสั่งให้ทีม AI..."
        aria-label="พิมพ์คำสั่ง"
        :disabled="isSending"
        @keydown.enter.exact.prevent="onSend"
      />

      <!-- Send button -->
      <button
        class="send-btn"
        aria-label="ส่งคำสั่ง"
        :disabled="isSending || (!localText.trim() && !attachedFiles.length)"
        @click="onSend"
      >
        <span v-if="isSending">⏳</span>
        <span v-else>ส่งคำสั่ง</span>
      </button>
    </div>
  </div>
</template>

<script setup>
const MAX_FILE_SIZE = 10 * 1024 * 1024
const MAX_FILES = 5

const props = defineProps({
  text:      { type: String, default: '' },
  isSending: { type: Boolean, default: false },
})
const emit = defineEmits(['update:text', 'send', 'error'])

const fileInputRef = ref(null)
const inputRef     = ref(null)
const attachedFiles = ref([])

const localText = computed({
  get: () => props.text,
  set: (v) => emit('update:text', v),
})

function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

function onFilesSelected(e) {
  const selected = Array.from(e.target.files || [])
  const errors = []

  for (const f of selected) {
    if (attachedFiles.value.length >= MAX_FILES) {
      errors.push(`แนบได้สูงสุด ${MAX_FILES} ไฟล์`)
      break
    }
    if (f.size > MAX_FILE_SIZE) {
      errors.push(`ไฟล์ ${f.name} ใหญ่เกิน 10MB`)
      continue
    }
    if (!attachedFiles.value.find(x => x.name === f.name && x.size === f.size)) {
      attachedFiles.value.push(f)
    }
  }
  if (errors.length) emit('error', errors.join('\n'))
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function removeFile(index) {
  attachedFiles.value.splice(index, 1)
}

function onSend() {
  const text = localText.value?.trim()
  if (!text && !attachedFiles.value.length) return
  if (props.isSending) return
  emit('send', { text: text || '', files: [...attachedFiles.value] })
  attachedFiles.value = []
}

defineExpose({ focus: () => inputRef.value?.focus() })
</script>

<style scoped>
.input-area {
  background: #fff;
  border-top: 1px solid #e5e7eb;
  padding: 10px 14px 12px;
}

.file-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.file-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 3px 8px;
  font-size: 0.72rem;
}
.file-name { color: #1d4ed8; font-weight: 500; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-size { color: #6b7280; }
.file-remove {
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  padding: 0 2px;
  font-size: 0.75rem;
  line-height: 1;
}
.file-remove:hover { color: #ef4444; }

.input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.hidden-file-input { display: none; }

.attach-btn {
  flex-shrink: 0;
  width: 40px;
  height: 44px;
  border-radius: 999px;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.attach-btn:hover:not(:disabled) { background: #eff6ff; border-color: #93c5fd; }
.attach-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.text-input {
  flex: 1;
  height: 44px;
  border: 1px solid #d1d5db;
  border-radius: 999px;
  padding: 0 18px;
  font-size: 0.95rem;
  font-family: inherit;
  color: #1a1a2e;
  outline: none;
  background: #fff;
  transition: border-color 0.15s;
}
.text-input:focus { border-color: #1d6fe8; box-shadow: 0 0 0 3px rgba(29,111,232,0.1); }
.text-input:disabled { background: #f9fafb; opacity: 0.7; }
.text-input::placeholder { color: #9ca3af; }

.send-btn {
  flex-shrink: 0;
  height: 44px;
  padding: 0 20px;
  border: none;
  border-radius: 999px;
  background: #1d6fe8;
  color: #fff;
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
  min-width: 96px;
}
.send-btn:hover:not(:disabled) { background: #1558c0; }
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

@media (max-width: 400px) {
  .send-btn { min-width: 80px; padding: 0 12px; font-size: 0.82rem; }
}
</style>
