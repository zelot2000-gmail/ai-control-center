<template>
  <div class="page">
    <div class="header">
      <div>
        <h1 class="title">⚙️ Provider Settings</h1>
        <p class="subtitle">Hermes / 9Router / ChatGPT / OpenAI-compatible</p>
      </div>
      <div class="header-links">
        <a href="/command" class="link-chip">→ Command</a>
        <a href="/jobs" class="link-chip">→ Jobs</a>
      </div>
    </div>

    <div v-if="loadError" class="error-box">⚠️ {{ loadError }}</div>
    <div v-if="loading" class="loading-box">⏳ Loading current settings…</div>

    <!-- ── SECTION A: AGENT RUNNER ── -->
    <section class="card">
      <div class="card-title">A. Agent Runner</div>
      <div class="grid">
        <label class="field">
          <span class="field-label">Agent Runner Enabled</span>
          <div class="checkbox-row">
            <input type="checkbox" v-model="form.agent_runner_enabled" id="ar_en"/>
            <label for="ar_en" class="checkbox-label">{{ form.agent_runner_enabled ? 'enabled' : 'disabled' }}</label>
          </div>
        </label>
        <label class="field">
          <span class="field-label">Runner Mode</span>
          <select v-model="form.agent_runner_mode" class="input">
            <option value="prompt_only">prompt_only</option>
            <option value="hermes_manual">hermes_manual</option>
            <option value="hermes_http">hermes_http</option>
          </select>
        </label>
      </div>
    </section>

    <!-- ── SECTION B: PROVIDER ── -->
    <section class="card">
      <div class="card-title">B. Provider</div>
      <div class="grid">
        <label class="field">
          <span class="field-label">Provider</span>
          <select v-model="form.hermes_provider" class="input" @change="applyPreset">
            <option value="hermes_native">hermes_native</option>
            <option value="9router">9router</option>
            <option value="openrouter">openrouter</option>
            <option value="chatgpt">chatgpt</option>
            <option value="openai_compatible">openai_compatible</option>
            <option value="local_lmstudio">local_lmstudio</option>
          </select>
        </label>
        <label class="field">
          <span class="field-label">Request Format</span>
          <select v-model="form.hermes_request_format" class="input">
            <option value="native">native</option>
            <option value="openai_compatible">openai_compatible</option>
          </select>
        </label>
        <label class="field field-full">
          <span class="field-label">API URL</span>
          <input v-model="form.hermes_api_url" class="input" placeholder="https://… or http://host.docker.internal:…"/>
        </label>
        <label class="field field-full">
          <span class="field-label">Model</span>
          <input v-model="form.hermes_model" class="input" placeholder="e.g. gpt-4o-mini, anthropic/claude-3-haiku, …"/>
        </label>
      </div>
    </section>

    <!-- ── SECTION C: CREDENTIALS ── -->
    <section class="card">
      <div class="card-title">C. Credentials</div>
      <div class="grid">
        <label class="field field-full">
          <span class="field-label">API Key</span>
          <div class="input-row">
            <input
              :type="showKey ? 'text' : 'password'"
              v-model="form.hermes_api_key"
              class="input"
              :placeholder="serverState.hermes_api_key_set ? '(existing key on server — leave blank to keep)' : 'sk-…'"
            />
            <button type="button" class="btn btn-ghost" @click="showKey = !showKey">
              {{ showKey ? '🙈 Hide' : '👁 Show' }}
            </button>
          </div>
          <span class="hint">
            Server status: API key
            <span :class="serverState.hermes_api_key_set ? 'pill-green' : 'pill-gray'">
              {{ serverState.hermes_api_key_set ? 'set' : 'not set' }}
            </span>
            — never displayed; values entered here are only sent for test or save.
          </span>
        </label>
      </div>
    </section>

    <!-- ── SECTION D: RUNTIME ── -->
    <section class="card">
      <div class="card-title">D. Runtime</div>
      <div class="grid">
        <label class="field">
          <span class="field-label">Fallback Mode</span>
          <select v-model="form.hermes_fallback_mode" class="input">
            <option value="hermes_manual">hermes_manual</option>
            <option value="prompt_only">prompt_only</option>
          </select>
        </label>
        <label class="field">
          <span class="field-label">Timeout (seconds)</span>
          <input v-model.number="form.hermes_timeout_seconds" type="number" min="1" class="input"/>
        </label>
        <label class="field">
          <span class="field-label">Retry Attempts</span>
          <input v-model.number="form.hermes_retry_attempts" type="number" min="0" class="input"/>
        </label>
        <label class="field">
          <span class="field-label">Retry Backoff (seconds)</span>
          <input v-model.number="form.hermes_retry_backoff_seconds" type="number" min="0" step="0.5" class="input"/>
        </label>
        <label class="field field-full">
          <span class="field-label">Temperature <span class="field-hint">(optional)</span></span>
          <input
            v-model="form.hermes_temperature"
            type="number"
            min="0" max="2" step="0.1"
            class="input"
            placeholder="blank = provider default"
          />
          <span class="hint" v-if="form.hermes_provider === 'chatgpt'">
            ℹ️ Some OpenAI models (GPT-5 / reasoning) only support default temperature. Leave blank if unsure — if the model rejects, we'll retry without it automatically.
          </span>
        </label>
      </div>
    </section>

    <!-- ── SECTION E: TEST CONNECTION ── -->
    <section class="card">
      <div class="card-title">E. Test Connection</div>
      <div class="grid">
        <label class="field field-full">
          <span class="field-label">Test Prompt</span>
          <input v-model="testPrompt" class="input" placeholder="Say OK"/>
        </label>
      </div>
      <div class="actions">
        <button class="btn btn-primary" :disabled="testing" @click="testConnection">
          {{ testing ? '⏳ Testing…' : '🔌 Test Connection' }}
        </button>
        <button class="btn btn-secondary" :disabled="saving" @click="saveSettings">
          {{ saving ? '⏳ Saving…' : '💾 Save Settings (local runtime)' }}
        </button>
      </div>
      <div v-if="testResult" class="test-result" :class="testResult.ok ? 'tr-ok' : 'tr-err'">
        <div class="tr-row">
          <span class="tr-label">Status</span>
          <span class="tr-val">{{ testResult.ok ? '✅ OK' : '❌ FAIL' }}</span>
        </div>
        <div class="tr-row" v-if="testResult.http_status !== null && testResult.http_status !== undefined">
          <span class="tr-label">HTTP</span>
          <span class="tr-val">{{ testResult.http_status }}</span>
        </div>
        <div class="tr-row" v-if="testResult.response_format">
          <span class="tr-label">Format</span>
          <span class="tr-val">{{ testResult.response_format }}</span>
        </div>
        <div class="tr-row" v-if="testResult.latency_ms !== undefined">
          <span class="tr-label">Latency</span>
          <span class="tr-val">{{ testResult.latency_ms }} ms</span>
        </div>
        <div class="tr-row" v-if="testResult.message">
          <span class="tr-label">Message</span>
          <span class="tr-val">{{ testResult.message }}</span>
        </div>
        <div class="tr-row" v-if="testResult.retried_without_temperature">
          <span class="tr-label">Retry</span>
          <span class="tr-val">🌡️ temperature unsupported by model — retried without it</span>
        </div>
        <div class="tr-row" v-if="testResult.error_message">
          <span class="tr-label">Error</span>
          <span class="tr-val tr-error">{{ testResult.error_message }}</span>
        </div>
        <div class="tr-row" v-if="errorClassification">
          <span class="tr-label">Diagnosis</span>
          <span class="tr-val">{{ errorClassification }}</span>
        </div>
        <div class="tr-row" v-if="testResult.fallback_mode">
          <span class="tr-label">Fallback</span>
          <span class="tr-val">{{ testResult.fallback_mode }}</span>
        </div>
        <!-- Safe debug fields (never the key itself) -->
        <div class="tr-debug">
          <span>api_key_set: <code>{{ String(testResult.api_key_set ?? '—') }}</code></span>
          <span>api_key_length: <code>{{ testResult.api_key_length ?? '—' }}</code></span>
          <span>headers_authorization_set: <code>{{ String(testResult.headers_authorization_set ?? '—') }}</code></span>
        </div>
        <pre v-if="testResult.sample" class="tr-sample">{{ testResult.sample }}</pre>
      </div>
      <div v-if="saveResult" class="save-result" :class="saveResult.ok ? 'tr-ok' : 'tr-err'">
        <div>{{ saveResult.ok ? '✅ ' : '❌ ' }}{{ saveResult.message }}</div>
        <div v-if="saveResult.next_steps" class="save-hint">{{ saveResult.next_steps }}</div>
      </div>
    </section>

    <!-- ── SECTION F: GENERATED .ENV CONFIG ── -->
    <section class="card">
      <div class="card-title">F. Generated .env Config</div>
      <p class="card-hint">Copy this block into your <code>.env</code> file. API key is redacted in this preview.</p>
      <pre class="env-block">{{ envConfig }}</pre>
      <div class="actions">
        <button class="btn btn-primary" @click="copyEnv">📋 Copy .env Config</button>
      </div>
    </section>

    <!-- ── SECTION G: COMMAND SOURCES ── -->
    <section class="card">
      <div class="card-title">G. Supported Command Sources</div>
      <p class="card-hint">ChatGPT command sources supported across mobile-gateway / webhook-gateway:</p>
      <div class="source-badges">
        <span class="src-badge src-chatgpt">ChatGPT</span>
        <span class="src-badge src-chatgpt">chatgpt-mobile</span>
        <span class="src-badge src-dashboard">Dashboard</span>
        <span class="src-badge src-mobile">Mobile</span>
        <span class="src-badge src-webhook">Webhook</span>
        <span class="src-badge src-manual">Manual</span>
      </div>
    </section>
  </div>
</template>

<script setup>
const config = useRuntimeConfig()
const WORKER = config.public.workerBase

const loading    = ref(true)
const loadError  = ref('')
const showKey    = ref(false)
const testing    = ref(false)
const saving     = ref(false)
const testPrompt = ref('Say OK')

const form = ref({
  agent_runner_enabled: false,
  agent_runner_mode: 'prompt_only',
  hermes_provider: 'openai_compatible',
  hermes_request_format: 'native',
  hermes_api_url: '',
  hermes_model: '',
  hermes_api_key: '',
  hermes_fallback_mode: 'hermes_manual',
  hermes_timeout_seconds: 120,
  hermes_retry_attempts: 1,
  hermes_retry_backoff_seconds: 2,
  hermes_temperature: '',  // blank = provider default
})

function parseTemperature(v) {
  if (v === '' || v === null || v === undefined) return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

const serverState = ref({
  hermes_api_key_set: false,
})

const testResult = ref(null)
const saveResult = ref(null)

const PRESETS = {
  hermes_native: {
    hermes_provider: 'hermes_native',
    hermes_request_format: 'native',
    hermes_api_url: 'http://host.docker.internal:20199',
  },
  '9router': {
    hermes_provider: '9router',
    hermes_request_format: 'openai_compatible',
    hermes_api_url: '',
  },
  openrouter: {
    hermes_provider: 'openrouter',
    hermes_request_format: 'openai_compatible',
    hermes_api_url: 'https://openrouter.ai/api/v1/chat/completions',
  },
  chatgpt: {
    hermes_provider: 'chatgpt',
    hermes_request_format: 'openai_compatible',
    hermes_api_url: 'https://api.openai.com/v1/chat/completions',
  },
  openai_compatible: {
    hermes_provider: 'openai_compatible',
    hermes_request_format: 'openai_compatible',
    hermes_api_url: '',
  },
  local_lmstudio: {
    hermes_provider: 'local_lmstudio',
    hermes_request_format: 'openai_compatible',
    hermes_api_url: 'http://host.docker.internal:1234/v1/chat/completions',
  },
}

function applyPreset() {
  const p = PRESETS[form.value.hermes_provider]
  if (!p) return
  form.value.hermes_request_format = p.hermes_request_format
  if (!form.value.hermes_api_url || p.hermes_api_url) {
    form.value.hermes_api_url = p.hermes_api_url
  }
}

const errorClassification = computed(() => {
  const msg = (testResult.value?.error_message || '').toLowerCase()
  if (!msg) return ''
  if (msg.includes("didn't provide an api key") || msg.includes('missing') && msg.includes('api key')) {
    return '🔑 Missing API key — frontend ไม่ได้ส่ง key หรือ backend ไม่ได้แนบ Authorization header'
  }
  if (msg.includes('invalid_api_key') || msg.includes('incorrect api key')) {
    return '🔐 Invalid key — ส่ง key ไปแล้ว แต่ provider ปฏิเสธ (key ผิด/ถูก revoke)'
  }
  if (msg.includes('insufficient_quota') || msg.includes('billing')) {
    return '💳 Quota/billing — key ถูก แต่บัญชี/เครดิตยังไม่พร้อม'
  }
  if (msg.includes('rate limit') || msg.includes('429')) {
    return '⏱️ Rate limited — ลองใหม่ในอีกสักครู่'
  }
  if (msg.includes('temperature') && (msg.includes('unsupported') || msg.includes('does not support'))) {
    return '🌡️ Model ไม่รองรับ temperature — เว้นช่อง Temperature ว่างไว้ หรือ backend จะ retry without temperature ให้อัตโนมัติ'
  }
  return ''
})

const envConfig = computed(() => {
  const k = '<REDACTED>'
  const lines = [
    `AGENT_RUNNER_ENABLED=${form.value.agent_runner_enabled ? 'true' : 'false'}`,
    `AGENT_RUNNER_MODE=${form.value.agent_runner_mode}`,
    `HERMES_PROVIDER=${form.value.hermes_provider}`,
    `HERMES_REQUEST_FORMAT=${form.value.hermes_request_format}`,
    `HERMES_API_URL=${form.value.hermes_api_url}`,
    `HERMES_MODEL=${form.value.hermes_model}`,
    `HERMES_API_KEY=${k}`,
    `HERMES_TIMEOUT_SECONDS=${form.value.hermes_timeout_seconds}`,
    `HERMES_RETRY_ATTEMPTS=${form.value.hermes_retry_attempts}`,
    `HERMES_RETRY_BACKOFF_SECONDS=${form.value.hermes_retry_backoff_seconds}`,
    `HERMES_FALLBACK_MODE=${form.value.hermes_fallback_mode}`,
    `HERMES_TEMPERATURE=${form.value.hermes_temperature ?? ''}`,
  ]
  return lines.join('\n')
})

async function loadCurrent() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await fetch(`${WORKER}/settings/provider`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    serverState.value.hermes_api_key_set = !!data.hermes_api_key_set
    form.value = {
      agent_runner_enabled: !!data.agent_runner_enabled,
      agent_runner_mode: data.agent_runner_mode || 'prompt_only',
      hermes_provider: data.hermes_provider || 'openai_compatible',
      hermes_request_format: data.hermes_request_format || 'native',
      hermes_api_url: data.hermes_api_url || '',
      hermes_model: data.hermes_model || '',
      hermes_api_key: '',
      hermes_fallback_mode: data.hermes_fallback_mode || 'hermes_manual',
      hermes_timeout_seconds: data.hermes_timeout_seconds ?? 120,
      hermes_retry_attempts: data.hermes_retry_attempts ?? 1,
      hermes_retry_backoff_seconds: data.hermes_retry_backoff_seconds ?? 2,
      hermes_temperature: (data.hermes_temperature === null || data.hermes_temperature === undefined) ? '' : String(data.hermes_temperature),
    }
  } catch (e) {
    loadError.value = `Cannot load settings from worker (${WORKER}): ${e.message}`
  } finally {
    loading.value = false
  }
}

const PROVIDERS_REQUIRE_KEY = ['chatgpt', 'openrouter', '9router', 'openai_compatible']

function needsApiKey() {
  return form.value.hermes_request_format === 'openai_compatible'
    && PROVIDERS_REQUIRE_KEY.includes(form.value.hermes_provider)
}

async function testConnection() {
  testing.value = true
  testResult.value = null
  const trimmedKey = (form.value.hermes_api_key || '').trim()

  if (needsApiKey() && !trimmedKey) {
    const ok = confirm('⚠️ Provider นี้ต้องมี API key — ยังไม่ได้กรอก. กด OK เพื่อยิงไปดูผล หรือ Cancel เพื่อกลับไปกรอก key')
    if (!ok) {
      testing.value = false
      return
    }
  }

  try {
    const body = {
      provider: form.value.hermes_provider,
      request_format: form.value.hermes_request_format,
      api_url: (form.value.hermes_api_url || '').trim(),
      api_key: trimmedKey,
      model: (form.value.hermes_model || '').trim(),
      test_prompt: testPrompt.value || 'Say OK',
    }
    const temp = parseTemperature(form.value.hermes_temperature)
    if (temp !== null) body.temperature = temp

    const res = await fetch(`${WORKER}/settings/provider/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json().catch(() => ({}))
    testResult.value = data
  } catch (e) {
    testResult.value = { ok: false, error_message: e.message }
  } finally {
    testing.value = false
  }
}

async function saveSettings() {
  saving.value = true
  saveResult.value = null
  const trimmedKey = (form.value.hermes_api_key || '').trim()

  try {
    const payload = {
      agent_runner_enabled: form.value.agent_runner_enabled,
      agent_runner_mode: form.value.agent_runner_mode,
      hermes_provider: form.value.hermes_provider,
      hermes_request_format: form.value.hermes_request_format,
      hermes_api_url: (form.value.hermes_api_url || '').trim(),
      hermes_model: (form.value.hermes_model || '').trim(),
      hermes_fallback_mode: form.value.hermes_fallback_mode,
      hermes_timeout_seconds: form.value.hermes_timeout_seconds,
      hermes_retry_attempts: form.value.hermes_retry_attempts,
      hermes_retry_backoff_seconds: form.value.hermes_retry_backoff_seconds,
    }
    const savedTemp = parseTemperature(form.value.hermes_temperature)
    if (savedTemp !== null) payload.hermes_temperature = savedTemp
    if (trimmedKey) payload.hermes_api_key = trimmedKey

    const res = await fetch(`${WORKER}/settings/provider`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      saveResult.value = { ok: false, message: err.detail || `HTTP ${res.status}` }
      return
    }
    const data = await res.json()
    saveResult.value = {
      ok: true,
      message: data.message || 'Saved to local runtime file',
      next_steps: '⚠️ Settings written. To activate: rebuild + restart worker, then click Test Connection (or wait for chained auto-test below).',
    }
    serverState.value.hermes_api_key_set = !!data.hermes_api_key_set

    // ── Save is the final step — chain a verification test against the just-saved values
    // (uses the entered api_key before we clear it from the form)
    testResult.value = null
    testing.value = true
    try {
      const testBody = {
        provider: form.value.hermes_provider,
        request_format: form.value.hermes_request_format,
        api_url: (form.value.hermes_api_url || '').trim(),
        api_key: trimmedKey,
        model: (form.value.hermes_model || '').trim(),
        test_prompt: testPrompt.value || 'Say OK',
      }
      const chainedTemp = parseTemperature(form.value.hermes_temperature)
      if (chainedTemp !== null) testBody.temperature = chainedTemp

      const testRes = await fetch(`${WORKER}/settings/provider/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(testBody),
      })
      testResult.value = await testRes.json().catch(() => ({}))
    } catch (e) {
      testResult.value = { ok: false, error_message: e.message }
    } finally {
      testing.value = false
    }

    form.value.hermes_api_key = ''
  } catch (e) {
    saveResult.value = { ok: false, message: e.message }
  } finally {
    saving.value = false
  }
}

async function copyEnv() {
  try {
    await navigator.clipboard.writeText(envConfig.value)
    alert('✅ .env config copied to clipboard (API key redacted)')
  } catch {
    alert('Copy not supported in this browser')
  }
}

onMounted(loadCurrent)
</script>

<style scoped>
*, *::before, *::after { box-sizing: border-box; }

.page {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #0f172a;
  color: #e2e8f0;
  min-height: 100vh;
  padding: 1.25rem;
  max-width: 900px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.title { font-size: 1.4rem; font-weight: 700; color: #f1f5f9; margin: 0; }
.subtitle { font-size: 0.82rem; color: #94a3b8; margin: 4px 0 0 0; }
.header-links { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.link-chip {
  font-size: 0.75rem;
  color: #93c5fd;
  background: #1e293b;
  padding: 4px 10px;
  border-radius: 999px;
  text-decoration: none;
  border: 1px solid #1e3a5f;
}
.link-chip:hover { background: #1e3a5f; }

.error-box {
  background: #450a0a; color: #fca5a5;
  padding: 0.6rem 0.9rem; border-radius: 8px; margin-bottom: 1rem; font-size: 0.85rem;
}
.loading-box {
  background: #1e293b; color: #94a3b8;
  padding: 0.6rem 0.9rem; border-radius: 8px; margin-bottom: 1rem; font-size: 0.85rem;
}

.card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 1rem 1.1rem;
  margin-bottom: 0.85rem;
}
.card-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #f1f5f9;
  margin-bottom: 0.7rem;
  letter-spacing: 0.02em;
}
.card-hint {
  font-size: 0.78rem;
  color: #94a3b8;
  margin: 0 0 0.5rem 0;
  line-height: 1.5;
}
.card-hint code { font-family: monospace; color: #fbbf24; }

.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}
.field { display: flex; flex-direction: column; gap: 4px; }
.field-full { grid-column: 1 / -1; }
.field-label {
  font-size: 0.72rem;
  color: #94a3b8;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.input {
  background: #0f172a;
  color: #e2e8f0;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 0.45rem 0.65rem;
  font-size: 0.85rem;
  font-family: inherit;
  width: 100%;
}
.input:focus { outline: none; border-color: #3b82f6; }
select.input { cursor: pointer; }
.input-row { display: flex; gap: 0.4rem; }
.checkbox-row {
  display: flex; align-items: center; gap: 6px;
  padding: 0.45rem 0.65rem;
  background: #0f172a; border: 1px solid #334155; border-radius: 6px;
}
.checkbox-label { font-size: 0.82rem; color: #cbd5e1; }
.hint {
  font-size: 0.72rem;
  color: #64748b;
  margin-top: 2px;
}
.pill-green { background: #064e3b; color: #34d399; padding: 1px 7px; border-radius: 999px; font-weight: 600; }
.pill-gray  { background: #334155; color: #94a3b8; padding: 1px 7px; border-radius: 999px; font-weight: 600; }

.actions { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.65rem; }
.btn {
  font-size: 0.82rem;
  font-weight: 600;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn:disabled { opacity: 0.55; cursor: not-allowed; }
.btn-primary   { background: #1d4ed8; color: #fff; }
.btn-secondary { background: #6d28d9; color: #fff; }
.btn-ghost     { background: #334155; color: #cbd5e1; }
.btn:hover:not(:disabled) { opacity: 0.88; }

.test-result, .save-result {
  margin-top: 0.75rem;
  padding: 0.65rem 0.85rem;
  border-radius: 8px;
  font-size: 0.82rem;
  border: 1px solid;
}
.tr-ok  { background: #022c22; border-color: #065f46; color: #a7f3d0; }
.tr-err { background: #1c0a0a; border-color: #7f1d1d; color: #fca5a5; }
.tr-row { display: flex; gap: 0.5rem; padding: 2px 0; }
.tr-label { min-width: 88px; color: inherit; opacity: 0.7; font-weight: 600; }
.tr-val { color: inherit; word-break: break-all; }
.tr-error { color: #fca5a5; }
.tr-sample {
  margin: 6px 0 0 0;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 0.5rem 0.65rem;
  font-family: monospace;
  font-size: 0.74rem;
  color: #cbd5e1;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 180px;
  overflow-y: auto;
}
.tr-debug {
  display: flex; flex-wrap: wrap; gap: 0.7rem;
  margin-top: 0.5rem; padding-top: 0.4rem;
  border-top: 1px dashed rgba(255,255,255,0.12);
  font-size: 0.7rem; opacity: 0.8;
}
.tr-debug code { background: rgba(0,0,0,0.3); padding: 1px 5px; border-radius: 3px; font-family: monospace; }
.save-hint { font-size: 0.74rem; opacity: 0.85; margin-top: 4px; }

.env-block {
  background: #020617;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 0.75rem 0.85rem;
  font-family: monospace;
  font-size: 0.78rem;
  color: #cbd5e1;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0.25rem 0 0.5rem 0;
  line-height: 1.55;
}

.source-badges { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.4rem; }
.src-badge {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 999px;
}
.src-chatgpt   { background: #064e3b; color: #6ee7b7; }
.src-dashboard { background: #1e3a5f; color: #93c5fd; }
.src-mobile    { background: #4c1d95; color: #c4b5fd; }
.src-webhook   { background: #422006; color: #fbbf24; }
.src-manual    { background: #334155; color: #cbd5e1; }

@media (max-width: 600px) {
  .grid { grid-template-columns: 1fr; }
  .field-full { grid-column: 1; }
}
</style>
