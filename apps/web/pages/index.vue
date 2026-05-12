<template>
  <div class="page">
    <h1>AI Control Center</h1>

    <div class="nav-grid">
      <a href="/command" class="nav-card">
        <span class="nav-icon">💬</span>
        <div>
          <div class="nav-title">Command</div>
          <div class="nav-desc">ส่งคำสั่งให้ทีม AI</div>
        </div>
      </a>
      <a href="/jobs" class="nav-card">
        <span class="nav-icon">📋</span>
        <div>
          <div class="nav-title">Jobs</div>
          <div class="nav-desc">ดูสถานะ Task ทั้งหมด</div>
        </div>
      </a>
      <a href="/knowledge" class="nav-card">
        <span class="nav-icon">📚</span>
        <div>
          <div class="nav-title">Knowledge</div>
          <div class="nav-desc">LLM Wiki — ฐานความรู้กลาง</div>
        </div>
      </a>
      <a href="/approvals" class="nav-card">
        <span class="nav-icon">✅</span>
        <div>
          <div class="nav-title">Approvals</div>
          <div class="nav-desc">รายการรออนุมัติ</div>
        </div>
      </a>
      <a href="/logs" class="nav-card">
        <span class="nav-icon">📜</span>
        <div>
          <div class="nav-title">Logs</div>
          <div class="nav-desc">System & Agent Logs</div>
        </div>
      </a>
    </div>

    <div class="api-links">
      <p class="api-title">API Endpoints</p>
      <ul>
        <li><a href="http://127.0.0.1:8088/docs" target="_blank">Mobile Gateway API Docs</a></li>
        <li><a href="http://127.0.0.1:8090/docs" target="_blank">RAG API Docs</a></li>
        <li><a href="http://127.0.0.1:8091/docs" target="_blank">TTO API Docs</a></li>
        <li><a href="http://127.0.0.1:8092/docs" target="_blank">RTK Bridge Docs</a></li>
        <li><a href="http://127.0.0.1:8094/status" target="_blank">Observer Status</a></li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.page { font-family: 'Segoe UI', sans-serif; padding: 2rem; max-width: 700px; margin: auto; }
h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 20px; }

.nav-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 28px;
}

.nav-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  text-decoration: none;
  color: inherit;
  transition: all 0.15s;
}

.nav-card:hover { background: #eff6ff; border-color: #93c5fd; }

.nav-icon { font-size: 1.5rem; flex-shrink: 0; }
.nav-title { font-size: 0.9rem; font-weight: 700; color: #1e293b; }
.nav-desc  { font-size: 0.75rem; color: #64748b; margin-top: 2px; }

.api-title { font-size: 0.8rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
.api-links ul { padding-left: 16px; }
.api-links li { margin-bottom: 4px; font-size: 0.85rem; }
a { color: #2563eb; }
</style>
