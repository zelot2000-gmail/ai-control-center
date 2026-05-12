<template>
  <div class="page">
    <!-- Header -->
    <div class="header">
      <h1 class="title">Jobs</h1>
      <button class="btn btn-refresh" :disabled="loading" @click="loadTasks">
        <span v-if="loading">⏳</span><span v-else>🔄</span> Refresh
      </button>
    </div>

    <!-- Summary bar -->
    <div class="summary" v-if="!loading && tasks.length">
      <span class="chip chip-total">{{ tasks.length }} total</span>
      <span class="chip chip-pending">{{ countByStatus('pending') }} pending</span>
      <span class="chip chip-running">{{ countByStatus('running') }} running</span>
      <span class="chip chip-exported">{{ countByStatus('exported') }} prompt ready</span>
      <span class="chip chip-agent-running">{{ countByStatus('agent_running') }} agent running</span>
      <span class="chip chip-completed">{{ countByStatus('completed') }} completed</span>
      <span class="chip chip-failed">{{ countByStatus('failed') }} failed</span>
    </div>

    <!-- Error -->
    <div class="error-box" v-if="fetchError">❌ {{ fetchError }}</div>

    <!-- Empty -->
    <div class="empty" v-if="!loading && !fetchError && tasks.length === 0">
      No tasks yet. Create a task via the Command page.
    </div>

    <!-- Task list -->
    <div class="task-list">
      <div
        v-for="task in sortedTasks"
        :key="task.task_id"
        class="task-card"
        :class="`card-${task.status}`"
      >
        <!-- Card header -->
        <div class="card-header">
          <span class="task-id">{{ shortId(task.task_id) }}</span>
          <span class="badge" :class="`badge-${task.status}`">{{ statusLabel(task.status) }}</span>
        </div>

        <!-- Intent -->
        <div class="intent" v-if="task.intent">{{ task.intent }}</div>

        <!-- Meta row -->
        <div class="meta">
          <span v-if="task.source">📱 {{ task.source }}</span>
          <span v-if="task.user">👤 {{ task.user }}</span>
          <span v-if="task.risk">⚡ risk {{ task.risk }}</span>
        </div>

        <!-- Agent Activity -->
        <div class="agent-activity" v-if="task.current_agent || task.active_agents?.length">
          <div class="aa-row">
            <span class="aa-icon">{{ agentIcon(task.current_agent || task.agents?.[0]) }}</span>
            <span class="aa-name">{{ task.current_agent || task.agents?.[0] }}</span>
            <span class="aa-step" v-if="task.current_step">· {{ task.current_step }}</span>
          </div>
          <div class="aa-chips" v-if="task.active_agents?.length > 1">
            <span v-for="a in task.active_agents" :key="a" class="aa-chip">{{ agentIcon(a) }} {{ a }}</span>
          </div>
        </div>

        <!-- Progress bar (non-terminal tasks except exported/completed) -->
        <div v-if="task.progress !== undefined && !['exported', 'completed'].includes(task.status)" class="progress-wrap">
          <div class="progress-bar" :class="`pb-${task.status}`" :style="{ width: `${task.progress}%` }"></div>
          <span class="progress-pct">{{ task.progress }}%</span>
        </div>

        <!-- Agent Running notice -->
        <div class="agent-running-notice" v-if="task.status === 'agent_running'">
          💬 กรุณา Copy Prompt ไปให้ Claude/Hermes ประมวลผล
        </div>

        <!-- Agents & Skills -->
        <div class="tags" v-if="task.agents?.length">
          <span class="tag tag-agent" v-for="a in task.agents" :key="a">{{ agentIcon(a) }} {{ a }}</span>
        </div>
        <div class="tags" v-if="task.skills?.length">
          <span class="tag tag-skill" v-for="s in task.skills" :key="s">{{ s }}</span>
          <span v-if="task.result?.rag_results_count > 0" class="tag tag-rag">
            📚 LLM Wiki · {{ task.result.rag_results_count }} results
          </span>
          <span v-if="task.result?.agent_run_id" class="tag tag-agent-runner" :class="`ar-${task.result.agent_run_status}`">
            🤖 {{ task.result.agent_run_mode || 'agent-runner' }}
          </span>
        </div>

        <!-- Attachment list -->
        <div class="attach-box" v-if="task.attachments?.length">
          <div class="attach-header">📎 {{ task.attachments.length }} ไฟล์แนบ</div>
          <div v-for="(f, i) in task.attachments" :key="i" class="attach-row">
            <span class="attach-fname">{{ f.filename || f.safe_filename }}</span>
            <span class="attach-mode" :class="`mode-${classifyMode(f.filename || f.safe_filename || '')}`">
              {{ classifyMode(f.filename || f.safe_filename || '') }}
            </span>
          </div>
        </div>

        <!-- Prompt path (exported/agent_running) -->
        <div class="export-path" v-if="task.result?.export_path && task.status !== 'completed'">
          📋 Prompt: <code>{{ shortPath(task.result.export_path) }}</code>
        </div>

        <!-- Final report preview (completed) -->
        <div class="report-preview" v-if="task.status === 'completed' && task.result?.final_report">
          <div class="report-label-row">
            <span class="report-label">Report by {{ task.result.report_source || 'agent' }}</span>
            <span
              v-if="task.result.verification_status"
              class="verify-badge"
              :class="`vbadge-${task.result.verification_status}`"
            >{{ verifyIcon(task.result.verification_status) }} {{ task.result.verification_status?.toUpperCase() }}</span>
          </div>
          <div class="report-snippet">
            {{ task.result.final_report.slice(0, 120) }}{{ task.result.final_report.length > 120 ? '…' : '' }}
          </div>
        </div>
        <!-- Verification badge only (no report text yet) -->
        <div class="verify-only" v-else-if="task.status === 'completed' && task.result?.verification_status">
          <span class="verify-badge" :class="`vbadge-${task.result.verification_status}`">
            {{ verifyIcon(task.result.verification_status) }} {{ task.result.verification_status?.toUpperCase() }}
          </span>
        </div>

        <!-- Warnings -->
        <div class="warnings" v-if="task.result?.warnings?.length">
          <span v-for="w in task.result.warnings" :key="w">⚠️ {{ w }}</span>
        </div>

        <!-- Error -->
        <div class="task-error" v-if="task.result?.error">❌ {{ task.result.error }}</div>

        <!-- Timestamps -->
        <div class="timestamps">
          <span v-if="task.created_at">Created: {{ fmtTime(task.created_at) }}</span>
          <span v-if="task.updated_at">Updated: {{ fmtTime(task.updated_at) }}</span>
        </div>

        <!-- Actions -->
        <div class="actions">
          <!-- pending/failed: Process -->
          <button
            v-if="task.status === 'pending' || task.status === 'failed'"
            class="btn btn-process"
            :disabled="processing[task.task_id]"
            @click="processTask(task.task_id)"
          >
            <span v-if="processing[task.task_id]">⏳ Processing…</span>
            <span v-else>▶ Process</span>
          </button>

          <!-- exported: View Prompt + Run Agent / Agent Runner actions -->
          <button
            v-if="task.status === 'exported'"
            class="btn btn-view"
            @click="viewPrompt(task.task_id)"
          >📄 View Prompt</button>

          <!-- Agent Runner prompt copy (when agent_run_id present) -->
          <button
            v-if="task.status === 'exported' && task.result?.agent_run_id"
            class="btn btn-agent-prompt"
            @click="copyAgentPrompt(task)"
          >📋 Copy Agent Prompt</button>

          <!-- Save Agent Report (replaces generic Run Agent for agent runner tasks) -->
          <button
            v-if="task.status === 'exported' && task.result?.agent_run_id && task.result?.agent_run_status === 'completed_prompt_ready'"
            class="btn btn-agent-save"
            @click="openAgentReport(task)"
          >📝 Save Agent Report</button>

          <!-- Agent Runner blocked: Approve -->
          <button
            v-if="task.result?.agent_run_status === 'blocked_approval_required'"
            class="btn btn-approve"
            @click="openAgentApprove(task)"
          >⛔ Approve Agent Run</button>

          <!-- View Agent Run detail -->
          <button
            v-if="task.result?.agent_run_id"
            class="btn btn-agent-run"
            @click="viewAgentRun(task.result.agent_run_id)"
          >🤖 View Agent Run</button>

          <button
            v-if="task.status === 'exported' && !task.result?.agent_run_id"
            class="btn btn-run-agent"
            :disabled="runningAgent[task.task_id]"
            @click="runAgent(task.task_id)"
          >
            <span v-if="runningAgent[task.task_id]">⏳</span>
            <span v-else>▶ Run Agent</span>
          </button>

          <!-- agent_running: View Prompt + Save Report -->
          <button
            v-if="task.status === 'agent_running'"
            class="btn btn-view"
            @click="viewPrompt(task.task_id)"
          >📄 View Prompt</button>

          <button
            v-if="task.status === 'agent_running'"
            class="btn btn-save"
            @click="openSaveReport(task.task_id)"
          >💾 Save Report</button>

          <!-- completed: View Report + Timeline + View Prompt -->
          <button
            v-if="task.status === 'completed'"
            class="btn btn-report"
            @click="viewReport(task)"
          >📊 View Report</button>

          <button
            v-if="task.agent_events?.length"
            class="btn btn-timeline"
            @click="viewTimeline(task)"
          >🕐 Timeline</button>

          <button
            v-if="task.status === 'completed'"
            class="btn btn-view"
            @click="viewPrompt(task.task_id)"
          >📄 View Prompt</button>
        </div>
      </div>
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
          <div class="save-error" v-if="saveModal.error">❌ {{ saveModal.error }}</div>
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
          <button class="btn btn-view" @click="closeSaveModal">Cancel</button>
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

        <!-- No report yet -->
        <div class="modal-body no-report-body" v-if="!reportModal.data?.final_report">
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
            <ul class="rs-list"><li v-for="item in reportModal.data.issues_found" :key="item">{{ item }}</li></ul>
          </div>
          <div class="report-section" v-if="reportModal.data.recommendations?.length">
            <div class="rs-title">💡 Recommendations</div>
            <ul class="rs-list"><li v-for="item in reportModal.data.recommendations" :key="item">{{ item }}</li></ul>
          </div>
          <div class="report-section" v-if="reportModal.data.next_actions?.length">
            <div class="rs-title">➡️ Next Actions</div>
            <ul class="rs-list"><li v-for="item in reportModal.data.next_actions" :key="item">{{ item }}</li></ul>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn btn-refresh" v-if="reportModal.data?.final_report" @click="copyReport">📋 Copy Report</button>
          <button class="btn btn-view" @click="closeReportModal">Close</button>
        </div>
      </div>
    </div>

    <!-- Agent Timeline Modal -->
    <div class="modal-overlay" v-if="timelineModal.open" @click.self="closeTimeline">
      <div class="modal">
        <div class="modal-header">
          <span>🕐 Agent Timeline — {{ shortId(timelineModal.taskId) }}</span>
          <button class="btn-close" @click="closeTimeline">✕</button>
        </div>
        <div class="modal-body">
          <div class="tl-empty" v-if="!timelineModal.events.length">No agent events yet.</div>
          <div v-for="(evt, i) in timelineModal.events" :key="i" class="tl-item">
            <div class="tl-icon">{{ agentIcon(evt.agent) }}</div>
            <div class="tl-body">
              <div class="tl-header">
                <span class="tl-agent">{{ evt.agent }}</span>
                <span class="tl-role">{{ evt.role }}</span>
                <span class="tl-time">{{ fmtTime(evt.timestamp) }}</span>
              </div>
              <div class="tl-action">{{ evt.action }}</div>
              <div class="tl-msg" v-if="evt.message">{{ evt.message }}</div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-view" @click="closeTimeline">Close</button>
        </div>
      </div>
    </div>

    <!-- Agent Run Detail Modal -->
    <div class="modal-overlay" v-if="agentRunModal.open" @click.self="closeAgentRun">
      <div class="modal">
        <div class="modal-header">
          <span>🤖 Agent Run Detail — {{ agentRunModal.data?.id?.slice(0,8) }}…</span>
          <button class="btn-close" @click="closeAgentRun">✕</button>
        </div>
        <div class="modal-body" v-if="agentRunModal.loading">⏳ Loading…</div>
        <div class="modal-body error-box" v-else-if="agentRunModal.error">❌ {{ agentRunModal.error }}</div>
        <div class="modal-body agent-run-detail" v-else-if="agentRunModal.data">
          <div class="ard-row"><span class="ard-label">Run ID</span><code class="ard-val">{{ agentRunModal.data.id }}</code></div>
          <div class="ard-row"><span class="ard-label">Task ID</span><code class="ard-val">{{ agentRunModal.data.job_id }}</code></div>
          <div class="ard-row"><span class="ard-label">Mode</span><span class="ard-val">{{ agentRunModal.data.runner_mode }}</span></div>
          <div class="ard-row">
            <span class="ard-label">Status</span>
            <span class="agent-runner-status" :class="`ar-${agentRunModal.data.status}`">{{ agentRunModal.data.status }}</span>
          </div>
          <div class="ard-row" v-if="agentRunModal.data.verification_status">
            <span class="ard-label">Verification</span>
            <span class="verify-badge" :class="`vbadge-${agentRunModal.data.verification_status}`">
              {{ verifyIcon(agentRunModal.data.verification_status) }} {{ agentRunModal.data.verification_status?.toUpperCase() }}
            </span>
          </div>
          <div class="ard-row"><span class="ard-label">Agent Role</span><span class="ard-val">{{ agentRunModal.data.agent_role }}</span></div>
          <div class="ard-row"><span class="ard-label">Workflow</span><span class="ard-val">{{ agentRunModal.data.workflow || '—' }}</span></div>
          <div class="ard-row"><span class="ard-label">RAG Results</span><span class="ard-val">{{ agentRunModal.data.rag_results_count ?? 0 }}</span></div>
          <div class="ard-row" v-if="agentRunModal.data.rag_top_path"><span class="ard-label">Top RAG Path</span><code class="ard-val">{{ agentRunModal.data.rag_top_path }}</code></div>
          <div class="ard-row" v-if="agentRunModal.data.prompt_path"><span class="ard-label">Prompt File</span><code class="ard-val ard-path">{{ agentRunModal.data.prompt_path }}</code></div>
          <div class="ard-row" v-if="agentRunModal.data.report_path"><span class="ard-label">Report File</span><code class="ard-val ard-path">{{ agentRunModal.data.report_path }}</code></div>
          <div class="ard-row"><span class="ard-label">Created</span><span class="ard-val">{{ fmtTime(agentRunModal.data.created_at) }}</span></div>
          <div class="ard-row" v-if="agentRunModal.data.completed_at"><span class="ard-label">Completed</span><span class="ard-val">{{ fmtTime(agentRunModal.data.completed_at) }}</span></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-view" @click="closeAgentRun">Close</button>
        </div>
      </div>
    </div>

    <!-- Agent Report Modal -->
    <div class="modal-overlay" v-if="agentRepModal.open" @click.self="agentRepModal.open = false">
      <div class="modal">
        <div class="modal-header">
          <span>📝 Save Agent Report — {{ agentRepModal.taskId?.slice(0,8) }}…</span>
          <button class="btn-close" @click="agentRepModal.open = false">✕</button>
        </div>
        <div class="modal-body">
          <p class="save-instruction">วาง <strong>ผลลัพธ์จาก Agent</strong> ที่นี่ — ห้ามวาง Prompt content หรือ Skill SOP</p>
          <div class="save-meta-row">
            <div class="save-field">
              <label class="field-label">Source</label>
              <select v-model="agentRepModal.report_source" class="agent-select">
                <option value="claude">Claude</option>
                <option value="chatgpt">ChatGPT</option>
                <option value="hermes">Hermes</option>
                <option value="manual">Manual</option>
              </select>
            </div>
            <div class="save-field">
              <label class="field-label">Verification</label>
              <select v-model="agentRepModal.verification_status" class="agent-select">
                <option value="">— (not set)</option>
                <option value="pass">✅ Pass</option>
                <option value="warning">⚠️ Warning</option>
                <option value="fail">❌ Fail</option>
              </select>
            </div>
          </div>
          <div class="save-field-full">
            <label class="field-label">Summary <span class="field-hint">(optional)</span></label>
            <input v-model="agentRepModal.report_summary" class="summary-input" placeholder="สรุปผลสั้นๆ" />
          </div>
          <div class="save-field-full">
            <label class="field-label">Final Report <span class="required">*</span></label>
            <textarea v-model="agentRepModal.report" class="report-textarea" rows="10" placeholder="วาง output จาก Claude/ChatGPT ที่นี่…"></textarea>
          </div>
          <div class="save-error" v-if="agentRepModal.error">❌ {{ agentRepModal.error }}</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-save" :disabled="!agentRepModal.report.trim() || agentRepModal.loading" @click="submitAgentReport">
            <span v-if="agentRepModal.loading">⏳ Saving…</span>
            <span v-else>💾 Save Report</span>
          </button>
          <button class="btn btn-view" @click="agentRepModal.open = false">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Agent Runner Approve Modal -->
    <div class="modal-overlay" v-if="agentApproveModal.open" @click.self="agentApproveModal.open = false">
      <div class="modal">
        <div class="modal-header">
          <span>⛔ Approve Agent Run — {{ agentApproveModal.taskId?.slice(0,8) }}…</span>
          <button class="btn-close" @click="agentApproveModal.open = false">✕</button>
        </div>
        <div class="modal-body">
          <div v-if="agentApproveModal.reason" class="approve-reason">🔒 {{ agentApproveModal.reason }}</div>
          <p class="approve-instruction">
            Required: <code>{{ agentApproveModal.required_phrase }}</code>
          </p>
          <div class="save-field-full">
            <label class="field-label">Approval Phrase <span class="required">*</span></label>
            <input
              v-model="agentApproveModal.phrase"
              class="summary-input"
              :placeholder="agentApproveModal.required_phrase"
            />
          </div>
          <div class="save-field-full">
            <label class="field-label">Approved By</label>
            <input v-model="agentApproveModal.approved_by" class="summary-input" placeholder="ชื่อผู้อนุมัติ" />
          </div>
          <div class="save-error" v-if="agentApproveModal.error">❌ {{ agentApproveModal.error }}</div>
        </div>
        <div class="modal-footer">
          <button
            class="btn btn-process"
            :disabled="!agentApproveModal.phrase.trim() || agentApproveModal.loading"
            @click="submitAgentApprove"
          >
            <span v-if="agentApproveModal.loading">⏳ Approving…</span>
            <span v-else>✅ Approve & Run Agent</span>
          </button>
          <button class="btn btn-view" @click="agentApproveModal.open = false">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Prompt Modal -->
    <div class="modal-overlay" v-if="promptModal.open" @click.self="closePromptModal">
      <div class="modal">
        <div class="modal-header">
          <span>Prompt — {{ shortId(promptModal.taskId) }}</span>
          <button class="btn-close" @click="closePromptModal">✕</button>
        </div>
        <div class="modal-body" v-if="promptModal.loading">⏳ Loading…</div>
        <div class="modal-body error-box" v-else-if="promptModal.error">❌ {{ promptModal.error }}</div>
        <pre class="modal-body prompt-content" v-else>{{ promptModal.content }}</pre>
        <div class="modal-footer">
          <button class="btn btn-refresh" @click="copyPrompt">📋 Copy</button>
          <button class="btn btn-view" @click="closePromptModal">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const config = useRuntimeConfig()
const API    = config.public.apiBase
const WORKER = config.public.workerBase

const tasks      = ref([])
const loading    = ref(false)
const fetchError = ref('')
const processing = ref({})
const runningAgent = ref({})

const AGENT_ICONS = {
  'manager': '🧭', 'programmer': '💻', 'devops': '🐳',
  'administrator': '🛡', 'designer': '🎨', 'qa': '🧪',
  'security': '🔐', 'rag-curator': '📚', 'observer': '👁',
  'research': '🔬', 'worker': '⚙️',
}
const agentIcon = (a) => AGENT_ICONS[a] || '🤖'

const STATUS_LABELS = {
  pending: 'PENDING', running: 'RUNNING', exporting: 'EXPORTING',
  exported: 'PROMPT READY', agent_running: 'AGENT RUNNING',
  completed: 'COMPLETED', failed: 'FAILED',
  blocked: 'BLOCKED', waiting_approval: 'WAIT APPROVAL',
  completed_prompt_ready: 'PROMPT READY', completed_report_saved: 'REPORT SAVED',
}
const statusLabel = (s) => STATUS_LABELS[s] || (s || '').toUpperCase()

const promptModal    = ref({ open: false, taskId: '', loading: false, error: '', content: '' })
const saveModal      = ref({ open: false, taskId: '', report: '', report_source: 'claude', report_summary: '', verification_status: '', loading: false, error: '' })
const reportModal    = ref({ open: false, taskId: '', data: null })
const timelineModal  = ref({ open: false, taskId: '', events: [] })
const agentRunModal      = ref({ open: false, runId: '', loading: false, error: '', data: null })
const agentRepModal      = ref({ open: false, taskId: '', runId: '', report: '', report_source: 'claude', report_summary: '', verification_status: '', loading: false, error: '' })
const agentApproveModal  = ref({ open: false, taskId: '', phrase: '', approved_by: 'chain', required_phrase: '', reason: '', loading: false, error: '' })

// ── Helpers ───────────────────────────────────────────────────────────────
const shortId   = (id) => id ? id.slice(0, 8) + '…' : '—'
const shortPath = (p)  => p  ? p.replace('/app/data/exports/', '') : ''
const fmtTime   = (ts) => {
  if (!ts) return ''
  try { return new Date(ts).toLocaleString('th-TH', { dateStyle: 'short', timeStyle: 'short' }) }
  catch { return ts }
}
const countByStatus = (s) => tasks.value.filter(t => t.status === s).length
const sortedTasks = computed(() =>
  [...tasks.value].sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
)

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
  if (report.includes('PASS / WARNING / FAIL')) warns.push('กรุณาระบุ Verification Status เป็น PASS, WARNING หรือ FAIL')
  if (/(?<!\.)\.\.\.(?!\.)/.test(report)) warns.push('มี placeholder "..." ในรายงาน กรุณากรอกให้ครบ')
  return warns
}

// ── Fetch tasks ───────────────────────────────────────────────────────────
async function loadTasks() {
  loading.value = true
  fetchError.value = ''
  try {
    const res = await fetch(`${API}/tasks`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    tasks.value = data.tasks || []
  } catch (e) {
    fetchError.value = `Cannot reach mobile-gateway (${API}): ${e.message}`
  } finally {
    loading.value = false
  }
}

// ── Process task (pending/failed → exported) ──────────────────────────────
async function processTask(taskId) {
  processing.value = { ...processing.value, [taskId]: true }
  try {
    const res = await fetch(`${WORKER}/process-task`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId }),
    })
    const data = await res.json()
    if (!res.ok) alert(`Process failed: ${data.detail || res.status}`)
    await loadTasks()
  } catch (e) {
    alert(`Cannot reach worker (${WORKER}): ${e.message}`)
  } finally {
    processing.value = { ...processing.value, [taskId]: false }
  }
}

// ── Run Agent (exported → agent_running) ──────────────────────────────────
async function runAgent(taskId) {
  runningAgent.value = { ...runningAgent.value, [taskId]: true }
  try {
    const res = await fetch(`${API}/tasks/${taskId}/run-agent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      alert(`Run Agent ไม่สำเร็จ: ${err.detail || res.status}`)
    } else {
      await loadTasks()
    }
  } catch (e) {
    alert(`Cannot reach API: ${e.message}`)
  } finally {
    runningAgent.value = { ...runningAgent.value, [taskId]: false }
  }
}

// ── Save Report (agent_running → completed) ───────────────────────────────
function openSaveReport(taskId) {
  saveModal.value = {
    open: true, taskId,
    report: REPORT_TEMPLATE,
    report_source: 'claude', report_summary: '', verification_status: '',
    loading: false, error: '',
  }
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
    saveModal.value.open = false
    await loadTasks()
  } catch (e) {
    saveModal.value.error = e.message
  } finally {
    saveModal.value.loading = false
  }
}

function closeSaveModal() { saveModal.value.open = false }

// ── View Report ───────────────────────────────────────────────────────────
function viewReport(task) {
  reportModal.value = {
    open: true,
    taskId: task.task_id,
    data: task.result || {},
  }
}

function closeReportModal() { reportModal.value.open = false }

async function copyReport() {
  try {
    await navigator.clipboard.writeText(reportModal.value.data?.final_report || '')
    alert('Copied!')
  } catch { alert('Copy not supported in this browser') }
}

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

const fmtFull    = (ts) => {
  if (!ts) return '—'
  try { return new Date(ts).toLocaleString('th-TH', { dateStyle: 'medium', timeStyle: 'short' }) }
  catch { return ts }
}
const verifyIcon = (v) => ({ pass: '✅', warning: '⚠️', fail: '❌' }[v] || '')

// ── View Prompt ───────────────────────────────────────────────────────────
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

function closePromptModal() { promptModal.value.open = false }

async function copyPrompt() {
  try {
    await navigator.clipboard.writeText(promptModal.value.content)
    alert('Copied!')
  } catch { alert('Copy not supported in this browser') }
}

// ── Timeline ──────────────────────────────────────────────────────────────
function viewTimeline(task) {
  timelineModal.value = { open: true, taskId: task.task_id, events: task.agent_events || [] }
}
function closeTimeline() { timelineModal.value.open = false }

// ── Agent Run Detail ──────────────────────────────────────────────────────
async function viewAgentRun(runId) {
  agentRunModal.value = { open: true, runId, loading: true, error: '', data: null }
  try {
    const res = await fetch(`${WORKER}/agent-runs/${runId}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    agentRunModal.value.data = await res.json()
  } catch (e) {
    agentRunModal.value.error = `Cannot load agent run: ${e.message}`
  } finally {
    agentRunModal.value.loading = false
  }
}
function closeAgentRun() { agentRunModal.value.open = false }

// ── Copy Agent Prompt ─────────────────────────────────────────────────────
async function copyAgentPrompt(task) {
  const runId = task.result?.agent_run_id
  if (!runId) return
  try {
    const res = await fetch(`${WORKER}/agent-runs/${runId}/prompt`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    await navigator.clipboard.writeText(data.content || '')
    alert('✅ Agent Prompt copied to clipboard')
  } catch (e) {
    alert(`Copy ไม่สำเร็จ: ${e.message}`)
  }
}

// ── Save Agent Report ─────────────────────────────────────────────────────
function openAgentReport(task) {
  agentRepModal.value = {
    open: true,
    taskId: task.task_id,
    runId: task.result?.agent_run_id,
    report: '', report_source: 'claude', report_summary: '', verification_status: '',
    loading: false, error: '',
  }
}

async function submitAgentReport() {
  if (!agentRepModal.value.report.trim()) return
  const warns = validateReport(agentRepModal.value.report)
  if (warns.length > 0) {
    const ok = confirm(`⚠️ รายการที่ยังไม่ครบ:\n${warns.map(w => '• ' + w).join('\n')}\n\nต้องการบันทึกต่อไปหรือไม่?`)
    if (!ok) return
  }
  agentRepModal.value.loading = true
  agentRepModal.value.error = ''
  try {
    const body = {
      final_report: agentRepModal.value.report,
      report_source: agentRepModal.value.report_source,
      summary: agentRepModal.value.report_summary.trim() || undefined,
      verification_status: agentRepModal.value.verification_status || undefined,
    }
    const res = await fetch(`${WORKER}/agent-runs/${agentRepModal.value.runId}/report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      agentRepModal.value.error = err.detail || `HTTP ${res.status}`
      return
    }
    agentRepModal.value.open = false
    await loadTasks()
  } catch (e) {
    agentRepModal.value.error = e.message
  } finally {
    agentRepModal.value.loading = false
  }
}

// ── Agent Runner: Approve ─────────────────────────────────────────────────
function openAgentApprove(task) {
  agentApproveModal.value = {
    open: true,
    taskId: task.task_id,
    phrase: '',
    approved_by: 'chain',
    required_phrase: task.result?.approval_phrase || '',
    reason: task.result?.agent_approval_reason || '',
    loading: false,
    error: '',
  }
}

async function submitAgentApprove() {
  if (!agentApproveModal.value.phrase.trim()) return
  agentApproveModal.value.loading = true
  agentApproveModal.value.error = ''
  try {
    const approveRes = await fetch(`${API}/tasks/${agentApproveModal.value.taskId}/approval`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        approval_phrase: agentApproveModal.value.phrase.trim(),
        approved_by: agentApproveModal.value.approved_by.trim() || 'unknown',
      }),
    })
    if (!approveRes.ok) {
      const err = await approveRes.json().catch(() => ({}))
      agentApproveModal.value.error = err.detail || `HTTP ${approveRes.status}`
      return
    }

    const runRes = await fetch(`${WORKER}/agent-runs/from-task/${agentApproveModal.value.taskId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    if (!runRes.ok) {
      const err = await runRes.json().catch(() => ({}))
      agentApproveModal.value.error = err.detail || `HTTP ${runRes.status}`
      return
    }

    agentApproveModal.value.open = false
    await loadTasks()
    alert('✅ Agent Runner approved and started!')
  } catch (e) {
    agentApproveModal.value.error = e.message
  } finally {
    agentApproveModal.value.loading = false
  }
}

// ── Init ──────────────────────────────────────────────────────────────────
onMounted(loadTasks)
</script>

<style scoped>
*, *::before, *::after { box-sizing: border-box; }

.page {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #0f172a;
  color: #e2e8f0;
  min-height: 100vh;
  padding: 1rem;
  max-width: 680px;
  margin: 0 auto;
}

/* Header */
.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.title  { font-size: 1.5rem; font-weight: 700; color: #f1f5f9; margin: 0; }

/* Summary */
.summary { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 1rem; }
.chip {
  font-size: 0.72rem; font-weight: 600;
  padding: 0.2rem 0.6rem; border-radius: 999px;
}
.chip-total        { background: #334155; color: #94a3b8; }
.chip-pending      { background: #1e293b; color: #94a3b8; }
.chip-running      { background: #1e3a5f; color: #60a5fa; }
.chip-exported     { background: #14532d; color: #4ade80; }
.chip-agent-running{ background: #431407; color: #fb923c; }
.chip-completed    { background: #064e3b; color: #34d399; }
.chip-failed       { background: #450a0a; color: #f87171; }

/* Buttons */
.btn {
  padding: 0.45rem 0.9rem; border-radius: 8px; border: none;
  font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s;
}
.btn:disabled   { opacity: 0.5; cursor: not-allowed; }
.btn-refresh    { background: #334155; color: #94a3b8; }
.btn-process    { background: #1d4ed8; color: #fff; }
.btn-view       { background: #0f766e; color: #fff; }
.btn-run-agent      { background: #1d4ed8; color: #fff; }
.btn-save           { background: #c2410c; color: #fff; }
.btn-report         { background: #065f46; color: #fff; }
.btn-timeline       { background: #1e3a5f; color: #93c5fd; }
.btn-agent-prompt   { background: #4c1d95; color: #e9d5ff; }
.btn-agent-save     { background: #6d28d9; color: #fff; }
.btn-agent-run      { background: #2e1a4a; color: #c4b5fd; }
.btn-approve        { background: #b45309; color: #fff; }

/* Error / Empty */
.error-box {
  background: #450a0a; color: #fca5a5;
  padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1rem; font-size: 0.85rem;
}
.empty { color: #64748b; text-align: center; padding: 3rem 1rem; font-size: 0.9rem; }

/* Task list */
.task-list { display: flex; flex-direction: column; gap: 0.75rem; }

.task-card {
  background: #1e293b;
  border-radius: 12px;
  padding: 1rem;
  border-left: 4px solid #334155;
}
.card-pending       { border-left-color: #475569; }
.card-running       { border-left-color: #3b82f6; }
.card-exporting     { border-left-color: #8b5cf6; }
.card-exported      { border-left-color: #22c55e; }
.card-agent_running { border-left-color: #f97316; }
.card-completed     { border-left-color: #059669; }
.card-failed        { border-left-color: #ef4444; }

.card-header {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;
}
.task-id { font-family: monospace; font-size: 0.8rem; color: #64748b; }

/* Status badge */
.badge {
  font-size: 0.7rem; font-weight: 700;
  padding: 0.2rem 0.55rem; border-radius: 999px;
  text-transform: uppercase; letter-spacing: 0.05em;
}
.badge-pending          { background: #334155; color: #94a3b8; }
.badge-running          { background: #1e3a5f; color: #60a5fa; }
.badge-exporting        { background: #2e1065; color: #c4b5fd; }
.badge-exported         { background: #14532d; color: #4ade80; }
.badge-agent_running    { background: #431407; color: #fb923c; }
.badge-completed        { background: #064e3b; color: #34d399; }
.badge-failed           { background: #450a0a; color: #f87171; }
.badge-blocked,
.badge-waiting_approval { background: #422006; color: #fbbf24; }

.intent { font-size: 0.92rem; color: #f1f5f9; margin-bottom: 0.45rem; line-height: 1.4; }

.meta { display: flex; flex-wrap: wrap; gap: 0.6rem; font-size: 0.75rem; color: #64748b; margin-bottom: 0.45rem; }

.tags { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.4rem; }
.tag  { font-size: 0.7rem; padding: 0.15rem 0.5rem; border-radius: 6px; }
.tag-agent { background: #1e3a5f; color: #93c5fd; }
.tag-skill { background: #1a2e1a; color: #86efac; }
.tag-rag          { background: #1e3a5f; color: #60a5fa; font-weight: 600; }
.tag-agent-runner { background: #2e1a4a; color: #c4b5fd; font-weight: 600; }
.tag-agent-runner.ar-completed_prompt_ready { background: #064e3b; color: #6ee7b7; }
.tag-agent-runner.ar-waiting_for_hermes_manual_execution { background: #451a03; color: #fcd34d; }
.tag-agent-runner.ar-completed { background: #064e3b; color: #6ee7b7; }
.tag-agent-runner.ar-failed              { background: #450a0a; color: #fca5a5; }
.tag-agent-runner.ar-completed_report_saved { background: #052e16; color: #4ade80; font-weight: 700; }

/* Agent Run Detail */
.agent-run-detail { display: flex; flex-direction: column; gap: 8px; }
.ard-row  { display: flex; align-items: flex-start; gap: 8px; font-size: 0.82rem; }
.ard-label { min-width: 100px; color: #94a3b8; font-weight: 600; flex-shrink: 0; }
.ard-val   { color: #e2e8f0; word-break: break-all; }
.ard-path  { font-size: 0.72rem; color: #a78bfa; }
.agent-runner-status { font-size: 0.75rem; font-weight: 600; padding: 2px 6px; border-radius: 4px; }
.ar-completed_prompt_ready  { background: #064e3b; color: #6ee7b7; }
.ar-completed_report_saved  { background: #052e16; color: #4ade80; }
.ar-waiting_for_hermes_manual_execution { background: #451a03; color: #fcd34d; }
.ar-failed  { background: #450a0a; color: #fca5a5; }
.ar-running { background: #172554; color: #93c5fd; }
.ar-blocked_approval_required { background: #422006; color: #fbbf24; font-weight: 700; }
.tag-agent-runner.ar-blocked_approval_required { background: #422006; color: #fbbf24; }

.attach-box {
  background: #0d1b2e; border: 1px solid #1e3a5f;
  border-radius: 8px; padding: 6px 10px; margin-bottom: 0.4rem;
}
.attach-header {
  font-size: 0.72rem; font-weight: 700; color: #60a5fa; margin-bottom: 4px;
}
.attach-row {
  display: flex; align-items: center; gap: 6px; padding: 1px 0;
}
.attach-fname {
  font-size: 0.72rem; color: #94a3b8;
  max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.attach-mode {
  font-size: 0.62rem; font-weight: 600;
  padding: 1px 5px; border-radius: 4px; white-space: nowrap; flex-shrink: 0;
}
.mode-text-extract        { background: #064e3b; color: #6ee7b7; }
.mode-document-extract    { background: #1e3a5f; color: #93c5fd; }
.mode-spreadsheet-extract { background: #2e1065; color: #c4b5fd; }
.mode-presentation-extract{ background: #422006; color: #fbbf24; }
.mode-vision-required     { background: #500724; color: #f9a8d4; }
.mode-unsupported         { background: #1e293b; color: #475569; }
.export-path { font-size: 0.75rem; color: #4ade80; margin-bottom: 0.35rem; word-break: break-all; }
.export-path code { font-family: monospace; }

/* Agent Running notice */
.agent-running-notice {
  font-size: 0.8rem;
  color: #fb923c;
  background: #1c0a00;
  border: 1px solid #431407;
  border-radius: 6px;
  padding: 6px 10px;
  margin-bottom: 0.45rem;
}

/* Completed report preview */
.report-preview {
  background: #022c22;
  border: 1px solid #065f46;
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 0.45rem;
}
.report-label-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 4px; }
.report-label  { font-size: 0.75rem; font-weight: 700; color: #34d399; }
.report-snippet { font-size: 0.78rem; color: #a7f3d0; line-height: 1.5; }

.verify-only { margin-bottom: 0.45rem; }
.verify-badge {
  font-size: 0.7rem; font-weight: 700; padding: 2px 8px;
  border-radius: 999px; text-transform: uppercase; letter-spacing: 0.04em; display: inline-block;
}
.vbadge-pass    { background: #14532d; color: #4ade80; }
.vbadge-warning { background: #422006; color: #fbbf24; }
.vbadge-fail    { background: #450a0a; color: #f87171; }

.warnings { display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.75rem; color: #fbbf24; margin-bottom: 0.35rem; }
.task-error { font-size: 0.75rem; color: #f87171; margin-bottom: 0.35rem; }

.timestamps { display: flex; flex-wrap: wrap; gap: 0.75rem; font-size: 0.7rem; color: #475569; margin-bottom: 0.6rem; }

.actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }

/* Agent activity */
.agent-activity { background: #0f172a; border: 1px solid #1e3a5f; border-radius: 8px; padding: 6px 10px; margin-bottom: 0.45rem; }
.aa-row   { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.aa-icon  { font-size: 1rem; }
.aa-name  { font-size: 0.82rem; font-weight: 600; color: #93c5fd; }
.aa-step  { font-size: 0.75rem; color: #64748b; }
.aa-chips { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
.aa-chip  { font-size: 0.67rem; padding: 1px 7px; background: #1e3a5f; color: #93c5fd; border-radius: 999px; }

/* Progress bar */
.progress-wrap { display: flex; align-items: center; gap: 8px; margin-bottom: 0.45rem; }
.progress-bar  { flex: 1; height: 5px; border-radius: 999px; transition: width 0.4s ease; }
.pb-pending         { background: #475569; }
.pb-running         { background: #3b82f6; }
.pb-exporting       { background: #8b5cf6; }
.pb-agent_running   { background: #f97316; }
.pb-failed          { background: #ef4444; }
.pb-blocked,
.pb-waiting_approval{ background: #f59e0b; }
.progress-pct { font-size: 0.7rem; color: #64748b; flex-shrink: 0; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.7);
  display: flex; align-items: flex-end; justify-content: center; z-index: 100; padding: 0;
}
@media (min-width: 600px) { .modal-overlay { align-items: center; padding: 1rem; } }

.modal {
  background: #1e293b; width: 100%; max-width: 660px; max-height: 85vh;
  border-radius: 16px 16px 0 0; display: flex; flex-direction: column; overflow: hidden;
}
@media (min-width: 600px) { .modal { border-radius: 16px; } }

.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.9rem 1rem; border-bottom: 1px solid #334155;
  font-weight: 600; font-size: 0.9rem; color: #f1f5f9;
}
.btn-close { background: none; border: none; color: #64748b; font-size: 1.1rem; cursor: pointer; padding: 0.2rem 0.4rem; }

.modal-body { flex: 1; overflow-y: auto; padding: 1rem; }

.prompt-content {
  font-family: monospace; font-size: 0.78rem; color: #cbd5e1;
  white-space: pre-wrap; word-break: break-word; margin: 0; line-height: 1.6;
}

.modal-footer {
  display: flex; gap: 0.5rem; padding: 0.75rem 1rem;
  border-top: 1px solid #334155; justify-content: flex-end; align-items: center;
}

.report-by { font-size: 0.78rem; color: #64748b; margin-right: auto; }

/* Save report modal */
.save-instruction { font-size: 0.82rem; color: #94a3b8; margin-bottom: 0.75rem; }
.save-instruction strong { color: #e2e8f0; }
.approve-reason {
  background: #450a0a; color: #fca5a5;
  padding: 0.5rem 0.75rem; border-radius: 6px;
  font-size: 0.82rem; margin-bottom: 0.75rem;
}
.approve-instruction {
  font-size: 0.82rem; color: #94a3b8; margin-bottom: 0.75rem; line-height: 1.6;
}
.approve-instruction code { color: #fbbf24; font-weight: 700; }
.save-meta-row   { display: flex; gap: 0.75rem; margin-bottom: 0.6rem; flex-wrap: wrap; }
.save-field      { display: flex; flex-direction: column; gap: 3px; flex: 1; min-width: 120px; }
.save-field-full { display: flex; flex-direction: column; gap: 3px; margin-bottom: 0.6rem; }
.field-label     { font-size: 0.75rem; color: #64748b; font-weight: 600; }
.field-hint      { font-weight: 400; color: #475569; }
.required        { color: #f87171; }
.agent-select {
  background: #0f172a; color: #e2e8f0; border: 1px solid #334155;
  border-radius: 6px; padding: 0.3rem 0.6rem; font-size: 0.82rem;
}
.summary-input {
  width: 100%; background: #0f172a; color: #e2e8f0;
  border: 1px solid #334155; border-radius: 6px;
  padding: 0.4rem 0.6rem; font-size: 0.82rem; box-sizing: border-box;
}
.report-textarea {
  width: 100%; background: #0f172a; color: #e2e8f0;
  border: 1px solid #334155; border-radius: 8px; padding: 0.75rem;
  font-family: monospace; font-size: 0.78rem; line-height: 1.6; resize: vertical;
}
.save-error { color: #fca5a5; font-size: 0.82rem; margin-top: 0.5rem; }

/* Report modal */
.no-report-body {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 0.5rem; padding: 3rem 1rem;
}
.no-report-icon { font-size: 2rem; }
.no-report-text { font-size: 1rem; font-weight: 600; color: #94a3b8; }
.no-report-hint { font-size: 0.82rem; color: #475569; }

.report-body    { overflow-y: auto; }
.report-meta-block {
  background: #0f172a; border: 1px solid #334155; border-radius: 8px;
  padding: 0.75rem; margin-bottom: 1rem; display: flex; flex-direction: column; gap: 5px;
}
.rmi { display: flex; align-items: center; gap: 8px; font-size: 0.8rem; }
.rml { color: #64748b; font-weight: 600; min-width: 80px; }
.rmv { color: #e2e8f0; }

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
.tl-header{ display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 2px; }
.tl-agent { font-size: 0.8rem; font-weight: 700; color: #93c5fd; }
.tl-role  { font-size: 0.65rem; padding: 1px 5px; border-radius: 4px; background: #1e3a5f; color: #7dd3fc; }
.tl-time  { font-size: 0.65rem; color: #475569; margin-left: auto; }
.tl-action{ font-size: 0.75rem; color: #64748b; font-family: monospace; margin-bottom: 2px; }
.tl-msg   { font-size: 0.78rem; color: #cbd5e1; }
</style>
