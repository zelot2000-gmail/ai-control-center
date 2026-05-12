---
title: "ADR: ทำไมถึงเลือก Serena MCP"
category: decisions
tags: [adr, serena, mcp, code-intelligence, decision]
status: stable
updated: 2026-05-12
---

# ADR: ทำไมถึงเลือก Serena MCP เป็น Code Intelligence Layer

## Status

**Accepted** — ใช้ใน development workflow

## Context

AI agent ที่ทำงาน code navigation เผชิญปัญหา:
1. อ่านไฟล์ทั้ง repo ใช้ token มหาศาล
2. Grep-based search ขาด semantic understanding
3. ไม่รู้ว่า function ถูกใช้ที่ไหนบ้าง (references)
4. Impact analysis ก่อน refactor ทำได้ยาก

## Options ที่พิจารณา

| Option | Approach | Accuracy | Token cost | Setup |
|--------|---------|----------|-----------|-------|
| **Serena MCP** | Language Server + semantic | สูง | ต่ำ | กลาง |
| Read all files | Brute force | สูง (ถ้าไม่ truncate) | สูงมาก | ไม่ต้อง |
| Grep/regex | Lexical | ปานกลาง | ต่ำ | ไม่ต้อง |
| GitHub Copilot | Cloud-based | สูง | กลาง | ง่าย |
| Sourcegraph | Enterprise | สูงมาก | ขึ้นกับ plan | ซับซ้อน |

## Decision

เลือก **Serena MCP**

## เหตุผล

### 1. Token Efficiency
- Grep ทั้ง repo → อาจได้ผล 100+ lines ที่ไม่เกี่ยวข้อง
- Serena `find_symbol` → ได้เฉพาะ definition + line number
- ประหยัด token ได้ ~80% สำหรับ code navigation tasks

### 2. Semantic Understanding
- เข้าใจ function signature, class hierarchy
- `find_references` หาทุก call site ได้แม่นยำ
- `impact_analysis` บอกได้ว่าแก้ X กระทบอะไรบ้าง

### 3. Self-hosted + MCP Standard
- รันบน local machine — ไม่ส่ง code ออกนอก
- ใช้ MCP protocol มาตรฐาน — integrate กับ Claude Code ได้ทันที
- Open source — ดู source code และ customize ได้

### 4. Polyglot
รองรับ Python, TypeScript, Go, Rust, Java — ครอบคลุม stack ของโปรเจกต์

## Serena vs RAG สำหรับ Code

| | Serena | RAG |
|---|--------|-----|
| Source | Source code | Documents |
| Unit | Symbol | Chunk |
| เหมาะ | Code nav, refactor | Knowledge, SOP |
| Accuracy | สูงมาก | ขึ้นกับ embedding |

**กฎ**: ห้ามใช้ RAG แทน Serena สำหรับ code navigation และ vice versa

## Agents ที่ใช้ Serena

| Agent | Use case |
|-------|----------|
| programmer | หา function, edit code |
| qa | หา test, check coverage |
| security | หา sensitive function |
| manager | impact analysis (read-only) |

## Trade-offs

| ข้อดี | ข้อเสีย |
|-------|---------|
| Token efficient | Startup time สำหรับ index |
| Semantic accuracy | ต้อง update index เมื่อ repo เปลี่ยนมาก |
| Self-hosted | ไม่รองรับ binary/minified files |
| MCP standard | Community ยังเล็กกว่า GitHub Copilot |

## Consequences

- **ดี**: agent ทำ code navigation ได้เร็วขึ้น ถูกลง
- **เสีย**: ต้อง maintain Serena setup
- **Mitigation**: document setup ใน wiki (serena-mcp.md)

## Review

ทบทวนถ้า:
- Serena ไม่ maintain แล้ว
- มี MCP-based code intelligence tool ที่ดีกว่า
- Repo ขนาดใหญ่มากจน Serena index ช้าเกินไป
