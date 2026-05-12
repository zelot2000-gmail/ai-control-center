# Skill: Programmer

## วัตถุประสงค์
เขียนโค้ด แก้ bug พัฒนา API frontend backend refactor test

## Stack
- Python 3.11 + FastAPI (backend services)
- Nuxt 3 + Vue 3 (web dashboard)
- TypeScript (frontend)

## Code Standards
- ปฏิบัติตาม code style เดิม
- เพิ่ม type hints ทุก function
- ไม่ hard-code secret / API key
- import อยู่ที่ top ของไฟล์เสมอ
- ห้าม print() ใน production code — ใช้ logging

## FastAPI Pattern
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok", "service": "service-name"}
```

## Error Handling
- ใช้ HTTPException สำหรับ API errors
- log error ด้วย logger.error()
- ห้าม log secret ใน error message
- return structured error response

## Testing
- เขียน test ใน tests/ directory
- ใช้ pytest
- ตรวจ coverage ก่อน merge

## Dependency Management
- เพิ่ม dependency ใน requirements.txt พร้อม version pin
- ถ้า dependency ใหม่ → แจ้ง R&D Agent ตรวจ security
