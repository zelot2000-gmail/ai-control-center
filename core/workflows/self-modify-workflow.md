# self-modify-workflow

**Purpose:** ให้ AI Control Center แก้ไขโค้ดของตัวเองได้แบบปลอดภัย ภายใต้ allowlist + approval gate

**Pipeline:** `Chat → Plan → Patch → Apply → Verify → Approval → Commit`

---

## Trigger

Mobile-gateway router หรือ /command UI route ไปที่ workflow นี้เมื่อพบ keywords:

- แก้ / ปรับ / เพิ่ม / ลบ
- refactor / bug / fix
- UI / component / page
- endpoint / api
- vue / docker / nginx / workflow
- settings / command page / jobs page

ตัวอย่างคำสั่งที่ route ที่นี่:
- "ปรับหน้า command ให้เหมือน ChatGPT"
- "แก้ bug ใน jobs.vue ที่ปุ่ม Save ไม่ทำงาน"
- "เพิ่ม endpoint /healthz ให้ worker"
- "refactor settings.vue ให้แยกเป็น component"

---

## Roles

| Role          | Responsibility                                            |
|---------------|-----------------------------------------------------------|
| manager       | จัดลำดับ, ขอ approval, สรุปรายงาน                            |
| programmer    | สร้าง plan + patch + verification commands                |
| qa            | run verification, รายงานผล PASS/WARNING/FAIL              |
| administrator | (production-only) อนุมัติ commit final                     |

---

## Skills

- `serena-mcp` — semantic file search before edit
- `code-edit` — generate unified diff
- `qa-verify` — run lint/typecheck/build
- `git-safe-commit` — commit with policy enforcement

---

## Risk Classification

| Level | Trigger                                                          | Approval                       |
|------:|------------------------------------------------------------------|--------------------------------|
| 1     | docs/wiki, .env.example, copy text changes                       | none                           |
| 2     | apps/web/{pages,components} CSS/text-only                         | none (apply only, no commit)   |
| 3     | apps/web logic, services/worker code, services/mobile-gateway     | `APPLY PATCH` to apply         |
| 4     | infra/docker/*, infra/nginx/*, .gitignore                         | `APPLY PATCH` + `COMMIT CHANGES` |
| 5     | Touches blocklist or production-impacting (Dockerfile RUN, secrets) | `CONFIRM DANGEROUS`            |

---

## Allowlist (paths editable)

- `apps/web/pages/`
- `apps/web/components/`
- `apps/web/layouts/`
- `services/worker/app/`
- `services/mobile-gateway/app/`
- `services/rag-api/app/`
- `infra/docker/docker-compose.wsl.yml`
- `infra/nginx/default.conf`
- `core/workflows/`
- `core/skills/`
- `docs/wiki/`
- `docs/releases/`
- `.env.example`
- `.gitignore`

## Blocklist (paths NEVER editable, even if user asks)

- `.env`
- `data/**` (runtime — including `data/provider-settings.local.json`)
- `node_modules/**`
- `.git/**`
- `apps/web/.output/**`
- `apps/web/dist/**`
- `apps/web/.nuxt/**`
- `**/*.key`, `**/*.pem`, `**/id_rsa*`
- `**/__pycache__/**`
- Any file whose new content matches `sk-[A-Za-z0-9]{20,}` or `Bearer\s+[A-Za-z0-9_-]{20,}`

---

## Modes

| Mode                  | Behavior                                                 | Default for                |
|-----------------------|----------------------------------------------------------|----------------------------|
| `propose_patch`       | สร้าง patch artifact เท่านั้น ไม่แตะ working tree              | plan-only                  |
| `apply_patch_local`   | apply patch ในตัว container (`/workspace`) ไม่ commit       | dev-fix, risk ≤ 2          |
| `commit_after_approval` | apply + commit หลังได้ phrase                            | risk ≥ 3, staging          |

---

## Endpoints

| Endpoint                  | Method | Auth phrase needed | Behavior                                          |
|---------------------------|--------|--------------------|---------------------------------------------------|
| `/code-edit/plan`         | POST   | —                  | สร้าง plan + patch artifact (provider auto-gen → fallback user diff) |
| `/code-edit/apply`        | POST   | `APPLY PATCH` (risk≥3) | apply saved patch to `/workspace`; save reverse patch |
| `/code-edit/commit`       | POST   | `COMMIT CHANGES` (risk≥3) or `CONFIRM DANGEROUS` (risk=5) | run verification → git commit |
| `/code-edit/rollback`     | POST   | `ROLLBACK PATCH`   | apply reverse patch, restore working tree         |
| `/code-edit/{task_id}`    | GET    | —                  | inspect task state (plan, patch, verification, status) |

---

## State machine

```
patch_proposed
  └─→ patch_applied
        ├─→ verification_passed
        │     ├─→ waiting_commit_approval (risk≥3)
        │     │     └─→ committed
        │     └─→ committed (risk≤2 auto)
        └─→ verification_failed
              ├─→ rolled_back (auto on fail)
              └─→ committed_with_warning (manual override)
```

---

## Verification per area

| Files touched                            | Verification command                                                |
|-------------------------------------------|---------------------------------------------------------------------|
| `apps/web/**`                             | `pnpm --filter web generate`                                        |
| `services/worker/app/**`                  | `python -m compileall services/worker/app`                          |
| `services/mobile-gateway/app/**`          | `python -m compileall services/mobile-gateway/app`                  |
| `infra/docker/docker-compose.wsl.yml`     | `docker compose --env-file .env -f … config`                        |
| `core/workflows/**`, `docs/**`            | (none required)                                                     |
| Always                                    | `git diff --check`, `git status --short`                            |

---

## Git safety rules

- Before any `apply`: working tree must be **clean OR limited to known artifact paths** (`data/`, `apps/web/.output/`). If dirty, return `412 Precondition Failed` unless `force=true` and approval phrase supplied.
- Before any `commit`: re-scan staged files against blocklist + secret regex; reject if match.
- Commit message: take from request body OR auto-generate `feat(self-modify): <one-line summary>` ending with task_id.
- Never use `--no-verify` or `--no-gpg-sign`.
- Never `git reset --hard` or `git checkout .` — use `rollback` endpoint (reverse-patch) instead.

---

## Artifact storage

Per task, under `data/code-edits/<task_id>/`:

- `task.json` — full state (instruction, plan, status, files, verification, timestamps)
- `forward.patch` — unified diff to apply
- `reverse.patch` — unified diff to undo (generated after apply)
- `plan.md` — natural-language plan from planner
- `verification.json` — verification command output (stdout/stderr/exit_code)

Directory is **gitignored** (`data/code-edits/*`).

---

## Out of scope (deferred to v1.1+)

- Multi-file repository-wide refactor (cross-package)
- Automatic test generation
- Branch-per-task workflow (v1 commits on current branch)
- LLM-mediated merge conflict resolution
- Stash management beyond rollback
