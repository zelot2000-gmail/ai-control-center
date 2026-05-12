---
title: "ADR: ทำไมถึงใช้ TTO + RTK Framework"
category: decisions
tags: [adr, tto, rtk, autonomy, risk, accountability, framework]
status: stable
updated: 2026-05-12
---

# ADR: ทำไมถึงใช้ TTO + RTK Framework

## Status

**Accepted** — core governance framework

## Background

### TTO (Tool-Task-Output)
Framework สำหรับกำหนดว่า agent แต่ละตัวมีสิทธิ์ใช้ tool อะไร, ทำ task อะไร, และ output ในรูปแบบไหน

### RTK (Risk-Task-Knowledge)
Framework สำหรับ validate ว่า task ที่จะรันมี risk level ที่เหมาะสม ก่อน execute

## Context

ปัญหาของ unconstrained AI agent:
1. Agent รัน destructive command โดยไม่ได้รับ approval
2. Agent เปิดเผย secret ใน log หรือ output
3. Agent ทำงานนอก scope ที่ได้รับมอบหมาย
4. ไม่มี audit trail ว่า agent ทำอะไรไปบ้าง

## Options ที่พิจารณา

### Option A: Trust agent completely
ไม่มี constraint — agent ตัดสินใจเองทั้งหมด

**ปัญหา**: ไม่ปลอดภัย, production incident risk สูง

### Option B: Human-in-the-loop ทุก step
ทุก action ต้องขอ approval จากมนุษย์

**ปัญหา**: ช้ามาก, defeats the purpose of automation

### Option C: Tiered autonomy (TTO + RTK)
กำหนด autonomy level และ validate risk ก่อน execute — ไม่ต้องขอ approval ทุกครั้ง

## Decision

เลือก **Tiered Autonomy with TTO + RTK (Option C)**

## TTO Framework

ทุก agent มี profile:
```yaml
agent: programmer
allowed_tools: [read_file, write_file, find_symbol, find_references]
forbidden_tools: [execute_shell, access_production, delete_volume]
task_scope: [code_edit, code_review, bug_fix]
output_format: [code, diff, explanation]
```

## RTK Validation

ก่อน execute command:
```
R (Risk): ประเมิน risk level 1-5
T (Task): เช็คว่า task อยู่ใน agent scope
K (Knowledge): ตรวจว่ามีข้อมูลเพียงพอก่อนดำเนินการ

ถ้า R ≥ 4 → ต้องขอ CONFIRM phrase
ถ้า T ไม่อยู่ใน scope → reject
ถ้า K ไม่พอ → request more context
```

## Autonomy Level Table

| Level | Action | Example | Approval |
|-------|--------|---------|---------|
| 0 | Read-only | ดูไฟล์, ค้นหา | — |
| 1 | Plan/suggest | เสนอ solution | — |
| 2 | Safe workflow | health check, test | — |
| 3 | Edit dev files | แก้ code ใน dev | — |
| 4 | Staging | deploy staging | CONFIRM STAGING |
| 5 | Production | deploy prod | CONFIRM DEPLOY |

## เหตุผลที่เลือก

1. **Balance automation vs safety**: agent ทำงานอิสระได้ระดับต่ำ แต่ต้องขอ approval ระดับสูง
2. **Auditability**: RTK validation สร้าง log ที่ชัดเจน
3. **Scalable**: เพิ่ม agent ใหม่ได้โดยแค่กำหนด TTO profile
4. **Principle of least privilege**: agent ได้รับ permission เฉพาะที่จำเป็น

## Consequences

- ต้องดูแล TTO profile ของทุก agent
- RTK validation เพิ่ม latency เล็กน้อย
- ได้ความปลอดภัยและ auditability

## Review

ทบทวนถ้า:
- Agent capabilities เพิ่มขึ้นมาก
- มี agent ประเภทใหม่ที่ไม่ fit กับ level ปัจจุบัน
