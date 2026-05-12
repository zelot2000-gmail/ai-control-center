# R&D Benchmark Report — AI Control Center
**agent**: research  
**task_id**: rd-bench-2026-001  
**risk_level**: 1 (read-only analysis)  
**mode**: hybrid  
**timestamp**: 2026-05-11  
**environment**: static code + architecture analysis

---

## วัตถุประสงค์
ประเมินความพร้อมของ stack ปัจจุบัน ระบุจุดที่ควรปรับ และ R&D candidates สำหรับ production readiness

---

## 1. Stack Summary

| Component | Technology | Version | Status |
|-----------|-----------|---------|--------|
| API Framework | FastAPI + uvicorn | 0.111/0.29 | ✅ Stable |
| Runtime | Python | 3.11-slim | ✅ LTS |
| Vector Store | Qdrant | v1.9.2 | ✅ Stable |
| Embedding Model | sentence-transformers (MiniLM-L12-v2) | 3.0.1 | ✅ Good |
| ML Framework | torch | 2.3.0 | ✅ Current |
| Database | Postgres 15 | latest | ✅ Stable |
| Cache | Redis 7 | latest | ✅ Stable |
| Reverse Proxy | nginx | alpine | ✅ Minimal |
| Orchestration | Docker Compose | v2 | ✅ Dev-ready |

---

## 2. Performance Analysis

### 2.1 TTO API (Thai Token Optimizer)
**สถานะ**: Fallback mode เท่านั้น — TTO CLI ไม่ได้ connect

```
ตรวจ: services/tto-api/app/main.py:128-130
if TTO_CLI_PATH:
    logger.info("TTO CLI available at %s — adapter not yet implemented, using fallback")
```

**Fallback performance** (static analysis):
- Regex-based whitespace normalization: O(n) — fast
- Token estimate: `len(text) // 4` — crude approximation
- ไม่มี actual Thai tokenizer เชื่อมต่อ

**Impact**: การ estimate token ไม่แม่นยำ → อาจส่ง prompt ยาวเกินไปให้ agent

**Recommendation**: เชื่อมต่อ `pythainlp` หรือ `newmm` tokenizer สำหรับ Thai-accurate token counting

---

### 2.2 RAG API — Embedding Performance
**Model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Model size: ~470MB
- Inference speed: ~50ms per query (CPU), ~5ms (GPU)
- Docker build time: ยาวมาก เพราะ `torch==2.3.0` (~3-4 GB)

**ข้อดี**: ครอบคลุมภาษาไทย multilingual
**ข้อเสีย**: torch ขนาดใหญ่ทำให้ image หนัก

**Recommendation (R&D)**: ทดสอบ `BAAI/bge-m3` หรือ `intfloat/multilingual-e5-base` ใน research profile ก่อน

---

### 2.3 Task Storage
**สถานะ**: `tasks.json` flat file

```python
TASKS_FILE = "/app/data/tasks.json"
def _save_tasks(tasks: dict):
    with open(TASKS_FILE, "w", ...) as f:
        json.dump(tasks, f, ...)
```

**ปัญหา**:
- ไม่มี locking → concurrent writes อาจ corrupt file
- ไม่มี pagination → tasks.json จะโตขึ้นเรื่อยๆ
- ไม่มี TTL → tasks เก่าไม่ถูกลบ

**Recommendation**: ย้ายไปใช้ Postgres ที่มีอยู่แล้ว ใช้ `asyncpg` หรือ `SQLAlchemy 2.0 async`

---

### 2.4 Worker / Agent Bridge
**สถานะ**: Export prompt เป็น `.md` file เท่านั้น

```python
if HERMES_CLI_PATH:
    logger.info("Hermes CLI adapter not yet implemented — using export fallback")
if AGENTUNIVERSE_CLI_PATH:
    logger.info("agentUniverse CLI adapter not yet implemented — using export fallback")
```

**Impact**: Agent ไม่ได้รัน actual execution — prompt แค่ถูก export ไม่ได้ส่งต่อจริง
**Priority**: สูง — นี่คือ core functionality ที่ยังไม่สมบูรณ์

---

### 2.5 Rate Limiting
**สถานะ**: ไม่มีในทุก service
- `POST /tasks` — ไม่มี limit
- `POST /search` — ไม่มี limit
- `POST /run-command` — disabled แต่ถ้าเปิด ไม่มี limit

**Recommendation**: เพิ่ม `slowapi` (FastAPI rate limiter) หรือ nginx `limit_req`

---

## 3. R&D Candidates

| Candidate | วัตถุประสงค์ | Effort | Adoption Status |
|-----------|------------|--------|----------------|
| `asyncpg` + Postgres tasks | แทน tasks.json | Low | **staging** |
| `slowapi` rate limiting | rate limit ทุก endpoint | Low | **staging** |
| `pythainlp` tokenizer | Thai token count แม่นยำ | Medium | **PoC only** |
| `BAAI/bge-m3` embedding | เปรียบเทียบกับ MiniLM | High (GPU) | **keep watching** |
| Hermes CLI integration | actual agent execution | High | **PoC only** |
| `redis-py` task queue | แทน flat file + async worker | Medium | **staging** |
| nginx `limit_req` | rate limiting via proxy | Low | **staging** |

---

## 4. Architecture Health Score

| Dimension | Score | หมายเหตุ |
|-----------|-------|---------|
| Separation of concerns | 8/10 | Services แยกชัดดี |
| Security baseline | 6/10 | พบ 2 High ที่แก้แล้ว |
| Observability | 7/10 | observer service มี, แต่ไม่มี structured log |
| Scalability | 5/10 | flat file storage เป็น bottleneck |
| Dev experience | 9/10 | Docker Compose + Makefile ครบ |
| Production readiness | 6/10 | prod compose พร้อม, แต่ agent bridge ยังไม่สมบูรณ์ |

**Overall**: 6.8/10 — พร้อม dev/staging แต่ต้องแก้ก่อน production

---

## 5. Priority Fix List (จาก R&D perspective)

1. **[High]** เชื่อม Hermes/agentUniverse bridge → worker ให้รัน agent จริง
2. **[High]** ย้าย task storage → Postgres
3. **[Medium]** เพิ่ม rate limiting
4. **[Medium]** เชื่อม Thai tokenizer ใน TTO fallback
5. **[Low]** ทดสอบ embedding model ทางเลือกใน research profile

---

## Accountability Log
```yaml
owner_agent: research
workflow: N/A (agent mode — open-ended analysis)
tool_usage_log: [file-read, static-code-analysis, architecture-review]
verification_log: [code-pattern-check, dependency-audit]
adoption_status_per_item: see R&D Candidates table
rollback_plan: N/A — read-only analysis
```
