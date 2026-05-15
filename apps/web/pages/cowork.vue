<template>
  <div class="cw-root">

    <!-- ══ LEFT SIDEBAR ══ -->
    <CoworkSidebar
      v-model="activeTab"
      :wsInfo="wsInfo"
      :recentItems="recentItems"
      @newTask="focusInput"
      @openWorkspaces="pickerOpen = true"
      @testWorkspace="testActiveWorkspace"
      @selectWorkspace="onSelectWorkspace"
      @openArtifacts="navigateJobs"
    />

    <!-- ══ CENTER PANEL ══ -->
    <div class="cw-center">
      <!-- Center header -->
      <div class="cw-header">
        <div class="cw-header-left">
          <span class="cw-mode-tag" :class="`mode-tag--${activeTab}`">
            {{ TAB_LABELS[activeTab] }}
          </span>
          <div class="cw-ws-info" v-if="wsInfo">
            <span class="cw-ws-name">{{ wsInfo.name }}</span>
            <code class="cw-ws-branch" v-if="wsInfo.git_branch">{{ wsInfo.git_branch }}</code>
            <span class="cw-ws-dot" title="Healthy">●</span>
          </div>
          <div class="cw-ws-info cw-ws-empty" v-else>
            <button class="cw-select-ws-btn" @click="pickerOpen = true">Select workspace ▾</button>
          </div>
        </div>
        <div class="cw-header-right">
          <div class="cw-mode-selector">
            <button
              v-for="m in MODES"
              :key="m.id"
              class="cw-mode-opt"
              :class="{ 'cw-mode-opt--active': selectedMode === m.id }"
              @click="selectedMode = m.id"
            >{{ m.label }}</button>
          </div>
          <a class="cw-hdr-link" href="/jobs" title="Jobs">Jobs ↗</a>
          <a class="cw-hdr-link" href="/settings" title="Settings">⚙</a>
        </div>
      </div>

      <!-- Chat area (reuse existing CommandChat) -->
      <CommandChat
        :messages="messages"
        :is-sending="isSending"
        ref="chatRef"
        class="cw-chat"
        @viewPrompt="viewPrompt"
        @runAgent="runAgent"
        @saveReport="openSaveReport"
        @viewReport="viewReport"
        @viewTimeline="viewTimeline"
        @copyAgentPrompt="copyAgentPrompt"
        @saveAgentReport="openAgentReport"
        @approveAgentRun="openApproveModal"
        @applyCodeEdit="applyCodeEdit"
        @commitCodeEdit="commitCodeEdit"
        @rollbackCodeEdit="rollbackCodeEdit"
        @viewCodeEditPatch="viewCodeEditPatch"
      />

      <!-- Quick actions -->
      <QuickActions @action="handleQuickAction" />

      <!-- Input -->
      <CommandInput
        v-model:text="inputText"
        :is-sending="isSending"
        ref="inputRef"
        @send="sendCommand"
        @error="onInputError"
      />
    </div>

    <!-- ══ RIGHT INSPECTOR ══ (hidden on mobile/tablet via CSS) -->
    <CoworkInspector
      :activeTask="lastTaskMeta"
      :wsInfo="wsInfo"
      class="cw-inspector-panel"
    />

    <!-- ══ WORKSPACE PICKER DRAWER ══ -->
    <WorkspacePicker
      :open="pickerOpen"
      :workspaces="workspaceList"
      :loading="wsListLoading"
      @close="pickerOpen = false"
      @select="setActiveWorkspace"
      @test="testWorkspace"
      @openInCowork="onOpenInCowork"
    />

    <!-- ══ MODALS (reused from command.vue) ══ -->

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
            <input v-model="saveModal.report_summary" class="text-input" placeholder="สรุปผลสั้นๆ" />
          </div>
          <div class="save-field-full">
            <label class="field-label">Final Report <span class="required">*</span></label>
            <textarea v-model="saveModal.report" class="report-textarea" placeholder="วาง output ทั้งหมดจาก Claude/Hermes ที่นี่…" rows="10"></textarea>
          </div>
          <div class="modal-error" v-if="saveModal.error">❌ {{ saveModal.error }}</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-save" :disabled="!saveModal.report.trim() || saveModal.loading" @click="submitSaveReport">
            <span v-if="saveModal.loading">⏳ Saving…</span>
            <span v-else>💾 Save Report</span>
          </button>
          <button class="btn btn-secondary" @click="closeSaveModal">Cancel</button>
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
        <div class="modal-body no-report-body" v-else-if="!reportModal.data?.final_report">
          <div class="no-report-icon">📋</div>
          <div class="no-report-text">ยังไม่มี Final Report</div>
          <div class="no-report-hint">กรุณากด Run Agent แล้ว Save Report ก่อน</div>
        </div>
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
        </div>
        <div class="modal-footer">
          <button class="btn btn-copy" v-if="reportModal.data?.final_report" @click="copyReport">📋 Copy</button>
          <button class="btn btn-secondary" @click="closeReportModal">Close</button>
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
          <button class="btn btn-secondary" @click="closeTimeline">Close</button>
        </div>
      </div>
    </div>

    <!-- Approve Modal -->
    <div class="modal-overlay" v-if="approveModal.open" @click.self="closeApproveModal">
      <div class="modal">
        <div class="modal-header">
          <span>⛔ Approve Agent Run — {{ approveModal.taskId?.slice(0,8) }}…</span>
          <button class="btn-close" @click="closeApproveModal">✕</button>
        </div>
        <div class="modal-body">
          <div v-if="approveModal.reason" class="approve-reason">🔒 {{ approveModal.reason }}</div>
          <p class="approve-instruction">
            Required phrase: <code>{{ approveModal.required_phrase }}</code>
          </p>
          <div class="save-field-full">
            <label class="field-label">Approval Phrase <span class="required">*</span></label>
            <input v-model="approveModal.phrase" class="text-input" :placeholder="approveModal.required_phrase" @keydown.enter="submitApproval" />
          </div>
          <div class="save-field-full">
            <label class="field-label">Approved By</label>
            <input v-model="approveModal.approved_by" class="text-input" placeholder="ชื่อผู้อนุมัติ" />
          </div>
          <div class="modal-error" v-if="approveModal.error">❌ {{ approveModal.error }}</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-approve" :disabled="!approveModal.phrase.trim() || approveModal.loading" @click="submitApproval">
            <span v-if="approveModal.loading">⏳ Approving…</span>
            <span v-else>✅ Approve & Run Agent</span>
          </button>
          <button class="btn btn-secondary" @click="closeApproveModal">Cancel</button>
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
          <button class="btn btn-secondary" @click="closeModal">Close</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import CoworkSidebar   from '~/components/CoworkSidebar.vue'
import CoworkInspector from '~/components/CoworkInspector.vue'
import WorkspacePicker from '~/components/WorkspacePicker.vue'
import CommandChat     from '~/components/CommandChat.vue'
import QuickActions    from '~/components/QuickActions.vue'
import CommandInput    from '~/components/CommandInput.vue'

const config  = useRuntimeConfig()
const API     = config.public.apiBase
const WORKER  = config.public.workerBase
const SECRET  = config.public.gatewaySecret || ''

// ── Layout state ──────────────────────────────────────────────────────────
const activeTab    = ref('cowork')
const selectedMode = ref('plan-only')
const pickerOpen   = ref(false)

const TAB_LABELS = { chat: 'Chat', cowork: 'CoWork', code: 'Code' }
const MODES = [
  { id: 'plan-only',  label: 'Plan Only' },
  { id: 'dev-fix',    label: 'Dev Fix' },
  { id: 'staging',    label: 'Staging' },
  { id: 'production', label: 'Production' },
]
const MODE_MAP = {
  'plan-only':  { mode: 'plan-only', environment: 'wsl' },
  'dev-fix':    { mode: 'execute',   environment: 'dev' },
  'staging':    { mode: 'dry-run',   environment: 'staging' },
  'production': { mode: 'plan-only', environment: 'production' },
}

// ── Workspace state ───────────────────────────────────────────────────────
const wsInfo        = ref(null)
const workspaceList = ref([])
const wsListLoading = ref(false)
const recentItems   = ref([
  { name: 'AI Control Center', health: 'ok', active: true },
  { name: 'POSFood', health: 'ok', active: false },
  { name: 'demo69', health: 'unknown', active: false },
])

// ── Chat state ────────────────────────────────────────────────────────────
const chatRef   = ref(null)
const inputRef  = ref(null)
const messages  = ref([])
const inputText = ref('')
const isSending = ref(false)

// ── Modal state ───────────────────────────────────────────────────────────
const promptModal   = ref({ open: false, taskId: '', loading: false, error: '', content: '' })
const saveModal     = ref({ open: false, taskId: '', bubbleId: '', report: '', report_source: 'claude', report_summary: '', verification_status: '', loading: false, error: '' })
const reportModal   = ref({ open: false, taskId: '', loading: false, error: '', data: null })
const timelineModal = ref({ open: false, taskId: '', events: [] })
const approveModal  = ref({ open: false, taskId: '', bubbleId: '', phrase: '', approved_by: 'chain', required_phrase: '', reason: '', loading: false, error: '' })

// ── Polling cleanup ───────────────────────────────────────────────────────
const activePolls = new Map()

// ── Last task meta → inspector ────────────────────────────────────────────
const lastTaskMeta = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i].meta?.type === 'task') {
      return messages.value[i].meta
    }
  }
  return null
})

// ── Init ──────────────────────────────────────────────────────────────────
onMounted(async () => {
  addMessage('system',
    'ระบบออนไลน์ครับ ยินดีต้อนรับ — ลองพิมพ์คำสั่ง เช่น:\n"ใน workspace AI Control Center ช่วยเสนอ patch ปรับหน้าแรก"'
  )
  await Promise.all([loadWorkspace(), loadWorkspaceList()])
})

onUnmounted(() => {
  for (const id of activePolls.values()) clearInterval(id)
  activePolls.clear()
})

async function loadWorkspace() {
  try {
    const [wsRes, healthRes] = await Promise.allSettled([
      fetch(`${WORKER}/workspace`),
      fetch(`${WORKER}/workspace/health`),
    ])

    if (wsRes.status === 'fulfilled' && wsRes.value.ok) {
      wsInfo.value = await wsRes.value.json()
    }

    if (healthRes.status === 'fulfilled' && healthRes.value.ok) {
      const h = await healthRes.value.json()
      // Normalize: merge health fields, prefer git_branch from health if wsInfo doesn't have it
      wsInfo.value = {
        ...wsInfo.value,
        health: h.healthy ? 'ok' : (h.root_exists ? 'warning' : 'error'),
        healthy: h.healthy,
        git_available: h.git_available,
        root_exists: h.root_exists,
        git_branch: wsInfo.value?.git_branch || h.git_branch || null,
        health_error: h.error || null,
      }
    }

    if (wsInfo.value?.name) {
      const healthStatus = wsInfo.value.health || 'unknown'
      const idx = recentItems.value.findIndex(r => r.name === wsInfo.value.name)
      if (idx >= 0) {
        recentItems.value[idx].active = true
        recentItems.value[idx].health = healthStatus === 'ok' ? 'ok' : 'unknown'
      }
    }
  } catch { /* non-critical */ }
}

async function loadWorkspaceList() {
  wsListLoading.value = true
  try {
    const res = await fetch(`${WORKER}/workspaces`)
    if (res.ok) {
      workspaceList.value = await res.json()
    } else if (wsInfo.value) {
      workspaceList.value = [{ ...wsInfo.value, active: true, health: 'ok' }]
    }
  } catch {
    if (wsInfo.value) {
      workspaceList.value = [{ ...wsInfo.value, active: true, health: 'ok' }]
    }
  } finally {
    wsListLoading.value = false
  }
}

async function setActiveWorkspace(ws) {
  try {
    const res = await fetch(`${WORKER}/workspaces/active`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: ws.name }),
    })
    if (res.ok) {
      wsInfo.value = ws
      pickerOpen.value = false
      addMessage('system', `✅ เปลี่ยน workspace เป็น: ${ws.name}`)
    }
  } catch { /* fallback: just set locally */
    wsInfo.value = ws
    pickerOpen.value = false
  }
}

async function testActiveWorkspace() {
  if (!wsInfo.value) { pickerOpen.value = true; return }
  await testWorkspace(wsInfo.value)
}

async function testWorkspace(ws) {
  try {
    const res = await fetch(`${WORKER}/workspaces/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: ws.name }),
    })
    const data = await res.json().catch(() => ({}))
    if (res.ok && data.ok) {
      addMessage('system', `✅ Workspace "${ws.name}" — access OK`)
    } else {
      addMessage('system', `⚠️ Workspace "${ws.name}" — ${data.error || 'test failed'}`)
    }
  } catch (e) {
    addMessage('system', `⚠️ Workspace test error: ${e.message}`)
  }
}

function onSelectWorkspace(ws) {
  setActiveWorkspace(ws)
}

function onOpenInCowork(ws) {
  setActiveWorkspace(ws)
  activeTab.value = 'cowork'
  focusInput()
}

function focusInput() {
  nextTick(() => inputRef.value?.$el?.querySelector('textarea')?.focus())
}

function navigateJobs() {
  window.location.href = '/jobs'
}

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

// ── Task meta helpers ─────────────────────────────────────────────────────
function statusToProgress(status) {
  return {
    pending: 0, running: 25, exporting: 80, exported: 100,
    agent_running: 10, completed: 100, failed: 100, blocked: 0, waiting_approval: 0,
  }[status] ?? 0
}

function statusToStep(status) {
  return {
    pending: 'รับคำสั่งแล้ว',
    running: 'กำลังวิเคราะห์...',
    exporting: 'กำลังเตรียมข้อมูล...',
    exported: 'เตรียมข้อมูลเรียบร้อย — กำลังให้ AI ประมวลผล',
    agent_running: 'AI กำลังประมวลผล',
    completed: 'งานเสร็จแล้ว',
    failed: 'งานนี้มีปัญหา',
    blocked: 'ต้องยืนยันก่อนดำเนินการ',
    waiting_approval: 'ต้องยืนยันก่อนดำเนินการ',
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
    current_agent: task.current_agent || task.agents?.[0] || null,
    speaker_agent: task.speaker_agent || null,
    working_agent: task.working_agent || null,
    active_agents: task.active_agents || task.agents || [],
    agent_events: task.agent_events || [],
    final_report: task.result?.final_report || null,
    report_source: task.result?.report_source || null,
    report_summary: task.result?.report_summary || null,
    verification_status: task.result?.verification_status || null,
    attachments_count: task.attachments?.length || 0,
    attachments: task.attachments || [],
    rag_results_count: task.result?.rag_results_count ?? 0,
    rag_top_path: task.result?.rag_top_path || null,
    agent_run_id: task.result?.agent_run_id || null,
    agent_run_status: task.result?.agent_run_status || null,
    agent_run_mode: task.result?.agent_run_mode || null,
    agent_prompt_path: task.result?.agent_prompt_path || null,
    approval_required: task.result?.approval_required || false,
    agent_approval_reason: task.result?.agent_approval_reason || null,
    hermes_http_status: task.result?.hermes_http_status || null,
    hermes_response_format: task.result?.hermes_response_format || null,
    fallback_mode: task.result?.fallback_mode || null,
    fallback_reason: task.result?.fallback_reason || null,
    hermes_endpoint: task.result?.hermes_endpoint || null,
    response_received_at: task.result?.response_received_at || null,
    report_path: task.result?.report_path || null,
    report_saved_at: task.result?.report_saved_at || null,
  }
}

// ── Auto-process + polling ────────────────────────────────────────────────
async function startAutoProcess(taskId, bubbleId) {
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
    } catch { /* ignore transient */ }
  }, 1500)
  activePolls.set(taskId, intervalId)

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
        meta: { ...getMessageMeta(bubbleId), status: 'failed', progress: 100, current_step: 'เกิดข้อผิดพลาด', error: err.detail || `HTTP ${res.status}` },
      })
      return
    }
    try {
      const final = await fetch(`${API}/tasks/${taskId}`)
      if (final.ok) updateMessage(bubbleId, { meta: buildTaskMeta(await final.json()) })
    } catch { /* skip */ }
  } catch (e) {
    clearInterval(intervalId)
    activePolls.delete(taskId)
    updateMessage(bubbleId, {
      meta: { ...getMessageMeta(bubbleId), status: 'failed', progress: 0, current_step: 'ไม่สามารถเชื่อมต่อ Worker', error: e.message },
    })
  }
}

// ── File upload helper ────────────────────────────────────────────────────
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
    const attachments = []
    for (const f of files) {
      try { attachments.push(await uploadFile(f)) }
      catch (e) { addMessage('system', `⚠️ ${e.message}`) }
    }

    const headers = { 'Content-Type': 'application/json' }
    if (SECRET) headers['X-Gateway-Secret'] = SECRET

    const res = await fetch(`${API}/tasks`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        source: 'cowork',
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

    const isBlocked = data.approval_required || selectedMode.value === 'production'
    const bubbleId = addMessage('system', 'รับคำสั่งแล้วครับ กำลังเตรียมงาน', {
      type: 'task',
      task_id: data.task_id,
      status: isBlocked ? 'blocked' : 'pending',
      progress: 0,
      current_step: isBlocked ? 'รอการอนุมัติ' : 'รับคำสั่งแล้ว',
      agents: data.agents,
      skills: data.skills,
      approval_phrase: data.approval_phrase,
      attachments_count: attachments.length,
      attachments,
    })

    if (attachments.length) {
      const names = attachments.map(a => a.filename || a.safe_filename || '?').join(', ')
      addMessage('system', `ไฟล์ที่แนบ: ${names}`)
    }

    if (!isBlocked) {
      startAutoProcess(data.task_id, bubbleId)
    }

    if (detectCodeEdit(text)) {
      planCodeEdit(text, bubbleId, data.task_id).catch((e) => {
        updateMessage(bubbleId, {
          meta: { ...getMessageMeta(bubbleId), code_edit: { status: 'error', message: e.message } },
        })
      })
    }
  } catch (e) {
    addMessage('system', `ส่งคำสั่งไม่สำเร็จ: ไม่สามารถเชื่อมต่อ API (${e.message})`)
  } finally {
    isSending.value = false
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────
function handleQuickAction(text) { inputText.value = text }
function onInputError(msg) { addMessage('system', `⚠️ ${msg}`) }

// ── Run Agent ─────────────────────────────────────────────────────────────
async function runAgent({ taskId, bubbleId }) {
  try {
    const res = await fetch(`${API}/tasks/${taskId}/run-agent`, { method: 'POST', headers: { 'Content-Type': 'application/json' } })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      addMessage('system', `⚠️ Run Agent ไม่สำเร็จ: ${err.detail || res.status}`)
      return
    }
    updateMessage(bubbleId, { meta: { ...getMessageMeta(bubbleId), status: 'agent_running', progress: 10, current_step: 'กำลังให้ AI ประมวลผล...' } })
  } catch (e) { addMessage('system', `⚠️ Run Agent error: ${e.message}`) }
}

// ── Save Report ───────────────────────────────────────────────────────────
const REPORT_TEMPLATE = `## Final Report\n\n### Summary\nสรุปผลการทำงาน\n\n### Verification Status\nPASS / WARNING / FAIL`

function validateReport(report) {
  const warns = []
  if (report.includes('สรุปผลการทำงาน')) warns.push('กรุณากรอก Summary ให้ครบก่อน')
  if (report.includes('PASS / WARNING / FAIL')) warns.push('กรุณาระบุ Verification Status')
  return warns
}

function openSaveReport({ taskId, bubbleId }) {
  saveModal.value = { open: true, taskId, bubbleId, report: REPORT_TEMPLATE, report_source: 'claude', report_summary: '', verification_status: '', loading: false, error: '' }
}

async function submitSaveReport() {
  if (!saveModal.value.report.trim()) return
  const warns = validateReport(saveModal.value.report)
  if (warns.length) {
    const ok = confirm(`⚠️ รายการที่ยังไม่ครบ:\n${warns.map(w => '• ' + w).join('\n')}\n\nต้องการบันทึกต่อไปหรือไม่?`)
    if (!ok) return
  }
  saveModal.value.loading = true
  saveModal.value.error = ''
  try {
    const isAgentRun = !!saveModal.value.runId
    let url, body
    if (isAgentRun) {
      url = `${WORKER}/agent-runs/${saveModal.value.runId}/report`
      body = { final_report: saveModal.value.report, report_source: saveModal.value.report_source, summary: saveModal.value.report_summary.trim() || undefined, verification_status: saveModal.value.verification_status || undefined }
    } else {
      url = `${API}/tasks/${saveModal.value.taskId}/save-report`
      body = { report: saveModal.value.report, report_source: saveModal.value.report_source }
      if (saveModal.value.report_summary.trim()) body.report_summary = saveModal.value.report_summary.trim()
      if (saveModal.value.verification_status) body.verification_status = saveModal.value.verification_status
    }
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      saveModal.value.error = err.detail || `HTTP ${res.status}`
      return
    }
    updateMessage(saveModal.value.bubbleId, {
      meta: { ...getMessageMeta(saveModal.value.bubbleId), status: 'completed', progress: 100, current_step: 'Agent ทำงานเสร็จแล้ว', final_report: saveModal.value.report, report_source: saveModal.value.report_source },
    })
    saveModal.value.open = false
  } catch (e) { saveModal.value.error = e.message }
  finally { saveModal.value.loading = false }
}

function closeSaveModal() { saveModal.value.open = false }

// ── Code Edit ─────────────────────────────────────────────────────────────
const CODE_EDIT_KEYWORDS = ['แก้', 'ปรับ', 'เพิ่ม', 'ลบ', 'refactor', 'fix bug', 'แก้ bug', 'ui', 'component', 'endpoint', 'page', '.vue', 'docker', 'nginx', 'workflow', 'apps/web', 'services/worker', 'services/mobile-gateway']
function detectCodeEdit(text) {
  if (!text) return false
  const t = String(text).toLowerCase()
  return CODE_EDIT_KEYWORDS.some(kw => t.includes(kw.toLowerCase()))
}

async function planCodeEdit(instruction, bubbleId, taskId) {
  updateMessage(bubbleId, { meta: { ...getMessageMeta(bubbleId), code_edit: { status: 'planning', message: 'กำลังให้ AI วางแผนการแก้ไข...' } } })
  const res = await fetch(`${WORKER}/code-edit/plan`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_id: taskId, instruction, files: [] }) })
  const data = await res.json()
  updateMessage(bubbleId, { meta: { ...getMessageMeta(bubbleId), code_edit: data } })
}

async function applyCodeEdit({ taskId, bubbleId }) {
  const meta = getMessageMeta(bubbleId) || {}
  const required = meta.code_edit?.required_apply_phrase
  let phrase = ''
  if (required) {
    phrase = prompt(`Approval phrase required:\n${required}`) || ''
    if (phrase.trim() !== required) { addMessage('system', `⚠️ ยกเลิก — ต้องพิมพ์วลี: ${required}`); return }
  }
  const res = await fetch(`${WORKER}/code-edit/apply`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_id: taskId, approval_phrase: phrase }) })
  const data = await res.json()
  updateMessage(bubbleId, { meta: { ...getMessageMeta(bubbleId), code_edit_apply: data } })
  if (data.status === 'verification_passed' || data.status === 'waiting_commit_approval') {
    addMessage('system', '✅ Apply สำเร็จ — ตรวจสอบ verification ก่อน Commit')
  } else {
    addMessage('system', `⚠️ Apply: ${data.message || data.status}`)
  }
}

async function commitCodeEdit({ taskId, bubbleId }) {
  const meta = getMessageMeta(bubbleId) || {}
  const required = meta.code_edit?.required_commit_phrase
  let phrase = ''
  if (required) {
    phrase = prompt(`Commit approval phrase:\n${required}`) || ''
    if (phrase.trim() !== required) { addMessage('system', `⚠️ ยกเลิก — ต้องพิมพ์วลี: ${required}`); return }
  }
  const commitMessage = prompt('Commit message (เว้นว่างเพื่อใช้ default):') || ''
  const res = await fetch(`${WORKER}/code-edit/commit`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_id: taskId, approval_phrase: phrase, commit_message: commitMessage }) })
  const data = await res.json()
  updateMessage(bubbleId, { meta: { ...getMessageMeta(bubbleId), code_edit_commit: data } })
  if (data.status === 'committed') {
    addMessage('system', `✅ Commit สำเร็จ — ${data.commit_hash} บน ${data.branch}`)
  } else {
    addMessage('system', `⚠️ Commit: ${data.message || data.status}`)
  }
}

async function rollbackCodeEdit({ taskId, bubbleId }) {
  const phrase = prompt('Approval phrase required to rollback:\nROLLBACK PATCH') || ''
  if (phrase.trim() !== 'ROLLBACK PATCH') { addMessage('system', '⚠️ ยกเลิก rollback'); return }
  const res = await fetch(`${WORKER}/code-edit/rollback`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_id: taskId, approval_phrase: phrase }) })
  const data = await res.json()
  updateMessage(bubbleId, { meta: { ...getMessageMeta(bubbleId), code_edit_rollback: data } })
  addMessage('system', data.status === 'rolled_back' ? '✅ Rollback สำเร็จ' : `⚠️ Rollback: ${data.message || data.status}`)
}

async function viewCodeEditPatch({ taskId }) {
  const res = await fetch(`${WORKER}/code-edit/${taskId}/patch?kind=forward`)
  if (!res.ok) { addMessage('system', `⚠️ ไม่พบ patch สำหรับ task ${taskId}`); return }
  const data = await res.json()
  try {
    await navigator.clipboard.writeText(data.content || '')
    addMessage('system', '📋 Copied patch to clipboard')
  } catch {
    addMessage('system', `📄 Patch:\n${(data.content || '').slice(0, 400)}…`)
  }
}

// ── Agent Runner ──────────────────────────────────────────────────────────
async function copyAgentPrompt({ runId }) {
  try {
    const res = await fetch(`${WORKER}/agent-runs/${runId}/prompt`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    await navigator.clipboard.writeText(data.content || '')
    addMessage('system', '✅ Agent Prompt copied to clipboard')
  } catch (e) { addMessage('system', `⚠️ Copy Agent Prompt ไม่สำเร็จ: ${e.message}`) }
}

function openAgentReport({ taskId, runId, bubbleId }) {
  saveModal.value = { open: true, taskId, bubbleId, runId, report: '', report_source: 'claude', report_summary: '', verification_status: '', loading: false, error: '' }
}

function openApproveModal({ taskId, bubbleId, approvalPhrase, approvalReason }) {
  approveModal.value = { open: true, taskId, bubbleId, phrase: '', approved_by: 'chain', required_phrase: approvalPhrase || '', reason: approvalReason || '', loading: false, error: '' }
}

async function submitApproval() {
  if (!approveModal.value.phrase.trim()) return
  approveModal.value.loading = true
  approveModal.value.error = ''
  try {
    const approveRes = await fetch(`${API}/tasks/${approveModal.value.taskId}/approval`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approval_phrase: approveModal.value.phrase.trim(), approved_by: approveModal.value.approved_by.trim() || 'unknown' }),
    })
    if (!approveRes.ok) {
      const err = await approveRes.json().catch(() => ({}))
      approveModal.value.error = err.detail || `HTTP ${approveRes.status}`
      return
    }
    const runRes = await fetch(`${WORKER}/agent-runs/from-task/${approveModal.value.taskId}`, { method: 'POST', headers: { 'Content-Type': 'application/json' } })
    if (!runRes.ok) {
      const err = await runRes.json().catch(() => ({}))
      approveModal.value.error = err.detail || `HTTP ${runRes.status}`
      return
    }
    const runData = await runRes.json()
    updateMessage(approveModal.value.bubbleId, {
      meta: { ...getMessageMeta(approveModal.value.bubbleId), agent_run_id: runData.agent_run_id, agent_run_status: runData.agent_run_status, agent_run_mode: runData.agent_run_mode, approval_required: false },
    })
    approveModal.value.open = false
    addMessage('system', `✅ Agent Runner approved — run_id: ${runData.agent_run_id?.slice(0,8)}…`)
  } catch (e) { approveModal.value.error = e.message }
  finally { approveModal.value.loading = false }
}

function closeApproveModal() { approveModal.value.open = false }

// ── View Report ───────────────────────────────────────────────────────────
async function viewReport({ taskId }) {
  reportModal.value = { open: true, taskId, loading: true, error: '', data: null }
  try {
    const res = await fetch(`${API}/tasks/${taskId}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    reportModal.value.data = (await res.json()).result || {}
  } catch (e) { reportModal.value.error = `Cannot load report: ${e.message}` }
  finally { reportModal.value.loading = false }
}

function closeReportModal() { reportModal.value.open = false }

async function copyReport() {
  try {
    await navigator.clipboard.writeText(reportModal.value.data?.final_report || '')
    alert('Copied!')
  } catch { alert('Copy not supported in this browser') }
}

// ── Timeline ──────────────────────────────────────────────────────────────
function viewTimeline({ taskId, events }) { timelineModal.value = { open: true, taskId, events: events || [] } }
function closeTimeline() { timelineModal.value.open = false }

// ── Prompt modal ──────────────────────────────────────────────────────────
async function viewPrompt(taskId) {
  promptModal.value = { open: true, taskId, loading: true, error: '', content: '' }
  try {
    const res = await fetch(`${WORKER}/exports/${taskId}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    promptModal.value.content = (await res.json()).content || '(empty)'
  } catch (e) { promptModal.value.error = `Cannot load prompt: ${e.message}` }
  finally { promptModal.value.loading = false }
}

function closeModal() { promptModal.value.open = false }

async function copyPrompt() {
  try { await navigator.clipboard.writeText(promptModal.value.content); alert('Copied!') }
  catch { alert('Copy not supported in this browser') }
}

// ── Formatters ────────────────────────────────────────────────────────────
const AGENT_ICONS = { manager: '🧭', programmer: '💻', devops: '🐳', administrator: '🛡', designer: '🎨', qa: '🧪', security: '🔐', 'rag-curator': '📚', observer: '👁', research: '🔬', worker: '⚙️' }
const agentIcon = (a) => AGENT_ICONS[a] || '🤖'
const fmtFull = (ts) => {
  if (!ts) return '—'
  try { return new Date(ts).toLocaleString('th-TH', { dateStyle: 'medium', timeStyle: 'short' }) }
  catch { return ts }
}
const verifyIcon = (v) => ({ pass: '✅', warning: '⚠️', fail: '❌' }[v] || '')
</script>

<style scoped>
*, *::before, *::after { box-sizing: border-box; }

/* ── Root layout ── */
.cw-root {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  display: flex;
  background: #080c14;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
  color: #e2e8f0;
}

/* ── Center panel ── */
.cw-center {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #0f172a;
  border-left: none;
  border-right: none;
}

/* ── Center header ── */
.cw-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid #1e293b;
  background: #0a1020;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 8px;
}
.cw-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}
.cw-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.cw-mode-tag {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  flex-shrink: 0;
}
.mode-tag--chat   { background: #1e3a5f; color: #60a5fa; }
.mode-tag--cowork { background: #1e1b4b; color: #a78bfa; }
.mode-tag--code   { background: #064e3b; color: #6ee7b7; }

.cw-ws-info {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
}
.cw-ws-name {
  font-size: 0.78rem;
  font-weight: 600;
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cw-ws-branch {
  font-size: 0.62rem;
  background: #064e3b;
  color: #6ee7b7;
  padding: 1px 5px;
  border-radius: 3px;
  font-family: monospace;
  flex-shrink: 0;
}
.cw-ws-dot {
  color: #22c55e;
  font-size: 0.52rem;
  flex-shrink: 0;
}
.cw-ws-empty {}
.cw-select-ws-btn {
  background: #12243f;
  border: 1px solid #1e3a5f;
  border-radius: 5px;
  color: #60a5fa;
  font-size: 0.72rem;
  padding: 3px 8px;
  cursor: pointer;
  font-family: inherit;
}
.cw-select-ws-btn:hover { background: #1e3a5f; }

/* Mode selector buttons */
.cw-mode-selector {
  display: flex;
  gap: 2px;
  background: #080c14;
  padding: 2px;
  border-radius: 7px;
  border: 1px solid #1e293b;
}
.cw-mode-opt {
  padding: 4px 9px;
  border-radius: 5px;
  border: none;
  background: transparent;
  color: #475569;
  font-size: 0.68rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.12s;
  font-family: inherit;
  white-space: nowrap;
}
.cw-mode-opt:hover { color: #94a3b8; }
.cw-mode-opt--active { background: #1e293b; color: #e2e8f0; }

.cw-hdr-link {
  font-size: 0.7rem;
  color: #64748b;
  text-decoration: none;
  padding: 4px 7px;
  border: 1px solid #1e293b;
  border-radius: 5px;
  background: transparent;
  white-space: nowrap;
}
.cw-hdr-link:hover { background: #1e293b; color: #94a3b8; }

/* ── Chat area ── */
.cw-chat { flex: 1; min-height: 0; background: #0c1830 !important; }

/* ── Inspector visibility ── */
.cw-inspector-panel { display: flex; }

/* ── Responsive ── */
@media (max-width: 1100px) {
  .cw-inspector-panel { display: none; }
}
@media (max-width: 700px) {
  /* Sidebar becomes hidden, toggle via state if needed */
}

/* ══ MODALS ══ */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.62);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 500;
}
@media (min-width: 640px) { .modal-overlay { align-items: center; padding: 1rem; } }

.modal {
  background: #1a2540;
  color: #e2e8f0;
  width: 100%;
  max-width: 680px;
  max-height: 85vh;
  border-radius: 14px 14px 0 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #1e293b;
}
@media (min-width: 640px) { .modal { border-radius: 14px; } }

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid #1e293b;
  font-weight: 600;
  font-size: 0.88rem;
  flex-shrink: 0;
}
.btn-close { background: none; border: none; color: #475569; font-size: 1rem; cursor: pointer; padding: 0.2rem 0.4rem; }
.modal-body { flex: 1; overflow-y: auto; padding: 1rem; font-size: 0.82rem; }
.modal-error { color: #fca5a5; }
.modal-footer {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-top: 1px solid #1e293b;
  justify-content: flex-end;
  flex-shrink: 0;
}

.btn { padding: 0.42rem 0.85rem; border-radius: 7px; border: none; font-size: 0.8rem; font-weight: 600; cursor: pointer; font-family: inherit; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-copy     { background: #1e293b; color: #94a3b8; }
.btn-secondary { background: #0f766e; color: #fff; }
.btn-save     { background: #c2410c; color: #fff; }
.btn-approve  { background: #b45309; color: #fff; }

/* Save modal fields */
.save-instruction { font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.75rem; }
.save-instruction strong { color: #e2e8f0; }
.save-meta-row { display: flex; gap: 0.75rem; margin-bottom: 0.6rem; flex-wrap: wrap; }
.save-field { display: flex; flex-direction: column; gap: 3px; flex: 1; min-width: 120px; }
.save-field-full { display: flex; flex-direction: column; gap: 3px; margin-bottom: 0.6rem; }
.field-label { font-size: 0.72rem; color: #64748b; font-weight: 600; }
.field-hint { font-weight: 400; color: #475569; }
.required { color: #f87171; }
.agent-select { background: #0f172a; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px; padding: 0.3rem 0.6rem; font-size: 0.8rem; }
.text-input { width: 100%; background: #0f172a; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px; padding: 0.4rem 0.6rem; font-size: 0.8rem; box-sizing: border-box; font-family: inherit; }
.report-textarea { width: 100%; background: #0f172a; color: #e2e8f0; border: 1px solid #334155; border-radius: 8px; padding: 0.7rem; font-family: monospace; font-size: 0.76rem; line-height: 1.6; resize: vertical; box-sizing: border-box; }
.modal-error { color: #fca5a5; font-size: 0.8rem; margin-top: 0.5rem; }

/* Report modal */
.no-report-body { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.5rem; padding: 3rem 1rem; color: #64748b; }
.no-report-icon { font-size: 2rem; }
.no-report-text { font-size: 1rem; font-weight: 600; color: #94a3b8; }
.no-report-hint { font-size: 0.8rem; color: #475569; }
.report-body    { padding: 1rem; overflow-y: auto; }
.report-meta-block { background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 0.75rem; margin-bottom: 1rem; display: flex; flex-direction: column; gap: 5px; }
.rmi { display: flex; align-items: center; gap: 8px; font-size: 0.78rem; }
.rml { color: #64748b; font-weight: 600; min-width: 76px; }
.rmv { color: #e2e8f0; }
.verify-badge { font-size: 0.68rem; font-weight: 700; padding: 2px 8px; border-radius: 999px; text-transform: uppercase; }
.vbadge-pass    { background: #14532d; color: #4ade80; }
.vbadge-warning { background: #422006; color: #fbbf24; }
.vbadge-fail    { background: #450a0a; color: #f87171; }
.report-section  { margin-bottom: 1rem; }
.rs-title { font-size: 0.78rem; font-weight: 700; color: #94a3b8; margin-bottom: 0.4rem; }
.rs-summary { font-size: 0.85rem; color: #e2e8f0; line-height: 1.5; }
.rs-content { font-family: monospace; font-size: 0.76rem; color: #cbd5e1; white-space: pre-wrap; word-break: break-word; background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 0.75rem; margin: 0; line-height: 1.6; max-height: 320px; overflow-y: auto; }

/* Approve modal */
.approve-reason { background: #450a0a; color: #fca5a5; padding: 0.5rem 0.75rem; border-radius: 6px; font-size: 0.8rem; margin-bottom: 0.75rem; }
.approve-instruction { font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.75rem; line-height: 1.6; }
.approve-instruction code { color: #fbbf24; font-weight: 700; }

/* Prompt modal */
.prompt-content { font-family: monospace; font-size: 0.76rem; color: #cbd5e1; white-space: pre-wrap; word-break: break-word; margin: 0; line-height: 1.6; }

/* Timeline */
.tl-empty { color: #64748b; text-align: center; padding: 2rem; font-size: 0.82rem; }
.tl-item  { display: flex; gap: 10px; padding: 0.6rem 0; border-bottom: 1px solid #0f172a; }
.tl-item:last-child { border-bottom: none; }
.tl-icon  { font-size: 1.1rem; flex-shrink: 0; width: 22px; text-align: center; }
.tl-body  { flex: 1; min-width: 0; }
.tl-header-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 2px; }
.tl-agent { font-size: 0.78rem; font-weight: 700; color: #93c5fd; }
.tl-role  { font-size: 0.62rem; padding: 1px 5px; border-radius: 4px; background: #1e3a5f; color: #7dd3fc; }
.tl-time  { font-size: 0.62rem; color: #475569; margin-left: auto; }
.tl-action{ font-size: 0.72rem; color: #64748b; font-family: monospace; margin-bottom: 2px; }
.tl-msg   { font-size: 0.76rem; color: #cbd5e1; }
</style>
