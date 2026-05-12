# Prompt: Hermes Worker Bridge

## System
Bridge layer สำหรับส่งงานไปยัง Hermes agent framework

## Status
Hermes bridge เป็น adapter pattern — ถ้า Hermes CLI ไม่พร้อม จะ fallback เป็น local prompt export

## Input
Task Packet จาก Manager Agent

## Behavior

### ถ้า HERMES_CLI_PATH ตั้งค่าแล้ว
1. serialize task packet เป็น JSON
2. เรียก hermes CLI: `hermes run --task task.json`
3. รอ output
4. parse result กลับ
5. ส่ง report ให้ Manager

### ถ้า HERMES_CLI_PATH ว่าง (fallback)
1. สร้าง prompt จาก task packet
2. export ไป data/exports/{task_id}.prompt.md
3. return status: "exported_for_manual_review"
4. แจ้ง path ของ export file

## Export Format
```markdown
# Task: {task_id}

## Intent
{intent}

## Context
{optimized_context}

## Agents
{agents}

## Skills
{skills}

## Instructions
{plan_steps}

## Constraints
{constraints}
```

## Error Handling
- Hermes timeout → fallback to export
- Hermes error → log + report failure
- ห้าม expose secret ใน export file
