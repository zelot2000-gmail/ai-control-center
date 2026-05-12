<template>
  <div class="page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">Knowledge Base</h1>
        <p class="page-subtitle">LLM Wiki — ฐานความรู้กลางของระบบ ai-control-center</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="showSearch = !showSearch">
          🔍 Search Wiki
        </button>
        <button class="btn btn-primary" @click="showIngest = true">
          ⚡ Ingest Wiki
        </button>
      </div>
    </div>

    <!-- Search Bar -->
    <div class="search-bar" v-if="showSearch">
      <input
        v-model="searchQuery"
        class="search-input"
        type="text"
        placeholder="ค้นหาใน Knowledge Base... (เช่น: RAG chunking, Qdrant, prompt pattern)"
        @keydown.enter="runSearch"
      />
      <button class="btn btn-primary btn-sm" @click="runSearch" :disabled="!searchQuery.trim() || searching">
        <span v-if="searching">⏳</span>
        <span v-else>ค้นหา</span>
      </button>
      <button class="btn btn-ghost btn-sm" @click="clearSearch">ล้าง</button>
    </div>

    <!-- Search Results -->
    <div class="search-results" v-if="searchResults.length || searchError">
      <div class="section-title">ผลการค้นหา "{{ lastQuery }}" — {{ searchResults.length }} รายการ</div>
      <div v-if="searchError" class="error-box">{{ searchError }}</div>
      <div v-else-if="searchResults.length === 0" class="empty-results">
        ไม่พบเอกสารที่ตรงกับ "{{ lastQuery }}"
      </div>
      <div v-else class="result-list">
        <div v-for="(r, i) in searchResults" :key="i" class="result-card">
          <div class="result-header">
            <div class="result-meta">
              <span class="result-title">{{ r.title || r.payload?.title || 'Untitled' }}</span>
              <span class="result-category">{{ r.category || r.payload?.category || '' }}</span>
            </div>
            <span class="result-score">{{ ((r.score || 0) * 100).toFixed(0) }}%</span>
          </div>
          <div class="result-path">📄 {{ r.path || r.payload?.path || 'unknown' }}</div>
          <div v-if="r.heading_path || r.payload?.heading_path" class="result-heading">
            🔗 {{ r.heading_path || r.payload?.heading_path }}
          </div>
          <p class="result-text">{{ r.snippet || r.payload?.text || '' }}</p>
          <div v-if="(r.tags || r.payload?.tags || []).length" class="result-tags">
            <span v-for="tag in (r.tags || r.payload?.tags || [])" :key="tag" class="result-tag">{{ tag }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Wiki Sections -->
    <div class="wiki-grid">
      <div
        v-for="section in wikiSections"
        :key="section.id"
        class="wiki-section"
      >
        <div class="section-header">
          <span class="section-icon">{{ section.icon }}</span>
          <div>
            <div class="section-name">{{ section.name }}</div>
            <div class="section-desc">{{ section.description }}</div>
          </div>
        </div>
        <ul class="doc-list">
          <li v-for="doc in section.docs" :key="doc.file" class="doc-item">
            <span class="doc-icon">📄</span>
            <div class="doc-info">
              <div class="doc-title">{{ doc.title }}</div>
              <div class="doc-path">docs/wiki/{{ section.id }}/{{ doc.file }}</div>
            </div>
            <span class="doc-tag" :class="`tag-${doc.status}`">{{ doc.status }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- Stats Bar -->
    <div class="stats-bar">
      <div class="stat">
        <span class="stat-num">{{ totalDocs }}</span>
        <span class="stat-label">เอกสารทั้งหมด</span>
      </div>
      <div class="stat">
        <span class="stat-num">{{ wikiSections.length }}</span>
        <span class="stat-label">หมวดหมู่</span>
      </div>
      <div class="stat">
        <span class="stat-num stat-ok">{{ ingestReport?.chunks_added ?? '–' }}</span>
        <span class="stat-label">Chunks ใน RAG</span>
      </div>
      <div class="stat">
        <span class="stat-num stat-ok">{{ ingestReport?.files_ingested ?? '–' }}</span>
        <span class="stat-label">ไฟล์ที่ Ingest</span>
      </div>
      <div class="stat">
        <span class="stat-num" :class="collectionStatus === 'ok' ? 'stat-ok' : 'stat-warn'">
          {{ collectionStatus === 'ok' ? '✅' : '⚠️' }}
        </span>
        <span class="stat-label">RAG Collection</span>
      </div>
    </div>

    <!-- Ingest Modal -->
    <div class="modal-backdrop" v-if="showIngest" @click.self="showIngest = false">
      <div class="modal">
        <div class="modal-header">
          <span class="modal-title">⚡ Ingest Wiki → RAG</span>
          <button class="modal-close" @click="showIngest = false">✕</button>
        </div>
        <div class="modal-body">
          <p class="ingest-desc">
            Ingest เอกสารใน <code>docs/wiki/</code> เข้า Qdrant Collection <code>wiki</code><br>
            เพื่อให้ Agent ค้นหาความรู้ได้ผ่าน RAG Search
          </p>
          <div class="ingest-steps">
            <div class="step">1. Scan docs/wiki/**/*.md ทุกไฟล์</div>
            <div class="step">2. Parse frontmatter + heading-based chunking</div>
            <div class="step">3. Upsert chunks → Qdrant aicc_wiki (idempotent)</div>
          </div>

          <div v-if="ingestReport" class="ingest-report">
            <div class="report-row"><span class="report-label">ไฟล์ที่พบ:</span><span>{{ ingestReport.files_found }}</span></div>
            <div class="report-row"><span class="report-label">ไฟล์ที่ Ingest:</span><span class="stat-ok">{{ ingestReport.files_ingested }}</span></div>
            <div class="report-row"><span class="report-label">Chunks เพิ่ม:</span><span class="stat-ok">{{ ingestReport.chunks_added }}</span></div>
            <div class="report-row"><span class="report-label">Chunks ข้าม:</span><span>{{ ingestReport.chunks_skipped }}</span></div>
            <div v-if="ingestReport.errors?.length" class="report-row">
              <span class="report-label">Errors:</span><span class="stat-warn">{{ ingestReport.errors.length }}</span>
            </div>
            <div class="report-row">
              <span class="report-label">ครั้งล่าสุด:</span>
              <span class="report-time">{{ ingestReport.finished_at ? new Date(ingestReport.finished_at).toLocaleString('th') : '–' }}</span>
            </div>
          </div>

          <div class="ingest-endpoints">
            <div class="endpoint-row">
              <span class="endpoint-label">Ingest:</span>
              <code>POST {{ ragBaseUrl }}/ingest/wiki</code>
            </div>
            <div class="endpoint-row">
              <span class="endpoint-label">Search:</span>
              <code>POST {{ ragBaseUrl }}/search/wiki</code>
            </div>
            <div class="endpoint-row">
              <span class="endpoint-label">Report:</span>
              <code>GET {{ ragBaseUrl }}/ingest/reports/latest</code>
            </div>
          </div>

          <div v-if="ingestLog.length" class="ingest-log">
            <div v-for="(line, i) in ingestLog" :key="i" class="log-line" :class="line.type">
              {{ line.msg }}
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" @click="showIngest = false">ยกเลิก</button>
          <button
            class="btn btn-primary"
            @click="runIngest"
            :disabled="ingesting"
          >
            <span v-if="ingesting">⏳ กำลัง Ingest...</span>
            <span v-else>⚡ เริ่ม Ingest</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const ragBaseUrl = 'http://127.0.0.1:8090'
const gwBaseUrl  = 'http://127.0.0.1:8088'

const showSearch     = ref(false)
const showIngest     = ref(false)
const searchQuery    = ref('')
const lastQuery      = ref('')
const searching      = ref(false)
const searchResults  = ref([])
const searchError    = ref('')
const ingesting      = ref(false)
const ingestLog      = ref([])
const ingestReport   = ref(null)
const collectionStatus = ref('unknown')

const wikiSections = [
  {
    id: 'llm',
    icon: '🧠',
    name: 'LLM',
    description: 'Model selection, prompt engineering, context management',
    docs: [
      { file: 'model-selection.md',   title: 'Model Selection Guide',    status: 'stable' },
      { file: 'prompt-patterns.md',   title: 'Prompt Patterns',          status: 'stable' },
      { file: 'context-engineering.md', title: 'Context Engineering',    status: 'stable' },
      { file: 'embedding-models.md',  title: 'Embedding Models',         status: 'stable' },
    ],
  },
  {
    id: 'rag',
    icon: '📚',
    name: 'RAG',
    description: 'Chunking strategy, retrieval quality, Qdrant',
    docs: [
      { file: 'chunking-strategy.md', title: 'Chunking Strategy',        status: 'stable' },
      { file: 'retrieval-quality.md', title: 'Retrieval Quality',        status: 'stable' },
      { file: 'qdrant-notes.md',      title: 'Qdrant Notes',             status: 'stable' },
    ],
  },
  {
    id: 'mcp',
    icon: '🔌',
    name: 'MCP',
    description: 'MCP servers, Chrome DevTools, Serena, security',
    docs: [
      { file: 'chrome-devtools-mcp.md', title: 'Chrome DevTools MCP',   status: 'stable' },
      { file: 'serena-mcp.md',          title: 'Serena MCP',            status: 'stable' },
      { file: 'mcp-security.md',        title: 'MCP Security',          status: 'stable' },
    ],
  },
  {
    id: 'ops',
    icon: '⚙️',
    name: 'Ops',
    description: 'Docker WSL, AlmaLinux CWP, backup & restore',
    docs: [
      { file: 'docker-wsl.md',         title: 'Docker + WSL',           status: 'stable' },
      { file: 'almalinux8-cwp.md',     title: 'AlmaLinux 8 + CWP',      status: 'stable' },
      { file: 'backup-restore.md',     title: 'Backup & Restore',       status: 'stable' },
    ],
  },
  {
    id: 'workflows',
    icon: '🔄',
    name: 'Workflows',
    description: 'Workflow vs Agent, task lifecycle, approval policy',
    docs: [
      { file: 'workflow-vs-agent.md',  title: 'Workflow vs Agent',       status: 'stable' },
      { file: 'task-lifecycle.md',     title: 'Task Lifecycle',          status: 'stable' },
      { file: 'approval-policy.md',    title: 'Approval Policy',         status: 'stable' },
    ],
  },
  {
    id: 'decisions',
    icon: '🏛️',
    name: 'Decisions (ADR)',
    description: 'Architecture Decision Records — ทำไมถึงเลือก X',
    docs: [
      { file: 'why-qdrant.md',                 title: 'Why Qdrant',                    status: 'stable' },
      { file: 'why-hybrid-workflow-agent.md',  title: 'Why Hybrid Workflow-Agent',     status: 'stable' },
      { file: 'why-tto-rtk.md',               title: 'Why TTO + RTK',                 status: 'stable' },
      { file: 'why-serena-mcp.md',            title: 'Why Serena MCP',                status: 'stable' },
    ],
  },
]

const totalDocs = computed(() => wikiSections.reduce((s, sec) => s + sec.docs.length, 0))

async function runSearch() {
  const q = searchQuery.value.trim()
  if (!q) return
  searching.value = true
  searchError.value = ''
  searchResults.value = []
  lastQuery.value = q
  try {
    const res = await fetch(`${ragBaseUrl}/search/wiki`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q, limit: 8 }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    searchResults.value = data.results || []
  } catch (e) {
    searchError.value = `ค้นหาไม่สำเร็จ: ${e.message} — ตรวจสอบว่า RAG Service รันอยู่ที่ ${ragBaseUrl}`
  } finally {
    searching.value = false
  }
}

function clearSearch() {
  searchQuery.value = ''
  searchResults.value = []
  searchError.value = ''
  lastQuery.value = ''
}

async function runIngest() {
  ingesting.value = true
  ingestLog.value = []
  addLog('info', 'เริ่ม Ingest docs/wiki/ → Qdrant aicc_wiki...')
  try {
    addLog('info', `POST ${ragBaseUrl}/ingest/wiki`)
    const res = await fetch(`${ragBaseUrl}/ingest/wiki`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`)
    const data = await res.json()
    ingestReport.value = data
    addLog('success', `Ingest สำเร็จ — ${data.files_ingested} ไฟล์, ${data.chunks_added} chunks เพิ่ม, ${data.chunks_skipped} ข้าม`)
    if (data.errors?.length) {
      data.errors.forEach(e => addLog('warn', `Error: ${e}`))
    }
    collectionStatus.value = 'ok'
  } catch (e) {
    addLog('error', `ล้มเหลว: ${e.message}`)
    addLog('warn', `ตรวจสอบว่า RAG Service รันอยู่ที่ ${ragBaseUrl} และ docs/wiki/ mount อยู่`)
  } finally {
    ingesting.value = false
  }
}

async function fetchIngestReport() {
  try {
    const res = await fetch(`${ragBaseUrl}/ingest/reports/latest`)
    if (res.ok) {
      const data = await res.json()
      if (data && !data.detail) {
        ingestReport.value = data
        collectionStatus.value = 'ok'
      }
    }
  } catch {
    // service may not be running yet
  }
}

function addLog(type, msg) {
  const prefix = { info: 'ℹ️', success: '✅', error: '❌', warn: '⚠️' }[type] || ''
  ingestLog.value.push({ type, msg: `${prefix} ${msg}` })
}

onMounted(() => {
  fetchIngestReport()
})
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #0f172a;
  color: #e2e8f0;
  padding: 24px;
  font-family: 'Segoe UI', sans-serif;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 12px;
}

.page-title {
  font-size: 1.6rem;
  font-weight: 700;
  color: #f1f5f9;
  margin: 0 0 4px;
}

.page-subtitle {
  font-size: 0.85rem;
  color: #64748b;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* Buttons */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.btn-primary { background: #2563eb; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-secondary { background: #334155; color: #e2e8f0; }
.btn-secondary:hover { background: #475569; }
.btn-ghost { background: transparent; color: #94a3b8; border: 1px solid #334155; }
.btn-ghost:hover { background: #1e293b; }
.btn-sm { padding: 6px 12px; font-size: 0.8rem; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Search */
.search-bar {
  display: flex;
  gap: 8px;
  align-items: center;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 10px 14px;
  margin-bottom: 16px;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #e2e8f0;
  font-size: 0.9rem;
  font-family: inherit;
}

.search-input::placeholder { color: #475569; }

/* Search Results */
.search-results {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 20px;
}

.section-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 12px;
}

.error-box {
  background: #7f1d1d20;
  border: 1px solid #dc2626;
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 0.82rem;
  color: #fca5a5;
}

.empty-results { color: #64748b; font-size: 0.85rem; }

.result-list { display: flex; flex-direction: column; gap: 10px; }

.result-card {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 8px;
  padding: 12px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.result-meta   { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
.result-title  { font-size: 0.82rem; font-weight: 600; color: #e2e8f0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.result-category { font-size: 0.68rem; background: #1e3a5f; color: #60a5fa; padding: 1px 5px; border-radius: 4px; flex-shrink: 0; }
.result-score  { font-size: 0.72rem; color: #22c55e; font-weight: 700; flex-shrink: 0; }
.result-path   { font-size: 0.72rem; color: #60a5fa; font-family: monospace; margin: 4px 0 2px; }
.result-heading { font-size: 0.7rem; color: #a78bfa; margin-bottom: 4px; }
.result-text   { font-size: 0.82rem; color: #94a3b8; margin: 0; line-height: 1.5; }
.result-tags   { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.result-tag    { font-size: 0.65rem; background: #1e293b; color: #64748b; border: 1px solid #334155; padding: 1px 6px; border-radius: 4px; }

/* Wiki Grid */
.wiki-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.wiki-section {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 16px;
}

.section-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 14px;
}

.section-icon {
  font-size: 1.4rem;
  flex-shrink: 0;
  margin-top: 2px;
}

.section-name {
  font-size: 1rem;
  font-weight: 700;
  color: #f1f5f9;
}

.section-desc {
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 2px;
}

.doc-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.doc-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  background: #0f172a;
  border-radius: 8px;
  border: 1px solid #1e293b;
}

.doc-icon { font-size: 0.85rem; flex-shrink: 0; margin-top: 2px; }

.doc-info { flex: 1; min-width: 0; }

.doc-title {
  font-size: 0.82rem;
  font-weight: 600;
  color: #e2e8f0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-path {
  font-size: 0.68rem;
  color: #475569;
  margin-top: 2px;
  font-family: monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-tag {
  flex-shrink: 0;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}

.tag-stable  { background: #14532d40; color: #4ade80; }
.tag-draft   { background: #78350f40; color: #fbbf24; }
.tag-deprecated { background: #7f1d1d40; color: #f87171; }

/* Stats Bar */
.stats-bar {
  display: flex;
  gap: 24px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 14px 20px;
  margin-bottom: 20px;
}

.stat { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.stat-num { font-size: 1.4rem; font-weight: 700; color: #60a5fa; }
.stat-ok   { color: #4ade80; }
.stat-warn { color: #fbbf24; }
.stat-label { font-size: 0.72rem; color: #64748b; }

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 20px;
}

.modal {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 14px;
  width: 100%;
  max-width: 520px;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #334155;
}

.modal-title { font-size: 1rem; font-weight: 700; color: #f1f5f9; }

.modal-close {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  font-size: 1rem;
  padding: 4px 8px;
}

.modal-close:hover { color: #e2e8f0; }

.modal-body { padding: 20px; }

.ingest-desc {
  font-size: 0.84rem;
  color: #94a3b8;
  margin: 0 0 14px;
  line-height: 1.6;
}

.ingest-steps {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}

.step {
  font-size: 0.8rem;
  color: #60a5fa;
  background: #0f172a;
  border-radius: 6px;
  padding: 6px 10px;
  font-family: monospace;
}

.ingest-endpoints {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}

.endpoint-row { display: flex; align-items: center; gap: 8px; font-size: 0.78rem; }
.endpoint-label { color: #64748b; min-width: 70px; }
.endpoint-row code { color: #a78bfa; }

.ingest-report {
  background: #0f172a;
  border: 1px solid #1e3a5f;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.report-row { display: flex; justify-content: space-between; font-size: 0.78rem; }
.report-label { color: #64748b; }
.report-time { color: #60a5fa; font-size: 0.72rem; }

.ingest-log {
  background: #0f172a;
  border-radius: 8px;
  padding: 10px 12px;
  max-height: 200px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.log-line { font-size: 0.76rem; font-family: monospace; line-height: 1.4; }
.log-line.info    { color: #94a3b8; }
.log-line.success { color: #4ade80; }
.log-line.error   { color: #f87171; }
.log-line.warn    { color: #fbbf24; }

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 20px;
  border-top: 1px solid #334155;
}

code {
  background: #0f172a;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.8em;
  color: #a78bfa;
}

@media (max-width: 600px) {
  .wiki-grid { grid-template-columns: 1fr; }
  .page-header { flex-direction: column; }
  .stats-bar { gap: 16px; }
}
</style>
