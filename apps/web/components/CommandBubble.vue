<template>
  <div class="bubble-row" :class="msg.role">
    <div class="bubble" :class="msg.role">
      <span v-if="msg.role === 'system'" class="dot" :class="dotClass"></span>
      <div class="bubble-body">
        <pre class="bubble-text">{{ msg.text }}</pre>

        <!-- Task progress block -->
        <div v-if="isTask" class="task-block">
          <!-- ID + Status badge -->
          <div class="task-row">
            <code class="task-id-code">{{ shortId(meta.task_id) }}</code>
            <span class="task-badge" :class="`badge-${meta.status}`">{{ statusLabel(meta.status) }}</span>
          </div>

          <!-- Agent Activity -->
          <div class="agent-activity" v-if="activeAgent">
            <div class="aa-row">
              <span class="aa-dot" :class="`fill-${meta.status}`"></span>
              <span class="aa-active">{{ agentIcon(activeAgent) }} {{ activeAgent }}</span>
              <span class="aa-sep" v-if="meta.speaker_agent && meta.speaker_agent !== activeAgent">
                · 🧭 {{ meta.speaker_agent }}
              </span>
            </div>
            <div class="aa-chips" v-if="meta.active_agents?.length > 1">
              <span v-for="a in meta.active_agents" :key="a" class="aa-chip">{{ agentIcon(a) }} {{ a }}</span>
            </div>
          </div>

          <!-- Agent Running instruction -->
          <div class="agent-running-info" v-if="meta.status === 'agent_running'">
            💬 Prompt พร้อมแล้ว — กรุณา <strong>Copy Prompt</strong> ไปให้ Claude/Hermes ประมวลผล
          </div>

          <!-- Attachment list (always visible if non-zero) -->
          <div class="attach-list" v-if="meta.attachments_count > 0">
            <div class="attach-list-header">📎 {{ meta.attachments_count }} ไฟล์แนบ</div>
            <div
              v-for="(f, i) in (meta.attachments || [])"
              :key="i"
              class="attach-row"
            >
              <span class="attach-fname">{{ f.filename || f.safe_filename }}</span>
              <span class="attach-mode" :class="`mode-${classifyMode(f.filename || f.safe_filename || '')}`">
                {{ classifyMode(f.filename || f.safe_filename || '') }}
              </span>
            </div>
          </div>

          <!-- Current step -->
          <div class="task-step">{{ meta.current_step }}</div>

          <!-- Progress bar -->
          <div class="progress-track">
            <div
              class="progress-fill"
              :class="`fill-${meta.status}`"
              :style="{ width: `${meta.progress ?? 0}%` }"
            ></div>
          </div>
          <div class="progress-pct">{{ meta.progress ?? 0 }}%</div>

          <!-- Exported / agent_running details -->
          <template v-if="meta.status === 'exported' || meta.status === 'agent_running'">
            <div class="task-detail" v-if="meta.agents?.length">
              <span class="dl">Agents:</span> {{ meta.agents.join(', ') }}
            </div>
            <div class="task-detail" v-if="meta.skills?.length">
              <span class="dl">Skills:</span> {{ meta.skills.join(', ') }}
            </div>
            <!-- RAG Wiki badge -->
            <div class="task-detail rag-info" v-if="meta.rag_results_count > 0">
              <span class="rag-badge">📚 LLM Wiki</span>
              <span class="rag-count">{{ meta.rag_results_count }} results</span>
              <span class="rag-path" v-if="meta.rag_top_path">· {{ meta.rag_top_path }}</span>
            </div>
            <!-- Agent Runner badge -->
            <div class="task-detail agent-runner-info" v-if="meta.agent_run_id">
              <span class="agent-runner-badge">🤖 Agent Runner</span>
              <span class="agent-runner-mode" v-if="meta.agent_run_mode">{{ meta.agent_run_mode }}</span>
              <span class="agent-runner-status" :class="`ar-${meta.agent_run_status}`" v-if="meta.agent_run_status">{{ meta.agent_run_status }}</span>
            </div>
            <div class="task-detail attach-info" v-if="meta.attachments_count > 0">
              <span class="dl">Files:</span> 📎 {{ meta.attachments_count }} ไฟล์แนบ
            </div>
            <div class="task-detail" v-if="meta.export_path">
              <span class="dl">Prompt:</span>
              <code>{{ shortPath(meta.export_path) }}</code>
            </div>
          </template>

          <!-- Completed details -->
          <template v-if="meta.status === 'completed'">
            <div class="report-meta-row">
              <span class="task-detail" v-if="meta.report_source">
                <span class="dl">Source:</span> {{ meta.report_source }}
              </span>
              <span v-if="meta.verification_status" class="verify-badge" :class="`vbadge-${meta.verification_status}`">
                {{ verifyIcon(meta.verification_status) }} {{ meta.verification_status?.toUpperCase() }}
              </span>
            </div>
            <div class="final-report-preview" v-if="meta.report_summary || meta.final_report">
              {{ meta.report_summary || meta.final_report?.slice(0, 150) }}
              {{ !meta.report_summary && (meta.final_report?.length ?? 0) > 150 ? '…' : '' }}
            </div>
          </template>

          <!-- Blocked / waiting approval -->
          <div class="task-blocked" v-if="isBlocked">
            ⚠️ ต้องยืนยันก่อนดำเนินการ<br>
            <code>{{ meta.approval_phrase }}</code>
          </div>

          <!-- Error -->
          <div class="task-error" v-if="meta.error">{{ meta.error }}</div>

          <!-- Actions -->
          <div class="task-actions">
            <!-- exported: View Prompt + Run Agent -->
            <button
              v-if="meta.status === 'exported'"
              class="btn-view-prompt"
              @click="$emit('viewPrompt', meta.task_id)"
            >📄 View Prompt</button>

            <button
              v-if="meta.status === 'exported'"
              class="btn-run-agent"
              @click="$emit('runAgent', { taskId: meta.task_id, bubbleId: msg.id })"
            >▶ Run Agent</button>

            <!-- agent_running: View Prompt + Save Report -->
            <button
              v-if="meta.status === 'agent_running'"
              class="btn-view-prompt"
              @click="$emit('viewPrompt', meta.task_id)"
            >📄 View Prompt</button>

            <button
              v-if="meta.status === 'agent_running'"
              class="btn-save-report"
              @click="$emit('saveReport', { taskId: meta.task_id, bubbleId: msg.id })"
            >💾 Save Report</button>

            <!-- Agent Runner: Copy Prompt + Save Agent Report -->
            <button
              v-if="meta.agent_run_id && meta.agent_run_status === 'completed_prompt_ready'"
              class="btn-copy-agent-prompt"
              @click="$emit('copyAgentPrompt', { runId: meta.agent_run_id })"
            >📋 Copy Agent Prompt</button>

            <button
              v-if="meta.agent_run_id && meta.agent_run_status === 'completed_prompt_ready'"
              class="btn-save-agent-report"
              @click="$emit('saveAgentReport', { taskId: meta.task_id, runId: meta.agent_run_id, bubbleId: msg.id })"
            >📝 Save Agent Report</button>

            <!-- completed: View Report + Timeline + View Prompt -->
            <button
              v-if="meta.status === 'completed'"
              class="btn-view-report"
              @click="$emit('viewReport', { taskId: meta.task_id, bubbleId: msg.id })"
            >📊 View Report</button>

            <button
              v-if="meta.status === 'completed' && meta.agent_events?.length"
              class="btn-timeline"
              @click="$emit('viewTimeline', { taskId: meta.task_id, events: meta.agent_events })"
            >🕐 Timeline</button>

            <button
              v-if="meta.status === 'completed'"
              class="btn-view-prompt"
              @click="$emit('viewPrompt', meta.task_id)"
            >📄 View Prompt</button>

            <a class="jobs-link" href="/jobs">ดู Jobs →</a>
          </div>
        </div>

        <!-- Legacy: non-task bubbles that still carry task_id -->
        <div class="bubble-meta" v-else-if="msg.meta?.task_id">
          <a class="jobs-link" href="/jobs">ดูใน Jobs →</a>
        </div>
      </div>
    </div>
    <div class="bubble-time">{{ fmtTime(msg.createdAt) }}</div>
  </div>
</template>

<script setup>
const props = defineProps({
  msg: { type: Object, required: true },
})
defineEmits(['viewPrompt', 'runAgent', 'saveReport', 'viewReport', 'viewTimeline', 'copyAgentPrompt', 'saveAgentReport'])

const AGENT_ICONS = {
  'manager': '🧭', 'programmer': '💻', 'devops': '🐳',
  'administrator': '🛡', 'designer': '🎨', 'qa': '🧪',
  'security': '🔐', 'rag-curator': '📚', 'observer': '👁',
  'research': '🔬', 'worker': '⚙️',
}
const agentIcon  = (a) => AGENT_ICONS[a] || '🤖'
const verifyIcon = (v) => ({ pass: '✅', warning: '⚠️', fail: '❌' }[v] || '')

const STATUS_LABELS = {
  pending: 'PENDING', running: 'RUNNING', exporting: 'EXPORTING',
  exported: 'PROMPT READY', agent_running: 'AGENT RUNNING',
  completed: 'COMPLETED', failed: 'FAILED',
  blocked: 'BLOCKED', waiting_approval: 'WAIT APPROVAL',
}
const statusLabel = (s) => STATUS_LABELS[s] || (s || '').toUpperCase()

const meta      = computed(() => props.msg.meta || {})
const isTask    = computed(() => meta.value.type === 'task')
const isBlocked = computed(() =>
  meta.value.status === 'blocked' || meta.value.status === 'waiting_approval'
)
const activeAgent = computed(() =>
  meta.value.current_agent || (meta.value.agents?.[0] ?? null)
)

const dotClass = computed(() => {
  if (!isTask.value) return ''
  const s = meta.value.status
  if (s === 'exported' || s === 'completed') return 'dot-green'
  if (s === 'failed')        return 'dot-red'
  if (isBlocked.value)       return 'dot-yellow'
  if (s === 'agent_running') return 'dot-orange'
  return 'dot-blue'
})

const _MODES = {
  txt: 'text-extract', md: 'text-extract', log: 'text-extract',
  json: 'text-extract', yaml: 'text-extract', yml: 'text-extract', csv: 'text-extract',
  pdf: 'document-extract', doc: 'document-extract', docx: 'document-extract',
  xls: 'spreadsheet-extract', xlsx: 'spreadsheet-extract',
  ppt: 'presentation-extract', pptx: 'presentation-extract',
  jpg: 'vision-required', jpeg: 'vision-required', png: 'vision-required',
  webp: 'vision-required', gif: 'vision-required',
}
const classifyMode = (fn) => {
  const ext = (fn || '').split('.').pop()?.toLowerCase() || ''
  return _MODES[ext] || 'unsupported'
}

const shortId   = (id) => id ? id.slice(0, 8) + '…' : '—'
const shortPath = (p)  => p  ? p.replace('/app/data/exports/', '') : p
const fmtTime   = (ts) => {
  try { return new Date(ts).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' }) }
  catch { return '' }
}
</script>

<style scoped>
.bubble-row { display: flex; flex-direction: column; margin-bottom: 12px; }
.bubble-row.user   { align-items: flex-end; }
.bubble-row.system { align-items: flex-start; }

.bubble {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  max-width: 88%;
  padding: 12px 15px;
  border-radius: 16px;
  word-break: break-word;
}
.bubble.system {
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  border-bottom-left-radius: 4px;
}
.bubble.user {
  background: #1d6fe8;
  color: #fff;
  border-bottom-right-radius: 4px;
  flex-direction: row-reverse;
}

/* Dot */
.dot {
  flex-shrink: 0;
  width: 10px; height: 10px;
  border-radius: 50%;
  background: #22c55e;
  margin-top: 4px;
}
.dot-green  { background: #22c55e; }
.dot-blue   { background: #3b82f6; animation: pulse 1.4s infinite; }
.dot-orange { background: #f97316; animation: pulse 1.4s infinite; }
.dot-red    { background: #ef4444; }
.dot-yellow { background: #f59e0b; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}

.bubble-body { flex: 1; min-width: 0; }

.bubble-text {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 15px;
  line-height: 1.55;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
.bubble.user   .bubble-text { color: #fff; }
.bubble.system .bubble-text { color: #1a1a2e; }

/* ── Task block ── */
.task-block {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #e5e7eb;
  font-size: 0.82rem;
  color: #374151;
}

.task-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.task-id-code {
  font-family: monospace;
  font-size: 0.75rem;
  color: #6b7280;
  background: #f3f4f6;
  padding: 1px 5px;
  border-radius: 4px;
}

/* Status badge */
.task-badge {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.badge-pending          { background: #e5e7eb; color: #6b7280; }
.badge-running          { background: #dbeafe; color: #1d4ed8; }
.badge-exporting        { background: #ede9fe; color: #7c3aed; }
.badge-exported         { background: #dcfce7; color: #15803d; }
.badge-agent_running    { background: #ffedd5; color: #c2410c; }
.badge-completed        { background: #d1fae5; color: #065f46; }
.badge-failed           { background: #fee2e2; color: #b91c1c; }
.badge-blocked,
.badge-waiting_approval { background: #fef3c7; color: #b45309; }

/* Agent activity */
.agent-activity {
  margin-bottom: 6px;
  padding: 5px 8px;
  background: #f9fafb;
  border-radius: 6px;
  border-left: 2px solid #dbeafe;
}
.aa-row { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
.aa-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.aa-active  { font-size: 0.8rem; font-weight: 600; color: #1e40af; }
.aa-sep     { font-size: 0.75rem; color: #6b7280; }
.aa-chips   { display: flex; flex-wrap: wrap; gap: 3px; margin-top: 4px; }
.aa-chip    { font-size: 0.67rem; padding: 1px 6px; background: #eff6ff; color: #1d4ed8; border-radius: 999px; }

/* Agent running info */
.agent-running-info {
  font-size: 0.8rem;
  color: #92400e;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 6px;
  padding: 6px 10px;
  margin-bottom: 6px;
}

.attach-list {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 5px 8px;
  margin-bottom: 6px;
  font-size: 0.72rem;
}
.attach-list-header {
  font-weight: 700;
  color: #1d4ed8;
  margin-bottom: 3px;
}
.attach-row {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 1px 0;
}
.attach-fname {
  color: #374151;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.attach-mode {
  font-size: 0.65rem;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 4px;
  white-space: nowrap;
}
.mode-text-extract       { background: #d1fae5; color: #065f46; }
.mode-document-extract   { background: #dbeafe; color: #1d4ed8; }
.mode-spreadsheet-extract{ background: #ede9fe; color: #5b21b6; }
.mode-presentation-extract{ background: #fef3c7; color: #b45309; }
.mode-vision-required    { background: #fce7f3; color: #be185d; }
.mode-unsupported        { background: #f3f4f6; color: #9ca3af; }
.attach-info { color: #1d4ed8; }

.task-step {
  font-size: 0.8rem;
  color: #6b7280;
  margin-bottom: 6px;
}

/* Progress bar */
.progress-track {
  width: 100%;
  height: 6px;
  background: #e5e7eb;
  border-radius: 999px;
  overflow: hidden;
  margin-bottom: 3px;
}
.progress-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s ease;
}
.fill-pending          { background: #9ca3af; }
.fill-running          { background: #3b82f6; }
.fill-exporting        { background: #8b5cf6; }
.fill-exported         { background: #22c55e; }
.fill-agent_running    { background: #f97316; }
.fill-completed        { background: #059669; }
.fill-failed           { background: #ef4444; }
.fill-blocked,
.fill-waiting_approval { background: #f59e0b; }

.progress-pct { font-size: 0.72rem; color: #9ca3af; margin-bottom: 8px; }

/* Details */
.task-detail { font-size: 0.78rem; color: #374151; margin-bottom: 3px; word-break: break-all; }
.task-detail code { font-family: monospace; color: #065f46; font-size: 0.75rem; }
.dl { font-weight: 600; color: #6b7280; }

.rag-info { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
.rag-badge {
  font-size: 0.67rem; font-weight: 700;
  background: #dbeafe; color: #1d4ed8;
  padding: 1px 6px; border-radius: 999px;
}
.rag-count { font-size: 0.72rem; color: #1d4ed8; font-weight: 600; }
.rag-path  { font-size: 0.68rem; color: #6b7280; font-family: monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px; }

.agent-runner-info { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
.agent-runner-badge {
  font-size: 0.67rem; font-weight: 700;
  background: #ede9fe; color: #6d28d9;
  padding: 1px 6px; border-radius: 999px;
}
.agent-runner-mode { font-size: 0.68rem; color: #7c3aed; font-family: monospace; }
.agent-runner-status { font-size: 0.68rem; font-weight: 600; padding: 1px 5px; border-radius: 4px; }
.ar-completed_prompt_ready  { background: #d1fae5; color: #065f46; }
.ar-completed_report_saved  { background: #bbf7d0; color: #14532d; font-weight: 700; }
.ar-waiting_for_hermes_manual_execution { background: #fef3c7; color: #92400e; }
.ar-completed { background: #d1fae5; color: #065f46; }
.ar-failed    { background: #fee2e2; color: #991b1b; }
.ar-running   { background: #dbeafe; color: #1e40af; }

.report-meta-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 4px; }
.verify-badge {
  font-size: 0.65rem; font-weight: 700;
  padding: 2px 6px; border-radius: 999px;
  text-transform: uppercase; letter-spacing: 0.04em;
}
.vbadge-pass    { background: #dcfce7; color: #15803d; }
.vbadge-warning { background: #fef3c7; color: #b45309; }
.vbadge-fail    { background: #fee2e2; color: #b91c1c; }

.final-report-preview {
  font-size: 0.78rem;
  color: #374151;
  background: #f0fdf4;
  border-left: 2px solid #22c55e;
  padding: 6px 8px;
  border-radius: 0 6px 6px 0;
  margin: 4px 0 6px;
  line-height: 1.5;
  word-break: break-word;
}

.task-blocked {
  font-size: 0.8rem;
  color: #92400e;
  background: #fef3c7;
  border-radius: 6px;
  padding: 6px 8px;
  margin: 6px 0;
  line-height: 1.5;
}
.task-blocked code { font-weight: 700; }

.task-error {
  font-size: 0.78rem;
  color: #b91c1c;
  background: #fee2e2;
  border-radius: 6px;
  padding: 5px 8px;
  margin: 6px 0;
}

/* Actions */
.task-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.btn-view-prompt, .btn-run-agent, .btn-save-report, .btn-view-report, .btn-timeline,
.btn-copy-agent-prompt, .btn-save-agent-report {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
}
.btn-view-prompt:hover, .btn-run-agent:hover, .btn-save-report:hover, .btn-view-report:hover, .btn-timeline:hover,
.btn-copy-agent-prompt:hover, .btn-save-agent-report:hover { opacity: 0.85; }

.btn-view-prompt  { background: #0f766e; color: #fff; }
.btn-run-agent    { background: #1d4ed8; color: #fff; }
.btn-save-report  { background: #c2410c; color: #fff; }
.btn-view-report  { background: #065f46; color: #fff; }
.btn-timeline            { background: #1e3a5f; color: #93c5fd; }
.btn-copy-agent-prompt   { background: #4c1d95; color: #e9d5ff; }
.btn-save-agent-report   { background: #6d28d9; color: #fff; }

.jobs-link {
  font-size: 0.75rem;
  color: #1d6fe8;
  text-decoration: none;
  font-weight: 600;
}
.jobs-link:hover { text-decoration: underline; }

.bubble-meta { margin-top: 6px; }

.bubble-time {
  font-size: 0.65rem;
  color: #9ca3af;
  margin-top: 3px;
  padding: 0 4px;
}
</style>
