<template>
  <div class="ws-page">
    <!-- Header -->
    <div class="ws-header">
      <div class="ws-header-left">
        <a href="/command" class="ws-back">← Back</a>
        <span class="ws-title">⊞ Workspaces</span>
      </div>
      <div class="ws-header-right">
        <button class="ws-btn ws-btn-primary" @click="openAddModal">+ Add Workspace</button>
        <a href="/cowork" class="ws-btn ws-btn-cowork">Open CoWork →</a>
      </div>
    </div>

    <!-- Health warning if no active workspace -->
    <div class="ws-warning" v-if="!activeWs && !loading">
      <span>⚠️</span>
      <span>ยังไม่มี workspace ที่ active — เลือก workspace เพื่อเริ่มใช้งาน CoWork</span>
    </div>

    <!-- Loading -->
    <div class="ws-loading" v-if="loading">
      <div class="ws-loading-spinner">⏳</div>
      <span>Loading workspaces…</span>
    </div>

    <!-- Workspace grid -->
    <div class="ws-grid" v-else-if="workspaces.length">
      <div
        v-for="ws in workspaces"
        :key="ws.name"
        class="ws-card"
        :class="{ 'ws-card--active': ws.active }"
      >
        <!-- Card header -->
        <div class="wsc-header">
          <div class="wsc-name-row">
            <span class="wsc-name">{{ ws.name }}</span>
            <span class="wsc-active-badge" v-if="ws.active">● Active</span>
          </div>
          <span class="wsc-health" :class="ws.health === 'ok' ? 'health--ok' : 'health--unknown'">
            ● {{ ws.health === 'ok' ? 'Healthy' : 'Unknown' }}
          </span>
        </div>

        <!-- Meta -->
        <div class="wsc-meta">
          <div class="wsc-meta-row" v-if="ws.git_branch">
            <span class="wsc-meta-key">Branch</span>
            <code class="wsc-meta-branch">{{ ws.git_branch }}</code>
          </div>
          <div class="wsc-meta-row" v-if="ws.container_path || ws.root">
            <span class="wsc-meta-key">Container</span>
            <span class="wsc-meta-path">{{ ws.container_path || ws.root }}</span>
          </div>
          <div class="wsc-meta-row" v-if="ws.host_path">
            <span class="wsc-meta-key">Host</span>
            <span class="wsc-meta-path">{{ ws.host_path }}</span>
          </div>
          <div class="wsc-meta-row" v-if="ws.default_mode">
            <span class="wsc-meta-key">Mode</span>
            <span class="wsc-meta-mode">{{ ws.default_mode }}</span>
          </div>
          <div class="wsc-meta-row" v-if="ws.last_used">
            <span class="wsc-meta-key">Last used</span>
            <span class="wsc-meta-val">{{ fmtDate(ws.last_used) }}</span>
          </div>
        </div>

        <!-- Test result -->
        <div class="wsc-test-result" v-if="testResults[ws.name]">
          <span :class="testResults[ws.name].ok ? 'test-ok' : 'test-fail'">
            {{ testResults[ws.name].ok ? '✓ Access OK' : '✕ ' + testResults[ws.name].error }}
          </span>
        </div>

        <!-- Actions -->
        <div class="wsc-actions">
          <button
            class="wsc-btn wsc-btn-primary"
            @click="setActive(ws)"
            :disabled="ws.active || settingActive === ws.name"
            v-if="!ws.active"
          >
            <span v-if="settingActive === ws.name">⏳ Setting…</span>
            <span v-else>Set Active</span>
          </button>
          <span class="wsc-active-pill" v-else>✓ Active</span>
          <button class="wsc-btn" @click="testAccess(ws)" :disabled="testing === ws.name">
            <span v-if="testing === ws.name">⏳</span>
            <span v-else>Test Access</span>
          </button>
          <a class="wsc-btn wsc-btn-cowork" :href="'/cowork'" @click.prevent="openInCowork(ws)">Open in CoWork</a>
          <button class="wsc-btn wsc-btn-danger" @click="removeWs(ws)" :disabled="ws.active">Remove</button>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div class="ws-empty" v-else>
      <div class="ws-empty-icon">⊞</div>
      <div class="ws-empty-title">No workspaces configured</div>
      <div class="ws-empty-sub">
        Add a workspace to get started.<br>
        Container path must match Docker volume mounts.
      </div>
      <button class="ws-btn ws-btn-primary ws-empty-btn" @click="openAddModal">+ Add Workspace</button>
    </div>

    <!-- Add Workspace Modal -->
    <div class="modal-overlay" v-if="addModal.open" @click.self="closeAddModal">
      <div class="modal">
        <div class="modal-header">
          <span>+ Add Workspace</span>
          <button class="btn-close" @click="closeAddModal">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-field">
            <label class="form-label">Name <span class="required">*</span></label>
            <input v-model="addModal.name" class="form-input" placeholder="เช่น: AI Control Center" />
          </div>
          <div class="form-field">
            <label class="form-label">Container Path <span class="required">*</span></label>
            <input v-model="addModal.container_path" class="form-input font-mono" placeholder="/workspace/ai-control-center" />
            <span class="form-hint">ต้องเป็น path ที่ Docker mount แล้วเท่านั้น</span>
          </div>
          <div class="form-field">
            <label class="form-label">Host Path</label>
            <div class="form-input-row">
              <input v-model="addModal.host_path" class="form-input font-mono" placeholder="E:\Project\laragon\www\ai-control-center" />
            </div>
            <span class="form-hint">ใช้สำหรับอ้างอิง — ไม่ใช้ในการแก้ไฟล์จริง</span>
          </div>
          <div class="form-field">
            <label class="form-label">Branch</label>
            <input v-model="addModal.git_branch" class="form-input font-mono" placeholder="main" />
          </div>
          <div class="form-field">
            <label class="form-label">Default Mode</label>
            <select v-model="addModal.default_mode" class="form-select">
              <option value="plan-only">plan-only</option>
              <option value="execute">execute</option>
              <option value="dry-run">dry-run</option>
            </select>
          </div>
          <div class="modal-error" v-if="addModal.error">❌ {{ addModal.error }}</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-primary" :disabled="!addModal.name.trim() || !addModal.container_path.trim() || addModal.loading" @click="submitAddWorkspace">
            <span v-if="addModal.loading">⏳ Adding…</span>
            <span v-else>+ Add Workspace</span>
          </button>
          <button class="btn btn-secondary" @click="closeAddModal">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const config = useRuntimeConfig()
const WORKER = config.public.workerBase

const workspaces  = ref([])
const loading     = ref(true)
const testing     = ref(null)
const settingActive = ref(null)
const testResults = ref({})

const addModal = ref({
  open: false, loading: false, error: '',
  name: '', container_path: '', host_path: '', git_branch: 'main', default_mode: 'plan-only',
})

const activeWs = computed(() => workspaces.value.find(w => w.active))

onMounted(async () => {
  await loadWorkspaces()
})

async function loadWorkspaces() {
  loading.value = true
  try {
    // Try worker /workspaces endpoint first
    const res = await fetch(`${WORKER}/workspaces`)
    if (res.ok) {
      workspaces.value = await res.json()
    } else {
      // Fall back to single workspace
      const wsRes = await fetch(`${WORKER}/workspace`)
      if (wsRes.ok) {
        const ws = await wsRes.json()
        workspaces.value = [{ ...ws, active: true, health: 'ok' }]
      }
    }
  } catch {
    // Try single workspace fallback
    try {
      const wsRes = await fetch(`${WORKER}/workspace`)
      if (wsRes.ok) {
        const ws = await wsRes.json()
        workspaces.value = [{ ...ws, active: true, health: 'ok' }]
      }
    } catch { /* nothing */ }
  } finally {
    loading.value = false
  }
}

async function setActive(ws) {
  settingActive.value = ws.name
  try {
    const res = await fetch(`${WORKER}/workspaces/active`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: ws.name }),
    })
    if (res.ok) {
      workspaces.value.forEach(w => { w.active = w.name === ws.name })
    }
  } catch { /* ignore */ }
  finally { settingActive.value = null }
}

async function testAccess(ws) {
  testing.value = ws.name
  try {
    const res = await fetch(`${WORKER}/workspaces/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: ws.name }),
    })
    const data = await res.json().catch(() => ({}))
    testResults.value = { ...testResults.value, [ws.name]: { ok: res.ok && data.ok, error: data.error } }
  } catch (e) {
    testResults.value = { ...testResults.value, [ws.name]: { ok: false, error: e.message } }
  } finally { testing.value = null }
}

function openInCowork(ws) {
  setActive(ws).then(() => { window.location.href = '/cowork' })
}

async function removeWs(ws) {
  if (!confirm(`Remove workspace "${ws.name}"?`)) return
  try {
    const res = await fetch(`${WORKER}/workspaces/${encodeURIComponent(ws.name)}`, { method: 'DELETE' })
    if (res.ok) {
      workspaces.value = workspaces.value.filter(w => w.name !== ws.name)
    }
  } catch { /* ignore */ }
}

function openAddModal() {
  addModal.value = { open: true, loading: false, error: '', name: '', container_path: '', host_path: '', git_branch: 'main', default_mode: 'plan-only' }
}

async function submitAddWorkspace() {
  addModal.value.loading = true
  addModal.value.error = ''
  try {
    const res = await fetch(`${WORKER}/workspaces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: addModal.value.name.trim(),
        container_path: addModal.value.container_path.trim(),
        host_path: addModal.value.host_path.trim() || undefined,
        git_branch: addModal.value.git_branch.trim() || 'main',
        default_mode: addModal.value.default_mode,
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      addModal.value.error = err.detail || `HTTP ${res.status}`
      return
    }
    addModal.value.open = false
    await loadWorkspaces()
  } catch (e) { addModal.value.error = e.message }
  finally { addModal.value.loading = false }
}

function closeAddModal() { addModal.value.open = false }

function fmtDate(ts) {
  if (!ts) return '—'
  try { return new Date(ts).toLocaleString('th-TH', { dateStyle: 'short', timeStyle: 'short' }) }
  catch { return ts }
}
</script>

<style scoped>
*, *::before, *::after { box-sizing: border-box; }

.ws-page {
  min-height: 100vh;
  background: #080c14;
  color: #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  padding: 0 0 40px;
}

/* Header */
.ws-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 24px;
  background: #0a1020;
  border-bottom: 1px solid #1e293b;
  flex-wrap: wrap;
}
.ws-header-left { display: flex; align-items: center; gap: 12px; }
.ws-back {
  font-size: 0.78rem;
  color: #64748b;
  text-decoration: none;
  padding: 4px 8px;
  border: 1px solid #1e293b;
  border-radius: 5px;
}
.ws-back:hover { background: #1e293b; color: #94a3b8; }
.ws-title { font-size: 1rem; font-weight: 700; color: #f1f5f9; }
.ws-header-right { display: flex; gap: 8px; }

/* Warning */
.ws-warning {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  background: #422006;
  border-bottom: 1px solid #7c2d12;
  font-size: 0.8rem;
  color: #fbbf24;
}

/* Loading */
.ws-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 3rem 24px;
  color: #64748b;
  font-size: 0.85rem;
}
.ws-loading-spinner { font-size: 1.2rem; }

/* Grid */
.ws-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  padding: 20px 24px;
}

/* Card */
.ws-card {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ws-card--active {
  border-color: #1e3a5f;
  background: #0c1830;
  box-shadow: 0 0 0 1px #1e3a5f20;
}

.wsc-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.wsc-name-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.wsc-name { font-size: 0.92rem; font-weight: 700; color: #f1f5f9; }
.wsc-active-badge { font-size: 0.62rem; font-weight: 700; color: #4ade80; background: #14532d; padding: 2px 6px; border-radius: 4px; }
.wsc-health { font-size: 0.66rem; font-weight: 600; flex-shrink: 0; }
.health--ok      { color: #22c55e; }
.health--unknown { color: #475569; }

.wsc-meta { display: flex; flex-direction: column; gap: 5px; }
.wsc-meta-row { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
.wsc-meta-key { font-size: 0.62rem; font-weight: 600; color: #334155; min-width: 64px; flex-shrink: 0; }
.wsc-meta-val { font-size: 0.74rem; color: #94a3b8; }
.wsc-meta-branch { font-size: 0.64rem; background: #064e3b; color: #6ee7b7; padding: 1px 6px; border-radius: 3px; font-family: monospace; }
.wsc-meta-path { font-size: 0.62rem; color: #475569; font-family: monospace; word-break: break-all; line-height: 1.4; }
.wsc-meta-mode { font-size: 0.62rem; background: #1e1b4b; color: #a78bfa; padding: 1px 6px; border-radius: 3px; }

.wsc-test-result { font-size: 0.72rem; padding: 6px 8px; border-radius: 5px; background: #0c1830; }
.test-ok   { color: #4ade80; }
.test-fail { color: #f87171; word-break: break-word; }

.wsc-actions { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-top: 2px; }
.wsc-btn {
  padding: 5px 10px;
  border-radius: 6px;
  border: 1px solid #1e293b;
  background: #0f172a;
  color: #94a3b8;
  font-size: 0.7rem;
  cursor: pointer;
  transition: all 0.12s;
  font-family: inherit;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.wsc-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.wsc-btn:not(:disabled):hover { background: #1e293b; color: #e2e8f0; }
.wsc-btn-primary { border-color: #1e3a5f; color: #60a5fa; }
.wsc-btn-primary:not(:disabled):hover { background: #1e3a5f; color: #fff; }
.wsc-btn-cowork { border-color: #064e3b; color: #6ee7b7; }
.wsc-btn-cowork:hover { background: #064e3b; color: #fff; }
.wsc-btn-danger { border-color: #450a0a; color: #f87171; }
.wsc-btn-danger:not(:disabled):hover { background: #450a0a; color: #fff; }
.wsc-active-pill { padding: 5px 10px; background: #14532d; color: #4ade80; font-size: 0.7rem; font-weight: 600; border-radius: 6px; }

/* Empty */
.ws-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 4rem 2rem;
  text-align: center;
}
.ws-empty-icon  { font-size: 2.5rem; opacity: 0.2; }
.ws-empty-title { font-size: 1rem; font-weight: 600; color: #475569; }
.ws-empty-sub   { font-size: 0.8rem; color: #334155; line-height: 1.6; }
.ws-empty-btn   { margin-top: 8px; }

/* Global buttons */
.ws-btn {
  padding: 7px 14px;
  border-radius: 7px;
  border: 1px solid #1e293b;
  background: #0f172a;
  color: #94a3b8;
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.12s;
  font-family: inherit;
  text-decoration: none;
}
.ws-btn:hover { background: #1e293b; color: #e2e8f0; }
.ws-btn-primary { border-color: #1e3a5f; color: #60a5fa; background: #12243f; }
.ws-btn-primary:hover { background: #1e3a5f; color: #fff; }
.ws-btn-cowork { border-color: #064e3b; color: #6ee7b7; background: #0a1f15; }
.ws-btn-cowork:hover { background: #064e3b; color: #fff; }

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 500;
  padding: 1rem;
}
.modal {
  background: #1a2540;
  color: #e2e8f0;
  width: 100%;
  max-width: 560px;
  max-height: 85vh;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #1e293b;
}
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
.btn-close { background: none; border: none; color: #475569; font-size: 1rem; cursor: pointer; }
.modal-body { flex: 1; overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: 12px; }
.modal-footer { display: flex; gap: 8px; padding: 0.75rem 1rem; border-top: 1px solid #1e293b; justify-content: flex-end; flex-shrink: 0; }
.modal-error { color: #fca5a5; font-size: 0.78rem; }

.form-field { display: flex; flex-direction: column; gap: 4px; }
.form-label { font-size: 0.72rem; font-weight: 600; color: #64748b; }
.form-input {
  width: 100%;
  background: #0f172a;
  color: #e2e8f0;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 0.45rem 0.65rem;
  font-size: 0.8rem;
  font-family: inherit;
}
.form-input:focus { outline: none; border-color: #3b82f6; }
.font-mono { font-family: monospace; font-size: 0.76rem; }
.form-select { background: #0f172a; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px; padding: 0.42rem 0.6rem; font-size: 0.8rem; font-family: inherit; }
.form-hint { font-size: 0.66rem; color: #475569; }
.form-input-row { display: flex; gap: 6px; }

.required { color: #f87171; }

.btn { padding: 0.42rem 0.85rem; border-radius: 7px; border: none; font-size: 0.8rem; font-weight: 600; cursor: pointer; font-family: inherit; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary   { background: #2563eb; color: #fff; }
.btn-primary:not(:disabled):hover { background: #1d4ed8; }
.btn-secondary { background: #0f766e; color: #fff; }
</style>
