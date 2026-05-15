<template>
  <aside class="cw-inspector">
    <!-- Header -->
    <div class="ci-header">
      <span class="ci-title">Inspector</span>
      <button class="ci-close-btn" v-if="closeable" @click="$emit('close')">✕</button>
    </div>

    <!-- Empty state: no task, no wsInfo -->
    <div class="ci-empty" v-if="!activeTask && !wsInfo">
      <div class="ci-empty-icon">◈</div>
      <div class="ci-empty-title">เริ่มต้นได้เลย</div>
      <div class="ci-empty-sub">พิมพ์คำสั่ง หรือเลือก workspace เพื่อเริ่มงาน</div>
    </div>

    <!-- Main content -->
    <div class="ci-body" v-else>

      <!-- === PROGRESS === -->
      <div class="ci-section" v-if="activeTask">
        <div class="ci-section-header">
          <span class="ci-section-icon">▶</span>
          Progress
        </div>
        <div class="ci-steps">
          <div
            v-for="step in progressSteps"
            :key="step.id"
            class="ci-step"
            :class="{
              'ci-step--done': step.done,
              'ci-step--active': step.active,
              'ci-step--pending': !step.done && !step.active,
            }"
          >
            <div class="ci-step-dot">
              <span v-if="step.done">✓</span>
              <span v-else-if="step.active" class="ci-step-pulse">●</span>
              <span v-else class="ci-step-empty">○</span>
            </div>
            <span class="ci-step-label">{{ step.label }}</span>
          </div>
        </div>
        <div class="ci-status-chip" v-if="activeTask.current_step">
          {{ activeTask.current_step }}
        </div>
        <div class="ci-error-chip" v-if="activeTask.error">
          {{ activeTask.error }}
        </div>
      </div>

      <!-- === WORKSPACE === -->
      <div class="ci-section" v-if="wsInfo">
        <div class="ci-section-header">
          <span class="ci-section-icon">⊞</span>
          Workspace
        </div>
        <div class="ci-kv-row">
          <span class="ci-kv-key">Name</span>
          <span class="ci-kv-val">{{ wsInfo.name }}</span>
        </div>
        <div class="ci-kv-row" v-if="wsInfo.git_branch">
          <span class="ci-kv-key">Branch</span>
          <code class="ci-kv-branch">{{ wsInfo.git_branch }}</code>
        </div>
        <div class="ci-kv-row" v-if="wsInfo.default_mode">
          <span class="ci-kv-key">Mode</span>
          <span class="ci-kv-mode">{{ wsInfo.default_mode }}</span>
        </div>
        <div class="ci-kv-row" v-if="wsInfo.root">
          <span class="ci-kv-key">Root</span>
          <span class="ci-kv-path">{{ wsInfo.root }}</span>
        </div>
        <div class="ci-health-line" :class="`health--${wsHealthStatus}`">
          <span>●</span>
          {{ wsHealthLabel }}
        </div>
        <div class="ci-error-chip" v-if="wsInfo.health_error && wsHealthStatus !== 'ok'">
          {{ wsInfo.health_error }}
        </div>
      </div>

      <!-- === FILES (from code_edit) === -->
      <div class="ci-section" v-if="changedFiles.length">
        <div class="ci-section-header">
          <span class="ci-section-icon">◫</span>
          Files
        </div>
        <div
          v-for="f in changedFiles"
          :key="f.path"
          class="ci-file-row"
        >
          <span class="ci-file-badge" :class="`ci-file-badge--${f.type}`">{{ f.type === 'blocked' ? '✕' : 'M' }}</span>
          <span class="ci-file-path">{{ f.path }}</span>
        </div>
      </div>

      <!-- === CONTEXT === -->
      <div class="ci-section" v-if="activeTask?.attachments_count > 0 || activeTask?.rag_results_count > 0">
        <div class="ci-section-header">
          <span class="ci-section-icon">◎</span>
          Context
        </div>
        <div class="ci-ctx-row" v-if="activeTask.attachments_count">
          <span class="ci-ctx-icon">📎</span>
          <span>{{ activeTask.attachments_count }} attachments</span>
        </div>
        <div class="ci-ctx-row" v-if="activeTask.rag_results_count">
          <span class="ci-ctx-icon">📚</span>
          <span>{{ activeTask.rag_results_count }} RAG results</span>
        </div>
        <div class="ci-ctx-row ci-ctx-path" v-if="activeTask.rag_top_path">
          <span class="ci-ctx-icon">↳</span>
          <span>{{ activeTask.rag_top_path }}</span>
        </div>
      </div>

      <!-- === ARTIFACTS === -->
      <div class="ci-section" v-if="hasArtifacts">
        <div class="ci-section-header">
          <span class="ci-section-icon">◆</span>
          Artifacts
        </div>
        <div class="ci-artifact" v-if="activeTask.agent_prompt_path">
          <span class="ci-artifact-icon">📝</span>
          <span class="ci-artifact-label">Prompt</span>
          <span class="ci-artifact-path">{{ basename(activeTask.agent_prompt_path) }}</span>
        </div>
        <div class="ci-artifact" v-if="activeTask.report_path">
          <span class="ci-artifact-icon">📊</span>
          <span class="ci-artifact-label">Report</span>
          <span class="ci-artifact-path">{{ basename(activeTask.report_path) }}</span>
        </div>
        <div class="ci-artifact" v-if="activeTask.code_edit?.patch_path">
          <span class="ci-artifact-icon">📄</span>
          <span class="ci-artifact-label">Patch</span>
          <span class="ci-artifact-path">{{ basename(activeTask.code_edit.patch_path) }}</span>
        </div>
        <div class="ci-artifact" v-if="activeTask.final_report">
          <span class="ci-artifact-icon">✅</span>
          <span class="ci-artifact-label">Report</span>
          <span class="ci-artifact-path">{{ activeTask.report_source || 'manual' }}</span>
        </div>
      </div>

      <!-- === DEBUG INFO (collapsible) === -->
      <div class="ci-section ci-section--dev" v-if="showDevInfo && activeTask?.task_id">
        <div class="ci-section-header">
          <span class="ci-section-icon">⚙</span>
          Debug Info
        </div>
        <div class="ci-dev-row" v-if="activeTask.task_id">
          <span class="ci-dev-key">task_id</span>
          <code class="ci-dev-val">{{ activeTask.task_id?.slice(0,12) }}…</code>
        </div>
        <div class="ci-dev-row" v-if="activeTask.agent_run_id">
          <span class="ci-dev-key">run_id</span>
          <code class="ci-dev-val">{{ activeTask.agent_run_id?.slice(0,12) }}…</code>
        </div>
        <div class="ci-dev-row" v-if="activeTask.agent_run_mode">
          <span class="ci-dev-key">runner</span>
          <code class="ci-dev-val">{{ activeTask.agent_run_mode }}</code>
        </div>
        <div class="ci-dev-row" v-if="activeTask.hermes_http_status">
          <span class="ci-dev-key">http</span>
          <code class="ci-dev-val">{{ activeTask.hermes_http_status }}</code>
        </div>
        <div class="ci-dev-row" v-if="activeTask.fallback_reason">
          <span class="ci-dev-key">fallback</span>
          <code class="ci-dev-val">{{ activeTask.fallback_reason }}</code>
        </div>
        <div class="ci-dev-row" v-if="activeTask.hermes_endpoint">
          <span class="ci-dev-key">endpoint</span>
          <code class="ci-dev-val">{{ activeTask.hermes_endpoint }}</code>
        </div>
      </div>

      <!-- Debug toggle -->
      <button class="ci-dev-toggle" @click="showDevInfo = !showDevInfo" v-if="activeTask?.task_id">
        {{ showDevInfo ? '▲ Hide debug' : '▼ Debug info' }}
      </button>
    </div>
  </aside>
</template>

<script setup>
const props = defineProps({
  activeTask: { type: Object, default: null },
  wsInfo: { type: Object, default: null },
  closeable: { type: Boolean, default: false },
})
defineEmits(['close'])

const showDevInfo = ref(false)

// Normalize health: handles both health='ok' (string) and healthy=true (bool from /workspace/health)
const wsHealthStatus = computed(() => {
  const ws = props.wsInfo
  if (!ws) return 'unknown'
  if (ws.health === 'ok' || ws.healthy === true) return 'ok'
  if (ws.health === 'warning') return 'warning'
  if (ws.health === 'error' || ws.healthy === false) return 'error'
  return 'unknown'
})

const wsHealthLabel = computed(() => ({
  ok: 'Healthy',
  warning: 'Warning',
  error: 'Failed',
  unknown: 'Status unknown',
})[wsHealthStatus.value] ?? 'Status unknown')

const STEP_ORDER = ['plan', 'patch', 'apply', 'verify', 'commit']
const STATUS_TO_STEP = {
  pending: 0, running: 0,
  exporting: 1, exported: 2,
  agent_running: 2,
  completed: 5,
  failed: -1, blocked: -1, waiting_approval: -1,
}
const STEP_LABELS = { plan: 'Plan', patch: 'Patch', apply: 'Apply', verify: 'Verify', commit: 'Commit' }

const progressSteps = computed(() => {
  const status = props.activeTask?.status || ''
  const currentIdx = STATUS_TO_STEP[status] ?? -1
  return STEP_ORDER.map((id, i) => ({
    id,
    label: STEP_LABELS[id],
    done: status === 'completed' ? true : i < currentIdx,
    active: i === currentIdx,
  }))
})

const changedFiles = computed(() => {
  const ce = props.activeTask?.code_edit
  if (!ce) return []
  const files = (ce.files_to_change || []).map(p => ({ path: p, type: 'changed' }))
  const blocked = (ce.blocked_paths || []).map(p => ({ path: p, type: 'blocked' }))
  return [...files, ...blocked]
})

const hasArtifacts = computed(() => {
  const t = props.activeTask
  return t && (t.agent_prompt_path || t.report_path || t.code_edit?.patch_path || t.final_report)
})

function basename(path) {
  if (!path) return ''
  return path.split('/').pop() || path
}
</script>

<style scoped>
.cw-inspector {
  width: 320px;
  min-width: 320px;
  height: 100%;
  background: #0a1020;
  border-left: 1px solid #1e293b;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}

/* Header */
.ci-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px 13px;
  border-bottom: 1px solid #1a2640;
  flex-shrink: 0;
}
.ci-title {
  font-size: 0.68rem;
  font-weight: 700;
  color: #334155;
  text-transform: uppercase;
  letter-spacing: 0.09em;
}
.ci-close-btn {
  background: none; border: none; color: #334155;
  cursor: pointer; font-size: 0.82rem; padding: 2px;
}

/* Empty state */
.ci-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 2rem;
}
.ci-empty-icon { font-size: 1.8rem; opacity: 0.2; color: #60a5fa; }
.ci-empty-title { font-size: 0.82rem; font-weight: 600; color: #334155; text-align: center; }
.ci-empty-sub { font-size: 0.7rem; color: #1e293b; text-align: center; line-height: 1.6; }

/* Body */
.ci-body {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0 12px;
}
.ci-body::-webkit-scrollbar { width: 3px; }
.ci-body::-webkit-scrollbar-track { background: transparent; }
.ci-body::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }

/* Sections */
.ci-section {
  padding: 10px 14px;
  border-bottom: 1px solid #0f172a;
}
.ci-section--dev { opacity: 0.7; }
.ci-section-header {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.62rem;
  font-weight: 700;
  color: #334155;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  margin-bottom: 8px;
}
.ci-section-icon { font-size: 0.72rem; }

/* Progress steps */
.ci-steps { display: flex; flex-direction: column; gap: 5px; margin-bottom: 8px; }
.ci-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.74rem;
}
.ci-step-dot {
  width: 18px;
  text-align: center;
  font-size: 0.72rem;
  flex-shrink: 0;
}
.ci-step--done .ci-step-dot  { color: #22c55e; }
.ci-step--active .ci-step-dot { color: #60a5fa; }
.ci-step--pending .ci-step-dot { color: #1e293b; }
.ci-step--done .ci-step-label  { color: #4ade80; }
.ci-step--active .ci-step-label { color: #60a5fa; font-weight: 600; }
.ci-step--pending .ci-step-label { color: #334155; }
.ci-step-pulse { animation: ci-pulse 1.4s infinite; }
@keyframes ci-pulse { 0%,100%{opacity:1;} 50%{opacity:0.2;} }
.ci-step-empty { color: #1e293b; }

.ci-status-chip {
  font-size: 0.7rem;
  color: #64748b;
  line-height: 1.5;
  padding: 4px 6px;
  background: #0c1830;
  border-radius: 5px;
  margin-top: 4px;
}
.ci-error-chip {
  font-size: 0.7rem;
  color: #fca5a5;
  background: #450a0a;
  padding: 4px 6px;
  border-radius: 5px;
  margin-top: 4px;
  line-height: 1.4;
  word-break: break-word;
}

/* KV rows (Workspace) */
.ci-kv-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 4px;
  min-width: 0;
}
.ci-kv-key {
  font-size: 0.63rem;
  font-weight: 600;
  color: #334155;
  min-width: 46px;
  flex-shrink: 0;
}
.ci-kv-val { font-size: 0.74rem; color: #94a3b8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ci-kv-branch {
  font-size: 0.62rem;
  background: #064e3b;
  color: #6ee7b7;
  padding: 1px 5px;
  border-radius: 3px;
  font-family: monospace;
}
.ci-kv-mode {
  font-size: 0.62rem;
  background: #1e1b4b;
  color: #a78bfa;
  padding: 1px 5px;
  border-radius: 3px;
}
.ci-kv-path {
  font-size: 0.6rem;
  color: #475569;
  font-family: monospace;
  word-break: break-all;
  line-height: 1.4;
}
.ci-health-line {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.68rem;
  font-weight: 600;
  margin-top: 6px;
}
.health--ok      { color: #22c55e; }
.health--warning { color: #f59e0b; }
.health--warn    { color: #f59e0b; }
.health--error   { color: #f87171; }
.health--unknown { color: #475569; }

/* Files */
.ci-file-row {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 3px 0;
}
.ci-file-badge {
  font-size: 0.58rem;
  font-weight: 700;
  padding: 0 4px;
  border-radius: 3px;
  font-family: monospace;
  flex-shrink: 0;
}
.ci-file-badge--changed { background: #422006; color: #f59e0b; }
.ci-file-badge--blocked { background: #450a0a; color: #f87171; }
.ci-file-path {
  font-size: 0.66rem;
  color: #94a3b8;
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Context */
.ci-ctx-row {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 0.72rem;
  color: #64748b;
  padding: 2px 0;
}
.ci-ctx-icon { font-size: 0.78rem; width: 16px; text-align: center; flex-shrink: 0; }
.ci-ctx-path { font-size: 0.62rem; font-family: monospace; word-break: break-all; }

/* Artifacts */
.ci-artifact {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 6px;
  border-radius: 5px;
  margin-bottom: 2px;
  background: #0c1830;
  cursor: default;
}
.ci-artifact-icon { font-size: 0.78rem; flex-shrink: 0; }
.ci-artifact-label {
  font-size: 0.64rem;
  font-weight: 600;
  color: #475569;
  min-width: 40px;
  flex-shrink: 0;
}
.ci-artifact-path {
  font-size: 0.62rem;
  color: #94a3b8;
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Dev info */
.ci-dev-row {
  display: flex;
  align-items: baseline;
  gap: 7px;
  margin-bottom: 3px;
}
.ci-dev-key {
  font-size: 0.6rem;
  color: #334155;
  font-family: monospace;
  min-width: 54px;
  flex-shrink: 0;
}
.ci-dev-val {
  font-size: 0.6rem;
  color: #475569;
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ci-dev-toggle {
  display: block;
  width: 100%;
  text-align: center;
  padding: 8px 14px;
  background: transparent;
  border: none;
  font-size: 0.62rem;
  color: #1e293b;
  cursor: pointer;
  font-family: inherit;
}
.ci-dev-toggle:hover { color: #334155; }
</style>
