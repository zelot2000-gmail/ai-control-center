<template>
  <Teleport to="body">
    <div class="wp-overlay" v-if="open" @click.self="$emit('close')">
      <div class="wp-drawer">
        <!-- Header -->
        <div class="wp-header">
          <div class="wp-header-left">
            <span class="wp-icon">⊞</span>
            <span class="wp-title">Workspaces</span>
          </div>
          <button class="wp-close" @click="$emit('close')">✕</button>
        </div>

        <!-- Loading -->
        <div class="wp-body" v-if="loading">
          <div class="wp-loading">⏳ Loading workspaces…</div>
        </div>

        <!-- Empty -->
        <div class="wp-body" v-else-if="!workspaces.length">
          <div class="wp-empty">
            <div class="wp-empty-icon">⊞</div>
            <div class="wp-empty-title">No workspaces configured</div>
            <div class="wp-empty-sub">
              Add workspace configuration to <code>data/workspaces.json</code>
            </div>
          </div>
        </div>

        <!-- Workspace list -->
        <div class="wp-body" v-else>
          <div
            v-for="ws in workspaces"
            :key="ws.name"
            class="wp-item"
            :class="{ 'wp-item--active': ws.active }"
          >
            <div class="wp-item-header">
              <span class="wp-item-name">{{ ws.name }}</span>
              <span
                class="wp-item-health"
                :class="ws.health === 'ok' ? 'health--ok' : 'health--unknown'"
              >
                ● {{ ws.health === 'ok' ? 'Healthy' : 'Unknown' }}
              </span>
            </div>

            <div class="wp-item-meta">
              <div class="wp-meta-row" v-if="ws.git_branch">
                <span class="wp-meta-key">Branch</span>
                <code class="wp-meta-branch">{{ ws.git_branch }}</code>
              </div>
              <div class="wp-meta-row" v-if="ws.container_path || ws.root">
                <span class="wp-meta-key">Path</span>
                <span class="wp-meta-path">{{ ws.container_path || ws.root }}</span>
              </div>
              <div class="wp-meta-row" v-if="ws.default_mode">
                <span class="wp-meta-key">Mode</span>
                <span class="wp-meta-mode">{{ ws.default_mode }}</span>
              </div>
              <div class="wp-meta-row" v-if="ws.last_used">
                <span class="wp-meta-key">Last used</span>
                <span class="wp-meta-val">{{ fmtDate(ws.last_used) }}</span>
              </div>
            </div>

            <div class="wp-item-actions">
              <button
                class="wp-btn wp-btn-primary"
                @click="$emit('select', ws)"
                v-if="!ws.active"
              >Set Active</button>
              <span class="wp-active-badge" v-else>✓ Active</span>
              <button class="wp-btn" @click="$emit('test', ws)">Test Access</button>
              <button class="wp-btn wp-btn-cowork" @click="onOpenCowork(ws)">Open in CoWork</button>
            </div>

            <!-- Test result -->
            <div class="wp-test-result" v-if="testResults[ws.name]">
              <span :class="testResults[ws.name].ok ? 'test-ok' : 'test-fail'">
                {{ testResults[ws.name].ok ? '✓ Access OK' : '✕ ' + testResults[ws.name].error }}
              </span>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="wp-footer">
          <a href="/workspaces" class="wp-footer-link">Manage workspaces →</a>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
const props = defineProps({
  open: { type: Boolean, default: false },
  workspaces: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'select', 'test', 'openInCowork'])

const testResults = ref({})

function onOpenCowork(ws) {
  emit('openInCowork', ws)
  emit('close')
}

function fmtDate(ts) {
  if (!ts) return '—'
  try {
    return new Date(ts).toLocaleString('th-TH', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return ts
  }
}
</script>

<style scoped>
.wp-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  z-index: 400;
  display: flex;
  align-items: stretch;
  justify-content: flex-end;
}

.wp-drawer {
  width: 440px;
  max-width: 100vw;
  background: #0c1525;
  border-left: 1px solid #1e293b;
  display: flex;
  flex-direction: column;
  animation: wp-slide 0.2s ease;
}
@keyframes wp-slide {
  from { transform: translateX(100%); }
  to   { transform: translateX(0); }
}

/* Header */
.wp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #1e293b;
  flex-shrink: 0;
}
.wp-header-left { display: flex; align-items: center; gap: 8px; }
.wp-icon { font-size: 1rem; color: #60a5fa; }
.wp-title { font-size: 0.88rem; font-weight: 700; color: #f1f5f9; }
.wp-close {
  background: none; border: none; color: #64748b;
  cursor: pointer; font-size: 1rem; padding: 2px 6px;
  border-radius: 4px;
}
.wp-close:hover { background: #1e293b; color: #e2e8f0; }

/* Body */
.wp-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.wp-body::-webkit-scrollbar { width: 4px; }
.wp-body::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }

/* States */
.wp-loading { text-align: center; color: #64748b; font-size: 0.82rem; padding: 2rem; }
.wp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 3rem 1rem;
  text-align: center;
}
.wp-empty-icon { font-size: 2rem; opacity: 0.3; color: #475569; }
.wp-empty-title { font-size: 0.85rem; font-weight: 600; color: #475569; }
.wp-empty-sub { font-size: 0.72rem; color: #334155; line-height: 1.5; }
.wp-empty-sub code { color: #64748b; font-size: 0.68rem; }

/* Workspace item */
.wp-item {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 10px;
  padding: 14px;
}
.wp-item--active {
  border-color: #1e3a5f;
  background: #0c1830;
}
.wp-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.wp-item-name { font-size: 0.85rem; font-weight: 700; color: #f1f5f9; }
.wp-item-health { font-size: 0.66rem; font-weight: 600; }
.health--ok    { color: #22c55e; }
.health--unknown { color: #475569; }

.wp-item-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}
.wp-meta-row { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
.wp-meta-key {
  font-size: 0.62rem;
  font-weight: 600;
  color: #334155;
  min-width: 46px;
  flex-shrink: 0;
}
.wp-meta-val { font-size: 0.72rem; color: #94a3b8; }
.wp-meta-branch {
  font-size: 0.62rem;
  background: #064e3b;
  color: #6ee7b7;
  padding: 1px 5px;
  border-radius: 3px;
  font-family: monospace;
}
.wp-meta-path {
  font-size: 0.62rem;
  color: #475569;
  font-family: monospace;
  word-break: break-all;
  line-height: 1.4;
}
.wp-meta-mode {
  font-size: 0.62rem;
  background: #1e1b4b;
  color: #a78bfa;
  padding: 1px 5px;
  border-radius: 3px;
}

/* Actions */
.wp-item-actions { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.wp-btn {
  padding: 5px 10px;
  border-radius: 6px;
  border: 1px solid #1e293b;
  background: #0f172a;
  color: #94a3b8;
  font-size: 0.7rem;
  cursor: pointer;
  transition: all 0.12s;
  font-family: inherit;
}
.wp-btn:hover { background: #1e293b; color: #e2e8f0; }
.wp-btn-primary { border-color: #1e3a5f; color: #60a5fa; }
.wp-btn-primary:hover { background: #1e3a5f; color: #fff; }
.wp-btn-cowork { border-color: #064e3b; color: #6ee7b7; }
.wp-btn-cowork:hover { background: #064e3b; color: #fff; }
.wp-active-badge {
  padding: 5px 10px;
  border-radius: 6px;
  background: #14532d;
  color: #4ade80;
  font-size: 0.7rem;
  font-weight: 600;
}

/* Test result */
.wp-test-result { margin-top: 8px; font-size: 0.7rem; }
.test-ok  { color: #4ade80; }
.test-fail { color: #f87171; word-break: break-word; }

/* Footer */
.wp-footer {
  padding: 12px 20px;
  border-top: 1px solid #1e293b;
  flex-shrink: 0;
}
.wp-footer-link {
  font-size: 0.72rem;
  color: #64748b;
  text-decoration: none;
}
.wp-footer-link:hover { color: #94a3b8; }
</style>
