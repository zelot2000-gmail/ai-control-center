<template>
  <div class="bubble-row" :class="msg.role">
    <div class="bubble" :class="msg.role">
      <span v-if="msg.role === 'system'" class="dot" :class="dotClass"></span>
      <div class="bubble-body">
        <pre class="bubble-text">{{ msg.text }}</pre>

        <!-- ── Task Console Panel ── -->
        <div v-if="isTask" class="task-panel">

          <!-- Friendly status sentence (replaces technical badge in default view) -->
          <div class="tp-friendly">
            <span class="tp-friendly-text">{{ friendlyStatusText }}</span>
            <span class="tp-badge tp-badge-small" :class="`tbadge-${meta.status}`">{{ statusLabel(meta.status) }}</span>
          </div>
          <div class="tp-progress-track">
            <div class="tp-progress-fill" :class="`tpf-${meta.status}`" :style="{width:`${meta.progress ?? 0}%`}"></div>
          </div>

          <!-- Agent Activity row -->
          <div class="tp-agent-activity" v-if="activeAgent">
            <span class="taa-dot" :class="`taad-${meta.status}`"></span>
            <span class="taa-name">{{ agentIcon(activeAgent) }} {{ activeAgent }}</span>
            <span class="taa-sep" v-if="meta.speaker_agent && meta.speaker_agent !== activeAgent">→ 🧭 {{ meta.speaker_agent }}</span>
            <div class="taa-chips" v-if="meta.active_agents?.length > 1">
              <span v-for="a in meta.active_agents" :key="a" class="taa-chip">{{ agentIcon(a) }} {{ a }}</span>
            </div>
          </div>

          <!-- RAG hint in friendly Thai (kept visible — useful context for user) -->
          <div class="tp-rag-hint" v-if="meta.rag_results_count > 0">
            📚 พบข้อมูลอ้างอิงที่เกี่ยวข้อง {{ meta.rag_results_count }} รายการ
          </div>

          <!-- ── SECTION: SELF-MODIFY CODE EDIT ── -->
          <div class="tp-section sec-code-edit" v-if="meta.code_edit">
            <div class="sec-label">🛠 แก้ไขโค้ดของระบบ</div>
            <div class="sec-body">
              <!-- planning -->
              <div v-if="meta.code_edit.status === 'planning'" class="ce-line">
                {{ meta.code_edit.message || 'กำลังให้ AI วางแผนการแก้ไข...' }}
              </div>

              <!-- patch proposed -->
              <template v-else-if="meta.code_edit.status === 'patch_proposed'">
                <div class="ce-line">
                  ผมเตรียม patch ให้แล้ว
                  <span v-if="meta.code_edit.files_to_change?.length">
                    — จะแก้ {{ meta.code_edit.files_to_change.length }} ไฟล์
                  </span>
                </div>
                <ul class="ce-files" v-if="meta.code_edit.files_to_change?.length">
                  <li v-for="f in meta.code_edit.files_to_change" :key="f">{{ f }}</li>
                </ul>
                <div class="ce-risk" :class="`ce-risk-${meta.code_edit.risk_level}`">
                  ระดับความเสี่ยง: {{ meta.code_edit.risk_level }} / 5
                  <span v-if="meta.code_edit.required_apply_phrase">
                    — ต้องพิมพ์ <code>{{ meta.code_edit.required_apply_phrase }}</code> ก่อน Apply
                  </span>
                </div>
              </template>

              <!-- blocked -->
              <div v-else-if="meta.code_edit.status === 'blocked'" class="ce-blocked">
                ⛔ {{ meta.code_edit.blocked_reason || meta.code_edit.message || 'ถูก block โดย policy' }}
                <ul v-if="meta.code_edit.blocked_paths?.length" class="ce-files">
                  <li v-for="f in meta.code_edit.blocked_paths" :key="f">{{ f }}</li>
                </ul>
              </div>

              <!-- error / no diff -->
              <div v-else-if="meta.code_edit.patch_source === 'none'" class="ce-blocked">
                ⚠️ {{ meta.code_edit.message || 'AI ยังตอบ patch ที่ใช้ได้ไม่ได้' }}
                <div v-if="meta.code_edit.provider_error" class="ce-err-detail">
                  {{ meta.code_edit.provider_error }}
                </div>
              </div>

              <!-- apply result -->
              <div v-if="meta.code_edit_apply" class="ce-apply">
                <div>
                  สถานะหลัง Apply:
                  <strong>{{ meta.code_edit_apply.status }}</strong>
                  <span v-if="meta.code_edit_apply.verification_status">
                    · ตรวจสอบ: {{ meta.code_edit_apply.verification_status }}
                  </span>
                </div>
                <pre class="ce-diff" v-if="meta.code_edit_apply.diff_summary">{{ meta.code_edit_apply.diff_summary }}</pre>
              </div>

              <!-- commit result -->
              <div v-if="meta.code_edit_commit" class="ce-apply">
                <div>
                  Commit: <strong>{{ meta.code_edit_commit.status }}</strong>
                  <code v-if="meta.code_edit_commit.commit_hash">{{ meta.code_edit_commit.commit_hash }}</code>
                  <span v-if="meta.code_edit_commit.branch">on {{ meta.code_edit_commit.branch }}</span>
                </div>
              </div>

              <!-- action buttons -->
              <div class="ce-actions">
                <button
                  v-if="meta.code_edit.status === 'patch_proposed' && !meta.code_edit_apply"
                  class="ce-btn ce-btn-view"
                  @click="$emit('viewCodeEditPatch', { taskId: meta.task_id })"
                >📄 View Patch</button>
                <button
                  v-if="meta.code_edit.status === 'patch_proposed' && !meta.code_edit_apply"
                  class="ce-btn ce-btn-apply"
                  @click="$emit('applyCodeEdit', { taskId: meta.task_id, bubbleId: msg.id })"
                >✏️ Apply Patch</button>
                <button
                  v-if="meta.code_edit_apply?.status === 'waiting_commit_approval'"
                  class="ce-btn ce-btn-commit"
                  @click="$emit('commitCodeEdit', { taskId: meta.task_id, bubbleId: msg.id })"
                >💾 Commit</button>
                <button
                  v-if="meta.code_edit_apply && meta.code_edit_commit?.status !== 'committed'"
                  class="ce-btn ce-btn-rollback"
                  @click="$emit('rollbackCodeEdit', { taskId: meta.task_id, bubbleId: msg.id })"
                >↩️ Rollback</button>
              </div>
            </div>
          </div>

          <!-- ── Technical details (collapsed by default) ── -->
          <details class="tech-details" v-if="hasTechnicalContent">
            <summary class="tech-summary">⚙️ ดูรายละเอียดทางเทคนิค</summary>
            <div class="tech-body">
              <div class="tech-row" v-if="meta.task_id">
                <span class="tech-key">Task ID</span>
                <code class="tech-val">{{ shortId(meta.task_id) }}</code>
              </div>
              <div class="tech-row" v-if="meta.agent_run_id">
                <span class="tech-key">Agent Run</span>
                <code class="tech-val">{{ meta.agent_run_id.slice(0,8) }}…</code>
              </div>
              <div class="tech-row" v-if="meta.agent_run_mode">
                <span class="tech-key">Runner Mode</span>
                <span class="tech-val">{{ meta.agent_run_mode }}</span>
              </div>
              <div class="tech-row" v-if="meta.agent_run_status">
                <span class="tech-key">Run Status</span>
                <span class="tech-val">{{ meta.agent_run_status }}</span>
              </div>
              <div class="tech-row" v-if="meta.hermes_http_status">
                <span class="tech-key">HTTP</span>
                <span class="tech-val" :class="meta.hermes_http_status === 200 ? 'tech-ok' : 'tech-err'">
                  {{ meta.hermes_http_status }}
                </span>
              </div>
              <div class="tech-row" v-if="meta.hermes_response_format">
                <span class="tech-key">Format</span>
                <span class="tech-val">{{ meta.hermes_response_format }}</span>
              </div>
              <div class="tech-row" v-if="meta.hermes_provider">
                <span class="tech-key">Provider</span>
                <span class="tech-val">{{ meta.hermes_provider }}</span>
              </div>
              <div class="tech-row" v-if="meta.fallback_mode">
                <span class="tech-key">Fallback</span>
                <span class="tech-val">{{ meta.fallback_mode }}</span>
              </div>
              <div class="tech-row" v-if="meta.fallback_reason">
                <span class="tech-key">Reason</span>
                <span class="tech-val tech-err">{{ meta.fallback_reason }}</span>
              </div>
              <div class="tech-row" v-if="meta.rag_top_path">
                <span class="tech-key">Top RAG</span>
                <code class="tech-val">{{ meta.rag_top_path }}</code>
              </div>
              <div class="tech-row" v-if="meta.agent_prompt_path">
                <span class="tech-key">Prompt</span>
                <code class="tech-val">{{ shortPath(meta.agent_prompt_path) }}</code>
              </div>
              <div class="tech-row" v-if="meta.report_path">
                <span class="tech-key">Report</span>
                <code class="tech-val">{{ shortPath(meta.report_path) }}</code>
              </div>
              <div class="tech-row" v-if="meta.response_received_at">
                <span class="tech-key">Received</span>
                <span class="tech-val">{{ fmtTime(meta.response_received_at) }}</span>
              </div>
              <div class="tech-row" v-if="meta.report_saved_at">
                <span class="tech-key">Saved</span>
                <span class="tech-val">{{ fmtTime(meta.report_saved_at) }}</span>
              </div>
              <a class="tech-link" :href="`/jobs`">เปิดในหน้า Jobs ↗</a>
            </div>
          </details>

          <!-- ── SECTION: APPROVAL REQUIRED — friendly + visible ── -->
          <div class="tp-section sec-approval"
               v-if="meta.agent_run_status === 'blocked_approval_required' || isBlocked">
            <div class="sec-label">⛔ ต้องยืนยันก่อนดำเนินการ</div>
            <div class="sec-body">
              <div class="ap-reason">{{ meta.agent_approval_reason || 'งานนี้เกี่ยวข้องกับสภาพแวดล้อม production ต้องยืนยันก่อนดำเนินการ' }}</div>
              <div class="ap-hint" v-if="meta.approval_phrase">
                พิมพ์วลียืนยัน: <code class="ap-phrase">{{ meta.approval_phrase }}</code>
              </div>
            </div>
          </div>

          <!-- ── SECTION: REPORT (completed) — final answer ── -->
          <div class="tp-section sec-report" v-if="meta.status === 'completed'">
            <div class="sec-label-row">
              <span class="sec-label">📊 รายงานผล</span>
              <span class="verify-badge" v-if="meta.verification_status"
                    :class="`vbadge-${meta.verification_status?.toLowerCase()}`">
                {{ verifyIcon(meta.verification_status) }} {{ verifyText(meta.verification_status) }}
              </span>
            </div>
            <div class="sec-body" v-if="meta.report_summary || meta.final_report">
              <div class="rp-preview">
                {{ meta.report_summary || meta.final_report?.slice(0, 140) }}{{ !meta.report_summary && (meta.final_report?.length ?? 0) > 140 ? '…' : '' }}
              </div>
            </div>
          </div>

          <!-- ── SECTION: ATTACHMENTS ── -->
          <div class="tp-section sec-attach" v-if="meta.attachments_count > 0">
            <div class="sec-label">📎 ATTACHMENTS ({{ meta.attachments_count }})</div>
            <div class="sec-body attach-grid">
              <div v-for="(f, i) in (meta.attachments || [])" :key="i" class="at-row">
                <span class="at-name">{{ f.filename || f.safe_filename }}</span>
                <span class="at-mode" :class="`mode-${classifyMode(f.filename || f.safe_filename || '')}`">
                  {{ classifyMode(f.filename || f.safe_filename || '') }}
                </span>
              </div>
            </div>
          </div>

          <!-- ── Error (friendly) ── -->
          <div class="tp-error" v-if="meta.error">⚠️ {{ meta.error }}</div>

          <!-- ── Actions ── -->
          <div class="tp-actions">
            <button v-if="meta.status === 'exported'" class="tpa-btn btn-view-prompt"
              @click="$emit('viewPrompt', meta.task_id)">📄 View Prompt</button>

            <button v-if="meta.status === 'exported'" class="tpa-btn btn-run-agent"
              @click="$emit('runAgent', { taskId: meta.task_id, bubbleId: msg.id })">▶ Run Agent</button>

            <button v-if="meta.status === 'agent_running'" class="tpa-btn btn-view-prompt"
              @click="$emit('viewPrompt', meta.task_id)">📄 View Prompt</button>

            <button v-if="meta.status === 'agent_running'" class="tpa-btn btn-save-report"
              @click="$emit('saveReport', { taskId: meta.task_id, bubbleId: msg.id })">💾 Save Report</button>

            <button
              v-if="meta.agent_run_id && ['completed_prompt_ready','waiting_hermes','waiting_for_hermes_manual_execution','hermes_manual_pending','hermes_response_unrecognized'].includes(meta.agent_run_status)"
              class="tpa-btn btn-copy-prompt"
              @click="$emit('copyAgentPrompt', { runId: meta.agent_run_id })">📋 Copy Agent Prompt</button>

            <button
              v-if="meta.agent_run_id && ['completed_prompt_ready','waiting_hermes','waiting_for_hermes_manual_execution','hermes_manual_pending','hermes_response_unrecognized'].includes(meta.agent_run_status)"
              class="tpa-btn btn-save-agent-report"
              @click="$emit('saveAgentReport', { taskId: meta.task_id, runId: meta.agent_run_id, bubbleId: msg.id })">📝 Save Agent Report</button>

            <button v-if="meta.agent_run_status === 'blocked_approval_required'"
              class="tpa-btn btn-approve"
              @click="$emit('approveAgentRun', { taskId: meta.task_id, bubbleId: msg.id, approvalPhrase: meta.approval_phrase, approvalReason: meta.agent_approval_reason })">⛔ Approve</button>

            <button v-if="meta.status === 'completed'" class="tpa-btn btn-view-report"
              @click="$emit('viewReport', { taskId: meta.task_id, bubbleId: msg.id })">📊 View Report</button>

            <button v-if="meta.status === 'completed' && meta.agent_events?.length"
              class="tpa-btn btn-timeline"
              @click="$emit('viewTimeline', { taskId: meta.task_id, events: meta.agent_events })">🕐 Timeline</button>

            <button v-if="meta.status === 'completed'" class="tpa-btn btn-view-prompt"
              @click="$emit('viewPrompt', meta.task_id)">📄 View Prompt</button>

            <a class="tpa-link" href="/jobs">Jobs →</a>
          </div>
        </div>

        <!-- Legacy non-task bubble -->
        <div class="bubble-meta" v-else-if="msg.meta?.task_id">
          <a class="tpa-link" href="/jobs">ดูใน Jobs →</a>
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
defineEmits([
  'viewPrompt', 'runAgent', 'saveReport', 'viewReport', 'viewTimeline',
  'copyAgentPrompt', 'saveAgentReport', 'approveAgentRun',
  'applyCodeEdit', 'commitCodeEdit', 'rollbackCodeEdit', 'viewCodeEditPatch',
])

const AGENT_ICONS = {
  'manager': '🧭', 'programmer': '💻', 'devops': '🐳',
  'administrator': '🛡', 'designer': '🎨', 'qa': '🧪',
  'security': '🔐', 'rag-curator': '📚', 'observer': '👁',
  'research': '🔬', 'worker': '⚙️',
}
const agentIcon  = (a) => AGENT_ICONS[a] || '🤖'
const verifyIcon = (v) => {
  const lv = (v || '').toLowerCase()
  return { pass: '✅', warning: '⚠️', fail: '❌', unknown: '❓' }[lv] || ''
}

const STATUS_LABELS = {
  pending: 'รับคำสั่งแล้ว',
  running: 'กำลังวิเคราะห์',
  exporting: 'กำลังเตรียมข้อมูล',
  exported: 'เตรียมข้อมูลเรียบร้อย',
  agent_running: 'AI กำลังประมวลผล',
  completed: 'เสร็จแล้ว',
  failed: 'มีปัญหา',
  blocked: 'รอการยืนยัน',
  waiting_approval: 'รอการยืนยัน',
  completed_prompt_ready: 'เตรียมข้อมูลเรียบร้อย',
  completed_report_saved: 'เสร็จแล้ว',
  waiting_hermes: 'AI กำลังประมวลผล',
  waiting_for_hermes_manual_execution: 'AI หลักยังไม่ตอบกลับ — กำลังรอ',
  hermes_manual_pending: 'AI หลักยังไม่ตอบกลับ — กำลังรอ',
  hermes_response_unrecognized: 'ผลลัพธ์มีปัญหา — กรุณาตรวจสอบ',
  blocked_approval_required: 'ต้องยืนยันก่อนดำเนินการ',
}
const statusLabel = (s) => STATUS_LABELS[s] || (s || '').toUpperCase()

// User-friendly verification label
const verifyText = (v) => {
  const lv = (v || '').toUpperCase()
  return { PASS: 'ตรวจสอบแล้ว', WARNING: 'มีข้อควรระวัง', FAIL: 'ไม่ผ่านการตรวจสอบ', UNKNOWN: 'ยังไม่ระบุผลตรวจสอบ' }[lv] || ''
}

const meta      = computed(() => props.msg.meta || {})
const isTask    = computed(() => meta.value.type === 'task')
const isBlocked = computed(() =>
  meta.value.status === 'blocked' || meta.value.status === 'waiting_approval'
)

// Friendly Thai sentence shown at the top of every task bubble — replaces tech jargon
const friendlyStatusText = computed(() => {
  const s = meta.value.status
  const ars = meta.value.agent_run_status
  if (s === 'completed') return 'งานเสร็จแล้ว และบันทึกรายงานเรียบร้อย'
  if (s === 'failed')   return 'งานนี้มีปัญหา ดูรายละเอียดทางเทคนิคหรือเปิดในหน้า Jobs ได้'
  if (ars === 'completed_report_saved') return 'AI ประมวลผลเสร็จแล้ว กำลังบันทึกรายงาน...'
  if (ars === 'waiting_for_hermes_manual_execution' || ars === 'hermes_manual_pending')
    return 'ระบบ AI หลักยังไม่ตอบกลับ กำลังรอการดำเนินการสำรอง'
  if (ars === 'hermes_response_unrecognized')
    return 'ระบบ AI ตอบกลับในรูปแบบที่ไม่รู้จัก กรุณาบันทึกรายงานเอง'
  if (ars === 'blocked_approval_required') return 'งานนี้ต้องยืนยันก่อนดำเนินการ'
  if (s === 'agent_running' || ars === 'waiting_hermes') return 'กำลังให้ AI ประมวลผล...'
  if (s === 'exported') return 'เตรียมข้อมูลสำหรับ AI เรียบร้อยแล้ว กำลังประมวลผลต่อ'
  if (s === 'exporting' || s === 'running') return 'กำลังเตรียมงาน...'
  if (s === 'blocked' || s === 'waiting_approval') return 'งานนี้ต้องยืนยันก่อนดำเนินการ'
  return 'รับคำสั่งแล้ว กำลังเตรียมงานให้...'
})

// Show technical sections only when at least one has content
const hasTechnicalContent = computed(() => {
  const m = meta.value
  return !!(m.hermes_http_status || m.hermes_response_format || m.agent_run_id
    || m.agent_run_mode || m.rag_results_count > 0 || m.fallback_reason
    || m.fallback_mode || m.export_path || m.agent_prompt_path || m.report_path)
})
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
/* ── Layout ── */
.bubble-row { display: flex; flex-direction: column; margin-bottom: 14px; }
.bubble-row.user   { align-items: flex-end; }
.bubble-row.system { align-items: flex-start; }

.bubble {
  display: flex; align-items: flex-start; gap: 10px;
  max-width: 92%; padding: 12px 14px;
  border-radius: 16px; word-break: break-word;
}
.bubble.system {
  background: #111827;
  border: 1px solid #1e293b;
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 16px rgba(0,0,0,0.45);
}
.bubble.user {
  background: #1d4ed8; color: #fff;
  border-bottom-right-radius: 4px;
  flex-direction: row-reverse;
}

/* ── Dot ── */
.dot { flex-shrink: 0; width: 9px; height: 9px; border-radius: 50%; background: #22c55e; margin-top: 5px; }
.dot-green  { background: #22c55e; }
.dot-blue   { background: #3b82f6; animation: pulse 1.4s infinite; }
.dot-orange { background: #f97316; animation: pulse 1.4s infinite; }
.dot-red    { background: #ef4444; }
.dot-yellow { background: #f59e0b; }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.3; } }

.bubble-body { flex: 1; min-width: 0; }
.bubble-text {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 14.5px; line-height: 1.55; margin: 0;
  white-space: pre-wrap; word-break: break-word;
}
.bubble.user   .bubble-text { color: #e0f2fe; }
.bubble.system .bubble-text { color: #cbd5e1; }

/* ── Task Panel ── */
.task-panel {
  margin-top: 10px; padding-top: 10px;
  border-top: 1px solid #1e293b;
}

/* Header */
.tp-header { margin-bottom: 8px; }
.tp-id-row { display: flex; align-items: center; gap: 7px; margin-bottom: 5px; }
.tp-id {
  font-family: 'Menlo','Consolas',monospace; font-size: 0.68rem;
  color: #475569; background: #0f172a; padding: 1px 6px;
  border-radius: 4px; border: 1px solid #1e293b;
}
.tp-badge {
  font-size: 0.6rem; font-weight: 800; padding: 2px 8px;
  border-radius: 999px; letter-spacing: 0.07em; text-transform: uppercase;
}
.tbadge-pending          { background: #1e293b; color: #64748b; }
.tbadge-running          { background: #1e3a5f; color: #60a5fa; border: 1px solid #1d4ed8; }
.tbadge-exporting        { background: #2e1065; color: #a78bfa; border: 1px solid #6d28d9; }
.tbadge-exported         { background: #14532d; color: #4ade80; border: 1px solid #16a34a; }
.tbadge-agent_running    { background: #431407; color: #fb923c; border: 1px solid #c2410c; }
.tbadge-completed        { background: #14532d; color: #86efac; border: 1px solid #22c55e; }
.tbadge-failed           { background: #450a0a; color: #f87171; border: 1px solid #b91c1c; }
.tbadge-blocked,
.tbadge-waiting_approval { background: #422006; color: #fbbf24; border: 1px solid #d97706; }
.tp-pct { font-size: 0.65rem; color: #334155; font-family: monospace; margin-left: auto; }

/* Progress */
.tp-progress-track { width: 100%; height: 3px; background: #1e293b; border-radius: 999px; overflow: hidden; margin-bottom: 5px; }
.tp-progress-fill  { height: 100%; border-radius: 999px; transition: width 0.4s ease; }
.tpf-pending          { background: #334155; }
.tpf-running          { background: #3b82f6; }
.tpf-exporting        { background: #8b5cf6; }
.tpf-exported         { background: #22c55e; }
.tpf-agent_running    { background: #f97316; }
.tpf-completed        { background: #059669; }
.tpf-failed           { background: #ef4444; }
.tpf-blocked,
.tpf-waiting_approval { background: #f59e0b; }

.tp-step { font-size: 0.72rem; color: #475569; font-style: italic; margin-bottom: 6px; line-height: 1.4; }

/* Friendly status (replaces tech badge for default chat view) */
.tp-friendly {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  margin-bottom: 8px;
}
.tp-friendly-text {
  font-size: 0.85rem; color: #f1f5f9; font-weight: 500; line-height: 1.45;
  flex: 1; min-width: 0;
}
.tp-badge-small { font-size: 0.6rem !important; padding: 1px 6px !important; opacity: 0.65; }

/* RAG hint shown in friendly Thai (kept visible) */
.tp-rag-hint {
  font-size: 0.74rem; color: #93c5fd;
  background: #0f2040; border: 1px solid #1e3a5f;
  border-radius: 6px; padding: 4px 9px; margin-bottom: 6px;
}

/* Collapsible technical details */
.tech-details {
  margin: 6px 0;
  background: #0f172a; border: 1px solid #1e293b;
  border-radius: 8px; padding: 0;
}
.tech-summary {
  cursor: pointer; padding: 6px 10px;
  font-size: 0.72rem; color: #94a3b8; font-weight: 600;
  user-select: none; list-style: none;
}
.tech-summary::-webkit-details-marker { display: none; }
.tech-summary:hover { color: #cbd5e1; }
.tech-details[open] .tech-summary {
  border-bottom: 1px solid #1e293b; color: #cbd5e1;
}
.tech-body {
  padding: 8px 10px;
  display: flex; flex-direction: column; gap: 4px;
}
.tech-row { display: flex; gap: 8px; font-size: 0.72rem; align-items: baseline; }
.tech-key { min-width: 78px; color: #64748b; font-weight: 600; }
.tech-val { color: #cbd5e1; word-break: break-all; flex: 1; min-width: 0; }
.tech-val code, code.tech-val { font-family: monospace; font-size: 0.7rem; color: #a78bfa; background: transparent; }
.tech-ok  { color: #4ade80; font-weight: 700; }
.tech-err { color: #fca5a5; }
.tech-link {
  display: inline-block; margin-top: 4px;
  font-size: 0.72rem; color: #60a5fa; text-decoration: none;
}
.tech-link:hover { text-decoration: underline; }
.ap-hint { font-size: 0.74rem; color: #fcd34d; margin-top: 4px; }

/* ── Self-modify code edit section ── */
.sec-code-edit {
  background: #1c1230; border-left: 3px solid #a78bfa;
}
.ce-line { font-size: 0.82rem; color: #e2e8f0; line-height: 1.5; margin-bottom: 4px; }
.ce-files {
  margin: 4px 0; padding-left: 1.1rem;
  font-size: 0.74rem; color: #c4b5fd; font-family: monospace; line-height: 1.55;
}
.ce-risk {
  font-size: 0.74rem; padding: 4px 8px; border-radius: 6px;
  margin-top: 4px; display: inline-block;
}
.ce-risk-1, .ce-risk-2 { background: #064e3b; color: #6ee7b7; }
.ce-risk-3            { background: #422006; color: #fbbf24; }
.ce-risk-4            { background: #422006; color: #fbbf24; }
.ce-risk-5            { background: #450a0a; color: #fca5a5; }
.ce-risk code         { font-weight: 700; }

.ce-blocked {
  font-size: 0.78rem; color: #fca5a5;
  background: #1c0a0a; border: 1px solid #7f1d1d; border-radius: 6px;
  padding: 5px 8px; margin: 4px 0;
}
.ce-err-detail { font-size: 0.72rem; opacity: 0.85; margin-top: 3px; }

.ce-apply {
  font-size: 0.78rem; color: #cbd5e1;
  background: #0f172a; border: 1px solid #334155; border-radius: 6px;
  padding: 6px 9px; margin: 4px 0;
}
.ce-apply strong { color: #f1f5f9; }
.ce-apply code   { font-family: monospace; color: #c4b5fd; }

.ce-diff {
  margin: 4px 0 0; padding: 4px 6px;
  font-family: monospace; font-size: 0.7rem;
  background: #020617; border-radius: 4px; color: #cbd5e1;
  white-space: pre-wrap; word-break: break-word;
  max-height: 120px; overflow-y: auto;
}

.ce-actions { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.ce-btn {
  font-size: 0.72rem; font-weight: 600;
  padding: 4px 10px; border-radius: 6px; border: none; cursor: pointer;
}
.ce-btn:hover { opacity: 0.88; }
.ce-btn-view     { background: #334155; color: #e9d5ff; }
.ce-btn-apply    { background: #6d28d9; color: #fff; }
.ce-btn-commit   { background: #15803d; color: #fff; }
.ce-btn-rollback { background: #b45309; color: #fff; }

/* Agent Activity */
.tp-agent-activity {
  display: flex; align-items: center; flex-wrap: wrap; gap: 5px;
  padding: 5px 8px; background: #0f172a; border-radius: 6px;
  border-left: 2px solid #1e3a5f; margin-bottom: 8px; font-size: 0.75rem;
}
.taa-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.taad-running       { background: #3b82f6; animation: pulse 1.4s infinite; }
.taad-agent_running { background: #f97316; animation: pulse 1.4s infinite; }
.taad-exporting     { background: #8b5cf6; animation: pulse 1.4s infinite; }
.taad-exported      { background: #22c55e; }
.taad-completed     { background: #059669; }
.taad-failed        { background: #ef4444; }
.taad-pending       { background: #475569; }
.taa-name  { font-weight: 700; color: #93c5fd; }
.taa-sep   { color: #334155; font-size: 0.68rem; }
.taa-chips { display: flex; flex-wrap: wrap; gap: 3px; width: 100%; margin-top: 2px; }
.taa-chip  { font-size: 0.62rem; padding: 1px 6px; background: #1e3a5f; color: #7dd3fc; border-radius: 999px; }

/* ── Section Cards ── */
.tp-section {
  border-radius: 8px; padding: 7px 10px; margin-bottom: 6px; font-size: 0.77rem;
}
.sec-label {
  font-size: 0.58rem; font-weight: 800; letter-spacing: 0.09em;
  text-transform: uppercase; margin-bottom: 4px;
}
.sec-label-row {
  display: flex; align-items: center; gap: 7px; flex-wrap: wrap; margin-bottom: 4px;
}
.sec-label-row .sec-label { margin-bottom: 0; }
.sec-body { display: flex; flex-wrap: wrap; align-items: center; gap: 5px; }

/* ── HERMES SUCCESS (green) ── */
.sec-hermes-ok { background: #022c22; border: 1px solid #14532d; border-left: 3px solid #22c55e; }
.sec-hermes-ok .sec-label { color: #4ade80; }
.hs-http.ok  { font-weight: 800; color: #4ade80; font-size: 0.78rem; }
.hs-badge-status { font-size: 0.68rem; color: #86efac; font-family: monospace; background: #064e3b; padding: 1px 5px; border-radius: 3px; }
.hs-fmt      { font-size: 0.68rem; color: #6ee7b7; background: #064e3b; padding: 1px 5px; border-radius: 3px; }
.hs-saved    { font-size: 0.67rem; color: #34d399; width: 100%; margin-top: 2px; }
.hs-received { font-size: 0.65rem; color: #059669; width: 100%; }

/* ── HERMES WAITING (amber) ── */
.sec-hermes-wait { background: #1a0e00; border: 1px solid #451a03; border-left: 3px solid #f97316; }
.sec-hermes-wait .sec-label { color: #fb923c; }
.hw-chip { font-size: 0.67rem; color: #fbbf24; font-family: monospace; background: #422006; padding: 1px 6px; border-radius: 3px; }
.hw-hint { font-size: 0.72rem; color: #78350f; width: 100%; margin-top: 3px; }

/* ── HERMES FALLBACK (orange/red) ── */
.sec-hermes-fallback { background: #160800; border: 1px solid #7c2d12; border-left: 3px solid #f97316; }
.sec-hermes-fallback .sec-label { color: #fb923c; }
.hf-mode       { font-size: 0.66rem; color: #fbbf24; background: #431407; padding: 1px 6px; border-radius: 3px; font-family: monospace; }
.hf-status-chip{ font-size: 0.66rem; color: #fdba74; background: #431407; padding: 1px 6px; border-radius: 3px; font-family: monospace; }
.hf-reason     { font-size: 0.72rem; color: #fca5a5; width: 100%; margin-top: 4px; word-break: break-word; line-height: 1.45; }

/* ── HERMES ERROR ── */
.sec-hermes-err { background: #1c0000; border: 1px solid #7f1d1d; border-left: 3px solid #ef4444; }
.sec-hermes-err .sec-label { color: #f87171; }
.hs-http.err { font-weight: 800; color: #f87171; font-size: 0.78rem; }

/* ── AGENT RUNNER (purple) ── */
.sec-agent-runner { background: #130a2a; border: 1px solid #4c1d95; border-left: 3px solid #8b5cf6; }
.sec-agent-runner .sec-label { color: #a78bfa; }
.ar-mode   { font-size: 0.68rem; color: #c4b5fd; font-family: monospace; background: #2e1065; padding: 1px 6px; border-radius: 3px; }
.ar-status { font-size: 0.66rem; font-weight: 700; padding: 1px 6px; border-radius: 3px; font-family: monospace; }
.ar-id     { font-size: 0.6rem; color: #334155; font-family: monospace; margin-left: auto; }
.ar-prompt-path { font-size: 0.6rem; color: #475569; font-family: monospace; width: 100%; margin-top: 2px; }
.ars-completed_report_saved             { background: #052e16; color: #4ade80; }
.ars-completed_prompt_ready             { background: #052e16; color: #86efac; }
.ars-waiting_for_hermes_manual_execution{ background: #422006; color: #fbbf24; }
.ars-blocked_approval_required          { background: #422006; color: #fb923c; }
.ars-failed                             { background: #450a0a; color: #f87171; }
.ars-running                            { background: #1e3a5f; color: #93c5fd; }
.ars-waiting_hermes                     { background: #1e3a5f; color: #60a5fa; }
.ars-hermes_manual_pending              { background: #422006; color: #fbbf24; }
.ars-hermes_response_unrecognized       { background: #450a0a; color: #f87171; }
.ars-completed                          { background: #052e16; color: #4ade80; }

/* ── RAG WIKI (cyan) ── */
.sec-rag { background: #040f1f; border: 1px solid #0e4f6b; border-left: 3px solid #06b6d4; }
.sec-rag .sec-label { color: #22d3ee; }
.rag-cnt  { font-size: 0.75rem; font-weight: 700; color: #67e8f9; }
.rag-path { font-size: 0.62rem; color: #0891b2; font-family: monospace; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ── APPROVAL REQUIRED (red) ── */
.sec-approval { background: #1c0000; border: 1px solid #7f1d1d; border-left: 3px solid #ef4444; }
.sec-approval .sec-label { color: #f87171; }
.ap-reason { font-size: 0.75rem; color: #fca5a5; width: 100%; margin-bottom: 4px; }
.ap-phrase { font-size: 0.75rem; color: #fbbf24; font-weight: 700; font-family: monospace; }

/* ── REPORT (emerald) ── */
.sec-report { background: #022c22; border: 1px solid #14532d; border-left: 3px solid #10b981; }
.sec-report .sec-label { color: #34d399; }
.rp-source  { font-size: 0.62rem; color: #334155; margin-left: auto; }
.rp-preview { font-size: 0.75rem; color: #6ee7b7; line-height: 1.5; width: 100%; margin-top: 3px; word-break: break-word; }

/* Verify badge */
.verify-badge { font-size: 0.6rem; font-weight: 800; padding: 2px 7px; border-radius: 999px; text-transform: uppercase; letter-spacing: 0.05em; }
.vbadge-pass    { background: #14532d; color: #4ade80; }
.vbadge-warning { background: #422006; color: #fbbf24; }
.vbadge-fail    { background: #450a0a; color: #f87171; }
.vbadge-unknown { background: #1e293b; color: #64748b; }

/* ── ATTACHMENTS (blue) ── */
.sec-attach { background: #040f1f; border: 1px solid #1e3a5f; border-left: 3px solid #3b82f6; }
.sec-attach .sec-label { color: #60a5fa; }
.attach-grid { flex-direction: column; gap: 3px; }
.at-row  { display: flex; align-items: center; gap: 6px; }
.at-name { font-size: 0.7rem; color: #94a3b8; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.at-mode { font-size: 0.6rem; font-weight: 700; padding: 1px 5px; border-radius: 3px; }
.mode-text-extract        { background: #052e16; color: #4ade80; }
.mode-document-extract    { background: #1e3a5f; color: #60a5fa; }
.mode-spreadsheet-extract { background: #2e1065; color: #a78bfa; }
.mode-presentation-extract{ background: #422006; color: #fbbf24; }
.mode-vision-required     { background: #500724; color: #f9a8d4; }
.mode-unsupported         { background: #1e293b; color: #475569; }

/* Misc */
.tp-export-path { font-size: 0.7rem; color: #4ade80; margin-bottom: 5px; word-break: break-all; }
.tp-export-path code { font-family: monospace; color: #6ee7b7; }
.tp-error { background: #1c0000; border: 1px solid #7f1d1d; border-left: 3px solid #ef4444; border-radius: 8px; padding: 6px 10px; margin-bottom: 6px; font-size: 0.73rem; color: #fca5a5; }

/* ── Actions ── */
.tp-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; padding-top: 8px; border-top: 1px solid #1e293b; }
.tpa-btn {
  font-size: 0.7rem; font-weight: 700; padding: 5px 11px;
  border-radius: 6px; border: none; cursor: pointer;
  letter-spacing: 0.02em; transition: opacity 0.15s, transform 0.1s;
}
.tpa-btn:hover { opacity: 0.82; transform: translateY(-1px); }
.tpa-btn:active { transform: translateY(0); }
.btn-view-prompt       { background: #0e7490; color: #e0f2fe; }
.btn-run-agent         { background: #1d4ed8; color: #dbeafe; }
.btn-save-report       { background: #b45309; color: #fef3c7; }
.btn-view-report       { background: #059669; color: #d1fae5; }
.btn-timeline          { background: #1e3a5f; color: #93c5fd; }
.btn-copy-prompt       { background: #4c1d95; color: #ede9fe; }
.btn-save-agent-report { background: #6d28d9; color: #f5f3ff; }
.btn-approve           { background: #7f1d1d; color: #fecaca; }

.tpa-link { font-size: 0.68rem; color: #334155; text-decoration: none; font-weight: 600; padding: 5px 0; margin-left: auto; align-self: center; }
.tpa-link:hover { color: #60a5fa; }

.bubble-meta { margin-top: 6px; }
.bubble-time { font-size: 0.6rem; color: #334155; margin-top: 4px; padding: 0 4px; }
</style>
