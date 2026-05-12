---
title: "Prompt Patterns"
category: llm
tags: [prompt, few-shot, chain-of-thought, structured-output, template]
status: stable
updated: 2026-05-12
---

# Prompt Patterns

## Pattern 1: Role + Task + Format (RTF)

โครงสร้างพื้นฐานที่ใช้ใน skill ทุกตัว

```markdown
คุณคือ [ROLE] ของทีม AI
งาน: [TASK_DESCRIPTION]

## Context
[RELEVANT_CONTEXT]

## ข้อมูล Input
[USER_INPUT]

## Output Format
ตอบเป็น JSON:
{
  "summary": "...",
  "action": "...",
  "confidence": 0-1
}
```

**เมื่อไรใช้**: งานทั่วไปที่ต้องการ structured output

---

## Pattern 2: Chain-of-Thought (CoT)

```markdown
วิเคราะห์ทีละขั้น:
1. ทำความเข้าใจปัญหา
2. ระบุ constraints
3. หา solution candidates
4. ประเมิน trade-offs
5. สรุป recommendation

คำถาม: [QUESTION]

ให้เดินตาม 5 ขั้นข้างต้นก่อนสรุป
```

**เมื่อไรใช้**: งานที่ต้องการ reasoning ลึก เช่น debug, architecture decision

---

## Pattern 3: Few-Shot Examples

```markdown
ตัวอย่าง:
Input: "cpu usage 95%"
Output: {"severity": "critical", "action": "scale_up", "agent": "observer"}

Input: "disk 60%"
Output: {"severity": "warning", "action": "monitor", "agent": "observer"}

ตอนนี้:
Input: "[USER_INPUT]"
Output:
```

**เมื่อไรใช้**: งานที่ต้องการ format ที่แน่นอนหรือ domain-specific classification

---

## Pattern 4: Decompose + Delegate

```markdown
งานหลัก: [COMPLEX_TASK]

แบ่งเป็น subtask:
1. [SUBTASK_1] → มอบให้ [AGENT_1]
2. [SUBTASK_2] → มอบให้ [AGENT_2]
3. สังเคราะห์ผล → [MANAGER_AGENT]

ทำ subtask 1 ก่อน:
```

**เมื่อไรใช้**: งาน multi-agent, workflow orchestration

---

## Pattern 5: Constraint-First

```markdown
กฎที่ห้ามละเมิด:
- ห้ามเปิดเผย API key หรือ secret
- ห้าม deploy production โดยไม่ได้รับ approval
- ห้ามลบข้อมูลโดยไม่มี backup

ภายใต้กฎข้างต้น:
[TASK]
```

**เมื่อไรใช้**: security-sensitive tasks, production operations

---

## Anti-Patterns ที่ต้องหลีกเลี่ยง

| Anti-Pattern | ปัญหา | แก้ด้วย |
|-------------|-------|---------|
| Prompt ยาวโดยไม่จำเป็น | เพิ่ม token cost, attention dilution | ตัดส่วนที่ไม่เกี่ยวออก |
| ไม่ระบุ format output | ได้ผลลัพธ์ที่ parse ยาก | กำหนด JSON schema ชัดเจน |
| ใช้คำกำกวม ("do it nicely") | ผลลัพธ์ไม่แน่นอน | ระบุ metric/criterion ที่วัดได้ |
| ถามหลายเรื่องในครั้งเดียว | ตอบพลาดบางส่วน | แยก prompt ต่อ subtask |

---

## Template ใน ai-control-center

Skill prompt templates อยู่ที่ `core/skills/<skill-name>/SKILL.md`

โครงสร้าง SKILL.md:
```yaml
skill_name: xxx
description: xxx
prompt_template: |
  [ROLE]
  [TASK]
  [CONTEXT_PLACEHOLDER]
  [FORMAT]
agents: [list]
workflows: [list]
```
