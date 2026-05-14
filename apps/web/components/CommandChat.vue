<template>
  <div class="chat-area" ref="el">
    <CommandBubble
      v-for="msg in messages"
      :key="msg.id"
      :msg="msg"
      @viewPrompt="$emit('viewPrompt', $event)"
      @runAgent="$emit('runAgent', $event)"
      @saveReport="$emit('saveReport', $event)"
      @viewReport="$emit('viewReport', $event)"
      @viewTimeline="$emit('viewTimeline', $event)"
      @copyAgentPrompt="$emit('copyAgentPrompt', $event)"
      @saveAgentReport="$emit('saveAgentReport', $event)"
      @approveAgentRun="$emit('approveAgentRun', $event)"
      @applyCodeEdit="$emit('applyCodeEdit', $event)"
      @commitCodeEdit="$emit('commitCodeEdit', $event)"
      @rollbackCodeEdit="$emit('rollbackCodeEdit', $event)"
      @viewCodeEditPatch="$emit('viewCodeEditPatch', $event)"
    />
    <div class="typing" v-if="isSending">
      <span></span><span></span><span></span>
    </div>
  </div>
</template>

<script setup>
import CommandBubble from './CommandBubble.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  isSending: { type: Boolean, default: false },
})
defineEmits([
  'viewPrompt', 'runAgent', 'saveReport', 'viewReport', 'viewTimeline',
  'copyAgentPrompt', 'saveAgentReport', 'approveAgentRun',
  'applyCodeEdit', 'commitCodeEdit', 'rollbackCodeEdit', 'viewCodeEditPatch',
])

const el = ref(null)

function scrollToBottom() {
  nextTick(() => {
    if (el.value) el.value.scrollTop = el.value.scrollHeight
  })
}

defineExpose({ scrollToBottom })
</script>

<style scoped>
.chat-area {
  flex: 1;
  background: #ede8df;
  padding: 16px;
  overflow-y: auto;
  min-height: 300px;
}

.typing {
  display: flex;
  gap: 5px;
  padding: 10px 14px;
  background: #fff;
  border-radius: 16px;
  width: fit-content;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.typing span {
  width: 8px; height: 8px; border-radius: 50%;
  background: #9ca3af;
  animation: bounce 1.2s infinite;
}
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-6px); }
}
</style>
