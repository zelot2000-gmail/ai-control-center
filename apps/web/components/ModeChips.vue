<template>
  <div class="chips-row">
    <button
      v-for="m in modes"
      :key="m.value"
      class="chip"
      :class="{ active: modelValue === m.value }"
      @click="select(m)"
    >
      {{ m.label }}
    </button>
    <span class="prod-note" v-if="modelValue === 'production'">
      ⚠️ Production ต้องใช้ approval ก่อนเสมอ
    </span>
  </div>
</template>

<script setup>
const props = defineProps({ modelValue: { type: String, default: 'plan-only' } })
const emit = defineEmits(['update:modelValue'])

const modes = [
  { value: 'plan-only',   label: 'Plan Only' },
  { value: 'dev-fix',     label: 'Dev Fix' },
  { value: 'staging',     label: 'Staging' },
  { value: 'production',  label: 'Production' },
]

function select(m) {
  emit('update:modelValue', m.value)
}
</script>

<style scoped>
.chips-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 14px;
  background: #f8f9fc;
  border-bottom: 1px solid #e9ecef;
  align-items: center;
}

.chip {
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid #d1d5db;
  background: #fff;
  color: #4b5563;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.chip:hover { border-color: #1d6fe8; color: #1d6fe8; }
.chip.active {
  background: #1d6fe8;
  border-color: #1d6fe8;
  color: #fff;
}

.prod-note {
  font-size: 0.68rem;
  color: #d97706;
  font-weight: 500;
}
</style>
