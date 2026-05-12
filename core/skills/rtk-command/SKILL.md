# Skill: RTK Safe Command

## วัตถุประสงค์
วางแผน validate และรัน shell command แบบปลอดภัยผ่าน allowlist

## Endpoints
- POST /plan-command — วางแผน command จาก goal
- POST /validate-command — ตรวจ command กับ allowlist + blocked patterns
- POST /run-command — รัน command (disabled ใน production)

## Allowlist
ดู `core/commands/command-allowlist.yaml`

## Blocked Patterns (ห้ามเด็ดขาด)
- rm -rf /
- rm -rf *
- mkfs
- dd if=
- shutdown
- reboot
- DROP DATABASE
- DELETE FROM (ถ้าไม่มี WHERE)
- docker volume rm
- chmod -R 777
- chown -R root

## Workspace Restriction
- ทำงานเฉพาะใน /workspace
- ห้ามเข้า /, /etc, /root, /home, /usr/bin

## Production Mode
- run-command ต้อง disabled จนกว่าจะตั้งค่า RTK_ALLOW_RUN_COMMAND=true
- plan-command และ validate-command ทำงานได้เสมอ

## Validation Response
```json
{
  "command": "ls -la",
  "is_safe": true,
  "risk_level": 1,
  "blocked_reason": null,
  "suggestions": []
}
```
