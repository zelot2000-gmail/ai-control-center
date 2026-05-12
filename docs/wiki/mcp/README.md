# MCP Notes

**หมวด**: mcp  
**สถานะ**: active  

เก็บ notes เกี่ยวกับ MCP (Model Context Protocol) servers ที่ใช้ใน ai-control-center

---

## MCP Servers ที่ใช้งาน

| Server | หน้าที่ | Environment | Agents |
|--------|--------|-------------|--------|
| Chrome DevTools MCP | UI QA, performance, network | local/dev/staging | designer, qa, observer, research, security |
| Serena MCP | Code intelligence, symbol navigation | local/dev | programmer, qa, security, research, manager |

---

## กฎการใช้ MCP

- **ห้ามใช้กับ production account จริง**
- **ห้ามเปิดหน้าเว็บที่มี secret / token**
- **ถ้าพบ secret บนหน้าเว็บ** → หยุดทันที แจ้ง Security Agent
- **ห้าม deploy** ผ่าน MCP โดยตรง
- **ทุก MCP session** ต้องบันทึก tool_usage_log

---

## หัวข้อที่ควรมี

| ไฟล์ | เนื้อหา | สถานะ |
|------|---------|-------|
| `chrome-devtools-guide.md` | วิธีใช้ Chrome DevTools MCP, use cases | TODO |
| `serena-mcp-guide.md` | วิธีใช้ Serena MCP, query patterns | TODO |
| `mcp-security-rules.md` | กฎ security สำหรับ MCP tools | TODO |
