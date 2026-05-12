# Prompt: agentUniverse Bridge

## System
Bridge layer สำหรับส่งงานไปยัง agentUniverse framework

## Status
agentUniverse bridge เป็น adapter pattern — ถ้า CLI ไม่พร้อม จะ fallback เป็น local prompt export

## Input
Task Packet จาก Manager Agent

## Behavior

### ถ้า AGENTUNIVERSE_CLI_PATH ตั้งค่าแล้ว
1. map task packet → agentUniverse job format
2. เรียก CLI: `agentuniverse submit --job job.yaml`
3. รอ result
4. parse และส่ง report กลับ

### ถ้า AGENTUNIVERSE_CLI_PATH ว่าง (fallback)
1. สร้าง agentUniverse job YAML จาก task packet
2. export ไป data/exports/{task_id}.au-job.yaml
3. return status: "exported_for_agentUniverse"

## agentUniverse Job Format (YAML)
```yaml
job_id: "{task_id}"
intent: "{intent}"
agents:
  - id: "{agent_id}"
    skills: {skills}
context: |
  {optimized_context}
constraints:
  environment: "{environment}"
  mode: "{mode}"
```

## Notes
- agentUniverse ทำงานใน port 8095 (worker service)
- ยังไม่ hard-code dependency — ใช้ adapter pattern
- ถ้าต้องการใช้จริง → R&D Agent ต้องทำ PoC ก่อน
