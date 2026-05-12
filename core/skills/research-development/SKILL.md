# Skill: Research & Development

## วัตถุประสงค์
วิจัยเครื่องมือใหม่ PoC benchmark compatibility check TDR

## Evaluation Framework

### Criteria (คะแนน 1-5)
1. usefulness — แก้ปัญหาได้จริง
2. docker_compat — ทำงานใน Docker ได้
3. wsl_compat — ทำงานใน WSL ได้
4. alma8_compat — ทำงานบน AlmaLinux 8 ได้
5. security_risk — ความเสี่ยงด้าน security (5=ปลอดภัยมาก)
6. maintenance_risk — ภาระ maintenance (5=น้อย)
7. resource_usage — ใช้ resource น้อย (5=น้อยมาก)
8. token_cost — cost ต่อ token/request (5=ถูก)
9. rollback_plan — ถอดออกได้ง่าย (5=ง่ายมาก)

### Score Thresholds
- Total >= 36/45 → production-ready candidate
- Total 27-35 → staging candidate
- Total 18-26 → PoC only
- Total 9-17 → keep watching
- Total < 9 → reject

## Sandbox Commands
```bash
# Start research sandbox
bash scripts/research-sandbox.sh

# Or via make
make research
```

## Document Templates
- Experiment: docs/research/experiments/EXPERIMENT_TEMPLATE.md
- Decision: docs/research/decisions/TDR_TEMPLATE.md

## Adoption Status
- reject
- keep watching
- PoC only
- staging
- production-ready

## ข้อห้าม
- ห้ามใช้ production volume ใน experiment
- ห้ามเอา PoC code เข้า main โดยไม่มี TDR
- ห้าม expose experiment service ออก internet
