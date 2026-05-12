<template>
  <div class="page">
    <div class="card">
      <div class="header">
        <span class="header-title">🚀 AI Command Center</span>
      </div>
      <ModeChips v-model="selectedMode" />
      <CommandChat
        :messages="messages"
        :is-sending="isSending"
        ref="chatRef"
        @viewPrompt="viewPrompt"
        @runAgent="runAgent"
        @saveReport="openSaveReport"
        @viewReport="viewReport"
        @viewTimeline="viewTimeline"
      />
      <QuickActions @action="handleQuickAction" />
      <CommandInput
        v-model:text="inputText"
        :is-sending="isSending"
        @send="sendCommand"
        @error="onInputError"
      />
    </div>

    <!-- Save Report Modal -->
    <div class="modal-overlay" v-if="saveModal.open" @click.self="closeSaveModal">
      <div class="modal">
        <div class="modal-header">
          <span>💾 Save Agent Report — {{ saveModal.taskId?.slice(0,8) }}…</span>
          <button class="btn-close" @click="closeSaveModal">✕</button>
        </div>
        <div class="modal-body">
          <p class="save-instruction">
            วาง <strong>ผลลัพธ์จาก Agent</strong> ที่นี่ — ห้ามวาง Prompt content หรือ Skill SOP
          </p>
          <div class="save-meta-row">
            <div class="save-field">
              <label class="field-label">Agent Source</label>
              <select v-model="saveModal.report_source" class="agent-select">
                <option value="claude">Claude</option>
                <option value="hermes">Hermes</option>
                <option value="agentuniverse">agentUniverse</option>
                <option value="manual">Manual</option>
              </select>
            </div>
            <div class="save-field">
              <label class="field-label">Verification</label>
              <select v-model="saveModal.verification_status" class="agent-select">
                <option value="">— (not set)</option>
                <option value="pass">✅ Pass</option>
                <option value="warning">⚠️ Warning</option>
                <option value="fail">❌ Fail</option>
              </select>
            </div>
          </div>
          <div class="save-field-full">
            <label class="field-label">Summary <span class="field-hint">(optional)</span></label>
            <input v-model="saveModal.report_summary" class="summary-input" placeholder="สรุปผลสั้นๆ เช่น: ตรวจ health สำเร็จ ทุก service OK" />
          </div>
          <div class="save-field-full">
            <label class="field-label">Final Report <span class="required">*</span></label>
            <textarea
              v-model="saveModal.report"
              class="report-textarea"
              placeholder="วาง output ทั้งหมดจาก Claude/Hermes ที่นี่…"
              rows="10"
            ></textarea>
          </div>
          <div class="modal-error" v-if="saveModal.error">❌ {{ saveModal.error }}</div>
        </div>
        <div class="modal-footer">
          <button
            class="btn btn-save"
            :disabled="!saveModal.report.trim() || saveModal.loading"
            @click="submitSaveReport"
          >
            <span v-if="saveModal.loading">⏳ Saving…</span>
            <span v-else>💾 Save Report</span>
          </button>
          <button class="btn btn-close-modal" @click="closeSaveModal">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Report Modal -->
    <div class="modal-overlay" v-if="reportModal.open" @click.self="closeReportModal">
      <div class="modal">
        <div class="modal-header">
          <span>📊 Agent Report — {{ reportModal.taskId?.slice(0,8) }}…</span>
          <button class="btn-close" @click="closeReportModal">✕</button>
        </div>

        <div class="modal-body" v-if="reportModal.loading">⏳ Loading…</div>
        <div class="modal-body modal-error" v-else-if="reportModal.error">❌ {{ reportModal.error }}</div>

        <!-- No report yet -->
        <div class="modal-body no-report-body" v-else-if="!reportModal.data?.final_report">
          <div class="no-report-icon">📋</div>
          <div class="no-report-text">ยังไม่มี Final Report</div>
          <div class="no-report-hint">กรุณากด Run Agent แล้ว Save Report ก่อน</div>
        </div>

        <!-- Structured report -->
        <div class="modal-body report-body" v-else>
          <div class="report-meta-block">
            <div class="rmi"><span class="rml">Source</span><span class="rmv">{{ reportModal.data.report_source || '—' }}</span></div>
            <div class="rmi"><span class="rml">Saved</span><span class="rmv">{{ fmtFull(reportModal.data.report_saved_at) }}</span></div>
            <div class="rmi" v-if="reportModal.data.verification_status">
              <span class="rml">Verification</span>
              <span class="verify-badge" :class="`vbadge-${reportModal.data.verification_status}`">
                {{ verifyIcon(reportModal.data.verification_status) }} {{ reportModal.data.verification_status?.toUpperCase() }}
              </span>
            </div>
          </div>

          <div class="report-section" v-if="reportModal.data.report_summary">
            <div class="rs-title">📋 สรุปผล</div>
            <div class="rs-summary">{{ reportModal.data.report_summary }}</div>
          </div>

          <div class="report-section">
            <div class="rs-title">📄 Final Report</div>
            <pre class="rs-content">{{ reportModal.data.final_report }}</pre>
          </div>

          <div class="report-section" v-if="reportModal.data.issues_found?.length">
            <div class="rs-title">🔍 Issues Found</div>
            <ul class="rs-list">
              <li v-for="item in reportModal.data.issues_found" :key="item">{{ item }}</li>
            </ul>
          </div>

          <div class="report-section" v-if="reportModal.data.recommendations?.length">
            <div class="rs-title">💡 Recommendations</div>
            <ul class="rs-list">
              <li v-for="item in reportModal.data.recommendations" :key="item">{{ item }}</li>
            </ul>
          </div>

          <div class="report-section" v-if="reportModal.data.next_actions?.length">
            <div class="rs-title">➡️ Next Actions</div>
            <ul class="rs-list">
              <li v-for="item in reportModal.data.next_actions" :key="item">{{ item }}</li>
            </ul>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn btn-copy" v-if="reportModal.data?.final_report" @click="copyReport">📋 Copy Report</button>
          <button class="btn btn-close-modal" @click="closeReportModal">Close</button>
        </div>
      </div>
    </div>

    <!-- Timeline Modal -->
    <div class="modal-overlay" v-if="timelineModal.open" @click.self="closeTimeline">
      <div class="modal">
        <div class="modal-header">
          <span>🕐 Agent Timeline — {{ timelineModal.taskId?.slice(0,8) }}…</span>
          <button class="btn-close" @click="closeTimeline">✕</button>
        </div>
        <div class="modal-body">
          <div class="tl-empty" v-if="!timelineModal.events.length">No agent events yet.</div>
          <div v-for="(evt, i) in timelineModal.events" :key="i" class="tl-item">
            <div class="tl-icon">{{ agentIcon(evt.agent) }}</div>
            <div class="tl-body">
              <div class="tl-header-row">
                <span class="tl-agent">{{ evt.agent }}</span>
                <span class="tl-role">{{ evt.role }}</span>
                <span class="tl-time">{{ fmtFull(evt.timestamp) }}</span>
              </div>
              <div class="tl-action">{{ evt.action }}</div>
              <div class="tl-msg" v-if="evt.message">{{ evt.message }}</div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-close-modal" @click="closeTimeline">Close</button>
        </div>
      </div>
    </div>

    <!-- Prompt Modal -->
    <div class="modal-overlay" v-if="promptModal.open" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <span>Prompt — {{ promptModal.taskId?.slice(0,8) }}…</span>
          <button class="btn-close" @click="closeModal">✕</button>
        </div>
        <div class="modal-body" v-if="promptModal.loading">⏳ Loading…</div>
        <div class="modal-body modal-error" v-else-if="promptModal.error">❌ {{ promptModal.error }}</div>
        <pre class="modal-body prompt-content" v-else>{{ promptModal.content }}</pre>
        <div class="modal-footer">
          <button class="btn btn-copy" @click="copyPrompt">📋 Copy</button>
          <button class="btn btn-close-modal" @click="closeModal">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import ModeChips from '~/components/ModeChips.vue'
import CommandChat from '~/components/CommandChat.vue'
import QuickActions from '~/components/QuickActions.vue'
import CommandInput from '~/components/CommandInput.vue'

const config  = useRuntimeConfig()
const API     = config.public.apiBase
const WORKER  = config.public.workerBase
const SECRET  = config.public.gatewaySecret || ''

const chatRef      = ref(null)
const messages     = ref([])
const inputText    = ref('')
const isSending    = ref(false)
const selectedMode = ref('plan-only')

const promptModal   = ref({ open: false, taskId: '', loading: false, error: '', content: '' })
const saveModal     = ref({ open: false, taskId: '', bubbleId: '', report: '', report_source: 'claude', report_summary: '', verification_status: '', loading: false, error: '' })
const reportModal   = ref({ open: false, taskId: '', loading: false, error: '', data: null })
const timelineModal = ref({ open: false, taskId: '', events: [] })

// Map taskId → intervalId for cleanup on unmount
const activePolls = new Map()

const MODE_MAP = {
  'plan-only':  { mode: 'plan-only', environment: 'wsl' },
  'dev-fix':    { mode: 'execute',   environment: 'dev' },
  'staging':    { mode: 'dry-run',   environment: 'staging' },
  'production': { mode: 'plan-only', environment: 'production' },
}

onMounted(() => {
  addMessage('system',
    'ระบบออนไลน์: ยินดีต้อนรับครับบอส ลองพิมพ์คำสั่งดูได้เลยครับ' +
    '\nเช่น "@Designer ออกแบบหน้าจอ POSFood ให้หน่อย"'
  )
})

onUnmounted(() => {
  for (const id of activePolls.values()) clearInterval(id)
  activePolls.clear()
})

// ── Message helpers ───────────────────────────────────────────────────────
function addMessage(role, text, meta = null) {
  const id = (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : Date.now().toString() + Math.random()
  messages.value.push({ id, role, text, meta, createdAt: new Date().toISOString() })
  nextTick(() => chatRef.value?.scrollToBottom())
  return id
}

function updateMessage(id, patch) {
  const idx = messages.value.findIndex(m => m.id === id)
  if (idx !== -1) {
    messages.value.splice(idx, 1, { ...messages.value[idx], ...patch })
    nextTick(() => chatRef.value?.scrollToBottom())
  }
}

function getMessageMeta(id) {
  return messages.value.find(m => m.id === id)?.meta || {}
}

// ── Task meta builders ────────────────────────────────────────────────────
function statusToProgress(status) {
  return {
    pending: 0, running: 25, exporting: 80, exported: 100,
    agent_running: 10, completed: 100,
    failed: 100, blocked: 0, waiting_approval: 0,
  }[status] ?? 0
}

function statusToStep(status) {
  return {
    pending: 'รับคำสั่งแล้ว',
    running: 'กำลังประมวลผล...',
    exporting: 'กำลังสร้าง Prompt...',
    exported: 'Prompt พร้อมแล้ว — รอส่งให้ Agent',
    agent_running: 'กำลังให้ Agent ประมวลผล',
    completed: 'Agent ทำงานเสร็จแล้ว — มี Final Report',
    failed: 'เกิดข้อผิดพลาด',
    blocked: 'รอการอนุมัติ',
    waiting_approval: 'รอการอนุมัติ',
  }[status] ?? status
}

function buildTaskMeta(task) {
  return {
    type: 'task',
    task_id: task.task_id,
    status: task.status,
    progress: task.progress ?? statusToProgress(task.status),
    current_step: task.current_step || statusToStep(task.status),
    agents: task.agents,
    skills: task.skills,
    export_path: task.result?.export_path,
    error: task.result?.error,
    approval_phrase: task.accountability?.approval_phrase,
    // Agent activity fields
    current_agent: task.current_agent || task.agents?.[0] || null,
    speaker_agent: task.speaker_agent || null,
    working_agent: task.working_agent || null,
    active_agents: task.active_agents || task.agents || [],
    agent_events: task.agent_events || [],
    // Report fields
    final_report: task.result?.final_report || null,
    report_source: task.result?.report_source || null,
    report_summary: task.result?.report_summary || null,
    verification_status: task.result?.verification_status || null,
    // Attachments
    attachments_count: task.attachments?.length || 0,
    attachments: task.attachments || [],
  }
}

// ── Auto-process + polling ────────────────────────────────────────────────
async function startAutoProcess(taskId, bubbleId) {
  // Poll every 1.5 s while process-task runs concurrently
  const intervalId = setInterval(async () => {
    try {
      const res = await fetch(`${API}/tasks/${taskId}`)
      if (!res.ok) return
      const task = await res.json()
      updateMessage(bubbleId, { meta: buildTaskMeta(task) })
      if (['exported', 'failed', 'blocked', 'waiting_approval'].includes(task.status)) {
        clearInterval(intervalId)
        activePolls.delete(taskId)
      }
    } catch { /* ignore transient errors */ }
  }, 1500)
  activePolls.set(taskId, intervalId)

  // Call process-task (synchronous on worker side — poll catches intermediate states)
  try {
    const res = await fetch(`${WORKER}/process-task`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId }),
    })
    clearInterval(intervalId)
    activePolls.delete(taskId)

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      updateMessage(bubbleId, {
        meta: {
          ...getMessageMeta(bubbleId),
          status: 'failed',
          progress: 100,
          current_step: 'เกิดข้อผิดพลาด',
          error: err.detail || `HTTP ${res.status}`,
        },
      })
      return
    }

    // Final authoritative state from gateway
    try {
      const final = await fetch(`${API}/tasks/${taskId}`)
      if (final.ok) {
        const t = await final.json()
        updateMessage(bubbleId, { meta: buildTaskMeta(t) })
      }
    } catch { /* skip */ }
  } catch (e) {
    clearInterval(intervalId)
    activePolls.delete(taskId)
    updateMessage(bubbleId, {
      meta: {
        ...getMessageMeta(bubbleId),
        status: 'failed',
        progress: 0,
        current_step: 'ไม่สามารถเชื่อมต่อ Worker',
        error: e.message,
      },
    })
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────
async function uploadFile(file) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${API}/uploads`, { method: 'POST', body: fd })
  if (!res.ok) throw new Error(`Upload ${file.name} failed: HTTP ${res.status}`)
  return await res.json()
}

// ── Send command ──────────────────────────────────────────────────────────
async function sendCommand(payload) {
  const text  = payload.text?.trim()
  const files = payload.files || []
  if (!text && !files.length) return
  if (isSending.value) return

  addMessage('user', text || `[แนบไฟล์ ${files.length} ไฟล์]`)
  inputText.value = ''
  isSending.value = true

  const modeConf = MODE_MAP[selectedMode.value] || MODE_MAP['plan-only']

  try {
    // 1. Upload attachments
    const attachments = []
    for (const f of files) {
      try {
        attachments.push(await uploadFile(f))
      } catch (e) {
        addMessage('system', `⚠️ ${e.message}`)
      }
    }

    // 2. POST /tasks
    const headers = { 'Content-Type': 'application/json' }
    if (SECRET) headers['X-Gateway-Secret'] = SECRET

    const res = await fetch(`${API}/tasks`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        source: 'dashboard',
        user: 'chain',
        text: text || '[Attachment task]',
        target_system: null,
        environment: modeConf.environment,
        mode: modeConf.mode,
        attachments,
      }),
    })

    const data = await res.json()
    if (!res.ok) {
      addMessage('system', `ส่งคำสั่งไม่สำเร็จ: ${data.detail || `HTTP ${res.status}`}`)
      return
    }

    // 3. Create task bubble
    const isBlocked = data.approval_required || selectedMode.value === 'production'
    const bubbleId = addMessage('system', 'รับคำสั่งแล้วครับ', {
      type: 'task',
      task_id: data.task_id,
      status: isBlocked ? 'blocked' : 'pending',
      progress: 0,
      current_step: isBlocked ? 'รอการอนุมัติ' : 'รับคำสั่งแล้ว',
      agents: data.agents,
      skills: data.skills,
      approval_phrase: data.approval_phrase,
      attachments_count: attachments.length,
      attachments: attachments,
    })

    if (attachments.length) {
      const names = attachments.map(a => a.filename || a.safe_filename || '?').join(', ')
      addMessage('system', `ไฟล์ที่แนบ: ${names}`)
    }

    // 4. Auto-process (skip if blocked)
    if (!isBlocked) {
      startAutoProcess(data.task_id, bubbleId)
    }
  } catch (e) {
    addMessage('system', `ส่งคำสั่งไม่สำเร็จ: ไม่สามารถเชื่อมต่อ API (${e.message})`)
  } finally {
    isSending.value = false
  }
}

// ── Quick action ──────────────────────────────────────────────────────────
function handleQuickAction(text) { inputText.value = text }
function onInputError(msg) { addMessage('system', `⚠️ ${msg}`) }

// ── Report template + validation ─────────────────────────────────────────
const REPORT_TEMPLATE = `## Final Report

### Summary
สรุปผลการทำงาน

### Services Checked
- Mobile Gateway:
- RAG API:
- TTO API:
- RTK Bridge:
- Webhook Gateway:
- Observer:
- Worker:
- Qdrant:
- Postgres:
- Redis:
- Web Dashboard:

### Issues Found
- ไม่มี / ระบุปัญหาที่พบ

### Commands Used
- docker compose ps
- docker compose config --quiet
- curl health endpoints
- docker logs tail

### Recommendations
- ข้อเสนอแนะถัดไป

### Verification Status
PASS / WARNING / FAIL`

function validateReport(report) {
  const warns = []
  if (report.includes('สรุปผลการทำงาน')) warns.push('กรุณากรอก Summary ให้ครบก่อน')
  if (!report.includes('Services Checked'))   warns.push('ไม่มีส่วน Services Checked')
  if (report.includes('PASS / WARNING / FAIL')) warns.push('กรุณาระบุ Verification Status เป็น PASS, WARNING หรือ FAIL')
  return warns
}

// ── Run Agent (fallback-manual) ───────────────────────────────────────────
async function runAgent({ taskId, bubbleId }) {
  try {
    const res = await fetch(`${API}/tasks/${taskId}/run-agent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      addMessage('system', `⚠️ Run Agent ไม่สำเร็จ: ${err.detail || res.status}`)
      return
    }
    updateMessage(bubbleId, {
      meta: {
        ...getMessageMeta(bubbleId),
        status: 'agent_running',
        progress: 10,
        current_step: 'กำลังเตรียมส่ง Prompt ให้ Agent',
      },
    })
  } catch (e) {
    addMessage('system', `⚠️ Run Agent error: ${e.message}`)
  }
}

// ── Save Report modal ─────────────────────────────────────────────────────
function openSaveReport({ taskId, bubbleId }) {
  saveModal.value = {
    open: true, taskId, bubbleId,
    report: REPORT_TEMPLATE,
    report_source: 'claude', report_summary: '', verification_status: '',
    loading: false, error: '',
  }
  // Log template opened (fire-and-forget)
  fetch(`${API}/tasks/${taskId}/agent-activity`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event: { agent: 'user', role: 'user', action: 'report_template_opened', message: 'เปิด Save Report modal' } }),
  }).catch(() => {})
}

async function submitSaveReport() {
  if (!saveModal.value.report.trim()) return
  const warns = validateReport(saveModal.value.report)
  if (warns.length > 0) {
    const ok = confirm(`⚠️ รายการที่ยังไม่ครบ:\n${warns.map(w => '• ' + w).join('\n')}\n\nต้องการบันทึกต่อไปหรือไม่?`)
    if (!ok) return
  }
  saveModal.value.loading = true
  saveModal.value.error = ''
  try {
    const body = {
      report: saveModal.value.report,
      report_source: saveModal.value.report_source,
    }
    if (saveModal.value.report_summary.trim()) body.report_summary = saveModal.value.report_summary.trim()
    if (saveModal.value.verification_status)  body.verification_status = saveModal.value.verification_status
    const res = await fetch(`${API}/tasks/${saveModal.value.taskId}/save-report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      saveModal.value.error = err.detail || `HTTP ${res.status}`
      return
    }
    updateMessage(saveModal.value.bubbleId, {
      meta: {
        ...getMessageMeta(saveModal.value.bubbleId),
        status: 'completed',
        progress: 100,
        current_step: 'Agent ทำงานเสร็จแล้ว — มี Final Report',
        final_report: saveModal.value.report,
        report_source: saveModal.value.report_source,
        report_summary: saveModal.value.report_summary || null,
        verification_status: saveModal.value.verification_status || null,
      },
    })
    saveModal.value.open = false
  } catch (e) {
    saveModal.value.error = e.message
  } finally {
    saveModal.value.loading = false
  }
}

function closeSaveModal() { saveModal.value.open = false }

// ── View Report modal ─────────────────────────────────────────────────────
async function viewReport({ taskId }) {
  reportModal.value = { open: true, taskId, loading: true, error: '', data: null }
  try {
    const res = await fetch(`${API}/tasks/${taskId}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const task = await res.json()
    reportModal.value.data = task.result || {}
  } catch (e) {
    reportModal.value.error = `Cannot load report: ${e.message}`
  } finally {
    reportModal.value.loading = false
  }
}

function closeReportModal() { reportModal.value.open = false }

async function copyReport() {
  try {
    await navigator.clipboard.writeText(reportModal.value.data?.final_report || '')
    alert('Copied!')
  } catch { alert('Copy not supported in this browser') }
}

const AGENT_ICONS = {
  'manager': '🧭', 'programmer': '💻', 'devops': '🐳',
  'administrator': '🛡', 'designer': '🎨', 'qa': '🧪',
  'security': '🔐', 'rag-curator': '📚', 'observer': '👁',
  'research': '🔬', 'worker': '⚙️',
}
const agentIcon  = (a) => AGENT_ICONS[a] || '🤖'
const fmtFull = (ts) => {
  if (!ts) return '—'
  try { return new Date(ts).toLocaleString('th-TH', { dateStyle: 'medium', timeStyle: 'short' }) }
  catch { return ts }
}
const verifyIcon = (v) => ({ pass: '✅', warning: '⚠️', fail: '❌' }[v] || '')

// ── Timeline modal ────────────────────────────────────────────────────────
function viewTimeline({ taskId, events }) {
  timelineModal.value = { open: true, taskId, events: events || [] }
}
function closeTimeline() { timelineModal.value.open = false }

// ── Prompt modal ──────────────────────────────────────────────────────────
async function viewPrompt(taskId) {
  promptModal.value = { open: true, taskId, loading: true, error: '', content: '' }
  try {
    const res = await fetch(`${WORKER}/exports/${taskId}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    promptModal.value.content = data.content || '(empty)'
  } catch (e) {
    promptModal.value.error = `Cannot load prompt: ${e.message}`
  } finally {
    promptModal.value.loading = false
  }
}

function closeModal() { promptModal.value.open = false }

async function copyPrompt() {
  try {
    await navigator.clipboard.writeText(promptModal.value.content)
    alert('Copied!')
  } catch { alert('Copy not supported in this browser') }
}
</script>

<style scoped>
*, *::before, *::after { box-sizing: border-box; }

.page {
  min-height: 100vh;
  background: #eef0f4;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  padding: 0;
}

@media (min-width: 600px) {
  .page { align-items: center; padding: 24px 16px; }
}

.card {
  width: 100%;
  max-width: 560px;
  min-height: 100vh;
  background: #fff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

@media (min-width: 600px) {
  .card {
    min-height: 680px;
    max-height: 840px;
    border-radius: 16px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.13);
  }
}

.header {
  background: #1d6fe8;
  color: #fff;
  text-align: center;
  padding: 18px 16px;
  flex-shrink: 0;
}

@media (min-width: 600px) { .header { border-radius: 16px 16px 0 0; } }

.header-title { font-size: 1.1rem; font-weight: 700; letter-spacing: 0.01em; }

/* ── Modal ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 200;
}
@media (min-width: 600px) {
  .modal-overlay { align-items: center; padding: 1rem; }
}

.modal {
  background: #1e293b;
  color: #e2e8f0;
  width: 100%;
  max-width: 660px;
  max-height: 85vh;
  border-radius: 16px 16px 0 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
@media (min-width: 600px) { .modal { border-radius: 16px; } }

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.9rem 1rem;
  border-bottom: 1px solid #334155;
  font-weight: 600;
  font-size: 0.9rem;
}
.btn-close {
  background: none; border: none;
  color: #64748b; font-size: 1.1rem; cursor: pointer;
  padding: 0.2rem 0.4rem;
}

.modal-body { flex: 1; overflow-y: auto; padding: 1rem; }
.modal-error { color: #fca5a5; }

.prompt-content {
  font-family: monospace;
  font-size: 0.78rem;
  color: #cbd5e1;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  line-height: 1.6;
}

.modal-footer {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-top: 1px solid #334155;
  justify-content: flex-end;
}

.btn { padding: 0.45rem 0.9rem; border-radius: 8px; border: none; font-size: 0.82rem; font-weight: 600; cursor: pointer; }
.btn:disabled    { opacity: 0.5; cursor: not-allowed; }
.btn-copy        { background: #334155; color: #94a3b8; }
.btn-close-modal { background: #0f766e; color: #fff; }
.btn-save        { background: #c2410c; color: #fff; }

.save-instruction { font-size: 0.82rem; color: #94a3b8; margin-bottom: 0.75rem; }
.save-instruction strong { color: #e2e8f0; }

.save-meta-row   { display: flex; gap: 0.75rem; margin-bottom: 0.6rem; flex-wrap: wrap; }
.save-field      { display: flex; flex-direction: column; gap: 3px; flex: 1; min-width: 120px; }
.save-field-full { display: flex; flex-direction: column; gap: 3px; margin-bottom: 0.6rem; }
.field-label     { font-size: 0.75rem; color: #64748b; font-weight: 600; }
.field-hint      { font-weight: 400; color: #475569; }
.required        { color: #f87171; }

.agent-select {
  background: #0f172a; color: #e2e8f0;
  border: 1px solid #334155; border-radius: 6px;
  padding: 0.3rem 0.6rem; font-size: 0.82rem;
}
.summary-input {
  width: 100%; background: #0f172a; color: #e2e8f0;
  border: 1px solid #334155; border-radius: 6px;
  padding: 0.4rem 0.6rem; font-size: 0.82rem; box-sizing: border-box;
}
.report-textarea {
  width: 100%; background: #0f172a; color: #e2e8f0;
  border: 1px solid #334155; border-radius: 8px; padding: 0.75rem;
  font-family: monospace; font-size: 0.78rem; line-height: 1.6;
  resize: vertical; box-sizing: border-box;
}
.modal-error { color: #fca5a5; font-size: 0.82rem; margin-top: 0.5rem; }

/* Report modal body */
.no-report-body {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 0.5rem; padding: 3rem 1rem; color: #64748b;
}
.no-report-icon { font-size: 2rem; }
.no-report-text { font-size: 1rem; font-weight: 600; color: #94a3b8; }
.no-report-hint { font-size: 0.82rem; color: #475569; }

.report-body    { padding: 1rem; overflow-y: auto; }
.report-meta-block {
  background: #0f172a; border: 1px solid #334155; border-radius: 8px;
  padding: 0.75rem; margin-bottom: 1rem; display: flex; flex-direction: column; gap: 5px;
}
.rmi { display: flex; align-items: center; gap: 8px; font-size: 0.8rem; }
.rml { color: #64748b; font-weight: 600; min-width: 80px; }
.rmv { color: #e2e8f0; }

.verify-badge {
  font-size: 0.7rem; font-weight: 700; padding: 2px 8px;
  border-radius: 999px; text-transform: uppercase; letter-spacing: 0.04em;
}
.vbadge-pass    { background: #14532d; color: #4ade80; }
.vbadge-warning { background: #422006; color: #fbbf24; }
.vbadge-fail    { background: #450a0a; color: #f87171; }

.report-section  { margin-bottom: 1rem; }
.rs-title {
  font-size: 0.8rem; font-weight: 700; color: #94a3b8;
  margin-bottom: 0.4rem; letter-spacing: 0.03em;
}
.rs-summary { font-size: 0.88rem; color: #e2e8f0; line-height: 1.5; }
.rs-content {
  font-family: monospace; font-size: 0.78rem; color: #cbd5e1;
  white-space: pre-wrap; word-break: break-word;
  background: #0f172a; border: 1px solid #334155;
  border-radius: 8px; padding: 0.75rem; margin: 0; line-height: 1.6;
  max-height: 320px; overflow-y: auto;
}
.rs-list {
  margin: 0; padding-left: 1.2rem; color: #cbd5e1; font-size: 0.82rem; line-height: 1.8;
}

/* Timeline */
.tl-empty { color: #64748b; text-align: center; padding: 2rem; font-size: 0.85rem; }
.tl-item  { display: flex; gap: 10px; padding: 0.6rem 0; border-bottom: 1px solid #0f172a; }
.tl-item:last-child { border-bottom: none; }
.tl-icon  { font-size: 1.2rem; flex-shrink: 0; width: 24px; text-align: center; }
.tl-body  { flex: 1; min-width: 0; }
.tl-header-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 2px; }
.tl-agent { font-size: 0.8rem; font-weight: 700; color: #93c5fd; }
.tl-role  { font-size: 0.65rem; padding: 1px 5px; border-radius: 4px; background: #1e3a5f; color: #7dd3fc; }
.tl-time  { font-size: 0.65rem; color: #475569; margin-left: auto; }
.tl-action{ font-size: 0.75rem; color: #64748b; font-family: monospace; margin-bottom: 2px; }
.tl-msg   { font-size: 0.78rem; color: #cbd5e1; }
</style>
