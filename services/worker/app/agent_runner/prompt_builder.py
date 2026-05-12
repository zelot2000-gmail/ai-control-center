from typing import Optional, List


def build_agent_prompt(
    *,
    run_id: str,
    job_id: str,
    source: str,
    command_id: Optional[str],
    agent_role: str,
    skills: List[str],
    input_text: str,
    workflow: str,
    rag_results: Optional[List[dict]] = None,
) -> str:
    skills_md = "\n".join(f"- {s}" for s in skills) if skills else "- (none)"

    rag_md = ""
    if rag_results is not None:
        rag_md += "\n## RAG Lookup Plan\n"
        rag_md += "- ใช้ RAG Search Results ด้านล่างก่อนตอบ\n"
        rag_md += "- ถ้ามี ADR/SOP ภายใน ให้เชื่อ internal wiki ก่อน generic knowledge\n"
        rag_md += "- cite path เช่น: `docs/wiki/mcp/serena-mcp.md` ใน final report\n"
        rag_md += "- ถ้า results ไม่พอ ให้บอกว่าข้อมูลใน wiki ยังไม่ครอบคลุม\n"
        rag_md += "\n## RAG Search Results\n"
        if not rag_results:
            rag_md += "\n> ⚠️ ไม่พบผลลัพธ์ — wiki อาจยังไม่ได้ ingest\n"
        else:
            for i, r in enumerate(rag_results, 1):
                title    = r.get("title", "Untitled")
                path     = r.get("path", "?")
                category = r.get("category", "?")
                heading  = r.get("heading_path", "")
                score    = r.get("score", 0)
                tags     = r.get("tags", [])
                snippet  = r.get("snippet", "")
                rag_md  += f"\n### {i}. {title}\n"
                rag_md  += f"- path: `{path}`\n"
                rag_md  += f"- category: {category}\n"
                if heading:
                    rag_md += f"- heading: {heading}\n"
                rag_md  += f"- score: {score:.3f}\n"
                if tags:
                    rag_md += f"- tags: {', '.join(tags) if isinstance(tags, list) else tags}\n"
                if snippet:
                    rag_md += f"- snippet:\n{snippet}\n"

    return f"""# AI Control Center — Agent Run

## Source
- source: {source}
- command_id: {command_id or "—"}
- job_id: {job_id}
- run_id: {run_id}

## Agent Role
{agent_role}

## Skills
{skills_md}

## User Command
{input_text}

## Workflow Intent
{workflow or "(not specified)"}
{rag_md}
## Execution Rules
- ❌ ห้ามแสดง secret หรือ API key ใน output
- ❌ ห้ามแก้ไข env file ถ้าไม่ได้รับคำสั่งชัดเจน
- ✅ Prefer minimal diffs — แก้เฉพาะที่จำเป็น
- ✅ อธิบาย risky changes ก่อน apply เสมอ
- ✅ Destructive operations → produce plan first, ห้ามรันทันที
- ✅ ใช้ LLM Wiki / Serena MCP / RTK / TTO เมื่อเกี่ยวข้อง

## Required Output
- **Summary**: สรุปผลการทำงาน
- **Files changed or proposed**: รายการไฟล์ที่แก้หรือวางแผนแก้
- **Commands run or proposed**: คำสั่งที่รันหรือวางแผนรัน
- **Risks**: ความเสี่ยงที่พบ
- **Next steps**: ขั้นตอนถัดไป
"""
