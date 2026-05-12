<template>
  <div class="qa-row">
    <button
      v-for="a in actions"
      :key="a.label"
      class="qa-btn"
      @click="emit('action', a.text)"
    >
      {{ a.label }}
    </button>
  </div>
</template>

<script setup>
const emit = defineEmits(['action'])

const actions = [
  { label: '🩺 ตรวจ Health',  text: 'ตรวจ health ระบบทั้งหมด โหมด plan-only' },
  { label: '📋 ดู Jobs',      text: 'สรุป jobs ล่าสุด' },
  { label: '📚 Ingest RAG',   text: 'เพิ่มเอกสารใน data/documents เข้า RAG' },
  { label: '🐳 ตรวจ Docker',  text: 'ตรวจ docker status และ service health' },
  { label: '📄 เปิด Logs',    text: 'สรุป logs ล่าสุดของระบบ' },
]
</script>

<style scoped>
.qa-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 14px;
  background: #f8f9fc;
  border-top: 1px solid #e9ecef;
}

.qa-btn {
  padding: 5px 11px;
  border-radius: 999px;
  border: 1px solid #d1d5db;
  background: #fff;
  color: #374151;
  font-size: 0.72rem;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}
.qa-btn:hover {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1d4ed8;
}
</style>
