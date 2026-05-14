<template>
  <aside class="cw-sidebar">
    <!-- Brand -->
    <div class="sb-brand">
      <div class="sb-brand-mark">◈</div>
      <div class="sb-brand-text">
        <span class="sb-brand-name">AI Control</span>
        <span class="sb-brand-sub">Center</span>
      </div>
    </div>

    <!-- Mode tabs -->
    <div class="sb-tabs">
      <button
        v-for="tab in TABS"
        :key="tab.id"
        class="sb-tab"
        :class="{ 'sb-tab--active': modelValue === tab.id }"
        @click="$emit('update:modelValue', tab.id)"
        :title="tab.label"
      >
        <span class="sb-tab-icon">{{ tab.icon }}</span>
        <span class="sb-tab-label">{{ tab.label }}</span>
      </button>
    </div>

    <!-- New task -->
    <div class="sb-section">
      <button class="sb-new-task" @click="$emit('newTask')">
        <span class="sb-new-plus">+</span>
        New Task
      </button>
    </div>

    <!-- Main nav -->
    <nav class="sb-nav">
      <button class="sb-nav-item" @click="$emit('openWorkspaces')">
        <span class="sb-nav-icon">⊞</span>
        <span>Projects</span>
      </button>
      <a class="sb-nav-item" href="/jobs">
        <span class="sb-nav-icon">⏱</span>
        <span>Scheduled</span>
      </a>
      <button class="sb-nav-item" @click="$emit('openArtifacts')">
        <span class="sb-nav-icon">◉</span>
        <span>Live Artifacts</span>
      </button>
      <a class="sb-nav-item" href="/approvals">
        <span class="sb-nav-icon">⊛</span>
        <span>Approvals</span>
      </a>
      <a class="sb-nav-item" href="/settings">
        <span class="sb-nav-icon">⚙</span>
        <span>Settings</span>
      </a>
    </nav>

    <!-- Divider -->
    <div class="sb-divider"></div>

    <!-- Recent workspaces -->
    <div class="sb-section sb-recent-section" v-if="recentItems.length">
      <div class="sb-section-label">Recent</div>
      <button
        v-for="item in recentItems"
        :key="item.name"
        class="sb-recent-item"
        :class="{ 'sb-recent-item--active': item.active }"
        @click="$emit('selectWorkspace', item)"
      >
        <span class="sb-recent-dot" :class="item.health === 'ok' ? 'dot--green' : 'dot--gray'"></span>
        <span class="sb-recent-name">{{ item.name }}</span>
      </button>
    </div>

    <div class="sb-flex-grow"></div>

    <!-- Active workspace card -->
    <div class="sb-ws-card" v-if="wsInfo">
      <div class="sb-ws-header">
        <span class="sb-ws-name">{{ wsInfo.name }}</span>
        <span class="sb-ws-health" title="Healthy">●</span>
      </div>
      <div class="sb-ws-meta">
        <code class="sb-ws-branch">{{ wsInfo.git_branch || 'main' }}</code>
        <span class="sb-ws-mode">{{ wsInfo.default_mode || 'plan' }}</span>
      </div>
      <div class="sb-ws-btns">
        <button class="sb-ws-btn" @click="$emit('openWorkspaces')">Switch</button>
        <button class="sb-ws-btn" @click="$emit('testWorkspace')">Test</button>
      </div>
    </div>
    <div class="sb-ws-card sb-ws-card--empty" v-else>
      <span class="sb-ws-empty">No workspace active</span>
      <button class="sb-ws-btn sb-ws-btn--full" @click="$emit('openWorkspaces')">Select Workspace →</button>
    </div>
  </aside>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: String, default: 'cowork' },
  wsInfo: { type: Object, default: null },
  recentItems: {
    type: Array,
    default: () => [
      { name: 'AI Control Center', health: 'ok', active: true },
      { name: 'POSFood', health: 'ok', active: false },
      { name: 'demo69', health: 'unknown', active: false },
    ],
  },
})
defineEmits(['update:modelValue', 'newTask', 'openWorkspaces', 'testWorkspace', 'selectWorkspace', 'openArtifacts'])

const TABS = [
  { id: 'chat', icon: '💬', label: 'Chat' },
  { id: 'cowork', icon: '◈', label: 'CoWork' },
  { id: 'code', icon: '<>', label: 'Code' },
]
</script>

<style scoped>
.cw-sidebar {
  width: 260px;
  min-width: 260px;
  height: 100%;
  background: #0a1020;
  border-right: 1px solid #1e293b;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}

/* Brand */
.sb-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 15px 14px 13px;
  border-bottom: 1px solid #1a2640;
  flex-shrink: 0;
}
.sb-brand-mark {
  width: 30px;
  height: 30px;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  color: #fff;
  flex-shrink: 0;
}
.sb-brand-text { display: flex; flex-direction: column; }
.sb-brand-name { font-size: 0.8rem; font-weight: 700; color: #f1f5f9; line-height: 1.2; }
.sb-brand-sub  { font-size: 0.62rem; color: #475569; line-height: 1.2; }

/* Mode tabs */
.sb-tabs {
  display: flex;
  gap: 2px;
  padding: 8px 8px;
  border-bottom: 1px solid #1a2640;
  flex-shrink: 0;
}
.sb-tab {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 4px;
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  color: #64748b;
  transition: all 0.14s;
}
.sb-tab:hover { background: #131f35; color: #94a3b8; }
.sb-tab--active { background: #1e3a5f; color: #60a5fa; }
.sb-tab-icon  { font-size: 0.88rem; }
.sb-tab-label { font-size: 0.6rem; font-weight: 600; }

/* Sections */
.sb-section { padding: 8px 8px; flex-shrink: 0; }
.sb-section-label {
  font-size: 0.6rem;
  font-weight: 700;
  color: #334155;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  padding: 0 4px;
  margin-bottom: 4px;
}

/* New Task */
.sb-new-task {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #12243f;
  border: 1px solid #1e3a5f;
  border-radius: 7px;
  color: #60a5fa;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.14s;
  font-family: inherit;
}
.sb-new-task:hover { background: #1d3461; color: #93c5fd; }
.sb-new-plus { font-size: 1.1rem; font-weight: 300; line-height: 1; }

/* Nav */
.sb-nav { padding: 2px 6px; display: flex; flex-direction: column; gap: 1px; flex-shrink: 0; }
.sb-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 8px;
  border-radius: 6px;
  font-size: 0.76rem;
  color: #94a3b8;
  cursor: pointer;
  background: transparent;
  border: none;
  text-decoration: none;
  transition: all 0.12s;
  text-align: left;
  width: 100%;
  font-family: inherit;
}
.sb-nav-item:hover { background: #131f35; color: #e2e8f0; }
.sb-nav-icon { font-size: 0.82rem; width: 16px; text-align: center; flex-shrink: 0; opacity: 0.65; }

/* Divider */
.sb-divider {
  height: 1px;
  background: #1a2640;
  margin: 4px 10px;
  flex-shrink: 0;
}

/* Recent */
.sb-recent-section { overflow-y: auto; max-height: 140px; }
.sb-recent-item {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  padding: 5px 6px;
  border-radius: 5px;
  background: transparent;
  border: none;
  font-size: 0.74rem;
  color: #94a3b8;
  cursor: pointer;
  text-align: left;
  transition: all 0.12s;
  font-family: inherit;
}
.sb-recent-item:hover { background: #131f35; color: #e2e8f0; }
.sb-recent-item--active { color: #60a5fa; }
.sb-recent-dot { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }
.dot--green { background: #22c55e; }
.dot--gray  { background: #334155; }
.sb-recent-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.sb-flex-grow { flex: 1; min-height: 8px; }

/* Workspace card */
.sb-ws-card {
  margin: 8px 8px 10px;
  background: #0d1f38;
  border: 1px solid #1e3a5f;
  border-radius: 9px;
  padding: 11px 12px;
  flex-shrink: 0;
}
.sb-ws-card--empty {
  border-color: #1e293b;
  background: #0a1020;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}
.sb-ws-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 5px;
}
.sb-ws-name { font-size: 0.76rem; font-weight: 600; color: #f1f5f9; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 160px; }
.sb-ws-health { color: #22c55e; font-size: 0.55rem; flex-shrink: 0; }
.sb-ws-meta { display: flex; align-items: center; gap: 5px; margin-bottom: 9px; flex-wrap: wrap; }
.sb-ws-branch {
  font-size: 0.62rem;
  background: #064e3b;
  color: #6ee7b7;
  padding: 1px 5px;
  border-radius: 3px;
  font-family: monospace;
}
.sb-ws-mode {
  font-size: 0.6rem;
  background: #1e1b4b;
  color: #a78bfa;
  padding: 1px 5px;
  border-radius: 3px;
}
.sb-ws-btns { display: flex; gap: 4px; }
.sb-ws-btn {
  flex: 1;
  padding: 5px 6px;
  border-radius: 5px;
  border: 1px solid #1e3a5f;
  background: #0f172a;
  color: #94a3b8;
  font-size: 0.68rem;
  cursor: pointer;
  transition: all 0.12s;
  font-family: inherit;
}
.sb-ws-btn:hover { background: #1e3a5f; color: #e2e8f0; }
.sb-ws-btn--full { flex: none; width: 100%; text-align: center; }
.sb-ws-empty { font-size: 0.7rem; color: #334155; text-align: center; }
</style>
