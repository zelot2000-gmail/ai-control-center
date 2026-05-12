import os
import re
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

QDRANT_HOST      = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT      = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION       = os.getenv("QDRANT_COLLECTION", "aicc_docs")
WIKI_COLLECTION  = os.getenv("QDRANT_WIKI_COLLECTION", "aicc_wiki")
EMBEDDING_MODEL  = os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
WIKI_DIR         = Path(os.getenv("WIKI_DIR", "/app/docs/wiki"))
REPORTS_DIR      = Path("/app/data/reports")
CHUNK_SIZE       = 512
CHUNK_OVERLAP    = 64
WIKI_MAX_CHARS   = int(os.getenv("WIKI_CHUNK_MAX_CHARS", "2000"))
VECTOR_SIZE      = 384

# Safety: blocked path patterns (never ingest these)
_BLOCKED = {"secret", ".env", "upload", "credential", "password", ".git"}

_embedder = None
_qdrant   = None
_latest_report: dict = {}


# ── Embedding / Qdrant helpers ────────────────────────────────────────────────

def get_embedder():
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
            _embedder = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("Embedding model loaded")
        except Exception as e:
            logger.error("Failed to load embedding model: %s", e)
            raise HTTPException(
                status_code=503,
                detail=f"Embedding model unavailable: {e}. Check logs for fix.",
            )
    return _embedder


def get_qdrant():
    global _qdrant
    if _qdrant is None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            _qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            _ensure_collection(_qdrant, COLLECTION)
        except Exception as e:
            logger.error("Qdrant connection failed: %s", e)
            raise HTTPException(status_code=503, detail=f"Qdrant unavailable: {e}")
    return _qdrant


def _ensure_collection(qc, name: str, size: int = VECTOR_SIZE):
    from qdrant_client.models import Distance, VectorParams
    existing = [c.name for c in qc.get_collections().collections]
    if name not in existing:
        qc.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=size, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection: %s (size=%d)", name, size)


# ── Generic chunking (word-based) ─────────────────────────────────────────────

def _chunk_text(text: str, source: str) -> List[dict]:
    words = text.split()
    chunks, i, n = [], 0, 0
    while i < len(words):
        chunk = " ".join(words[i:i + CHUNK_SIZE])
        chunks.append({"text": chunk, "source": source, "chunk_num": n})
        n += 1
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def _read_file(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning("Cannot read %s: %s", path, e)
        return None


# ── Wiki-specific helpers ─────────────────────────────────────────────────────

def _is_safe_wiki_path(p: Path) -> bool:
    """Ensure file is inside WIKI_DIR and not blocked."""
    try:
        p.resolve().relative_to(WIKI_DIR.resolve())
    except ValueError:
        return False
    name_lower = p.name.lower()
    return not any(b in name_lower for b in _BLOCKED)


def _parse_frontmatter(text: str) -> Tuple[dict, str]:
    """Extract YAML frontmatter from markdown. Returns (meta, body)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_raw = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    meta: dict = {}
    for line in fm_raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            val = v.strip().strip('"').strip("'")
            # handle tags: [a, b, c]
            if val.startswith("[") and val.endswith("]"):
                val = [t.strip().strip('"') for t in val[1:-1].split(",") if t.strip()]
            meta[k.strip()] = val
    return meta, body


_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)


def _chunk_markdown_wiki(body: str, filepath: Path, meta: dict) -> List[dict]:
    """Split markdown by headings, maintain heading path, split large sections."""
    rel_path = str(filepath.relative_to(WIKI_DIR.parent.parent))  # docs/wiki/...
    parts = filepath.parts
    # category = folder name under wiki (llm, rag, mcp, etc.)
    try:
        wiki_idx = list(parts).index("wiki")
        category = parts[wiki_idx + 1] if wiki_idx + 1 < len(parts) - 1 else "wiki"
    except ValueError:
        category = "wiki"

    title    = meta.get("title", filepath.stem)
    tags     = meta.get("tags", [])
    updated  = meta.get("updated", meta.get("updated_at", ""))

    # Find heading positions
    matches = list(_HEADING_RE.finditer(body))
    # Build sections: (start, end, level, heading_title)
    sections: List[Tuple[int, int, int, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        level = len(m.group(1))
        htitle = m.group(2).strip()
        sections.append((start, end, level, htitle))

    # If no headings found, treat whole body as one section
    if not sections:
        sections = [(0, len(body), 1, title)]

    chunks: List[dict] = []
    heading_stack: List[str] = []

    def _make_chunk(text: str, heading_path: str, idx: int) -> dict:
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        point_id = str(uuid.UUID(content_hash[:32]))
        return {
            "id":           point_id,
            "text":         text,
            "source_type":  "wiki",
            "path":         rel_path,
            "category":     category,
            "title":        title,
            "tags":         tags if isinstance(tags, list) else [tags],
            "updated_at":   updated,
            "heading_path": heading_path,
            "chunk_index":  idx,
            "content_hash": content_hash,
        }

    for start, end, level, htitle in sections:
        section_text = body[start:end].strip()
        if not section_text:
            continue

        # Maintain heading stack
        heading_stack = heading_stack[:level - 1]
        heading_stack.append(htitle)
        heading_path = " > ".join(heading_stack)

        # Split if too large
        if len(section_text) > WIKI_MAX_CHARS:
            sub_chunks = _split_large_text(section_text, WIKI_MAX_CHARS)
            for sub in sub_chunks:
                chunks.append(_make_chunk(sub, heading_path, len(chunks)))
        else:
            chunks.append(_make_chunk(section_text, heading_path, len(chunks)))

    return chunks


def _split_large_text(text: str, max_chars: int) -> List[str]:
    """Split text into segments of max_chars, breaking on newlines where possible."""
    if len(text) <= max_chars:
        return [text]
    parts = []
    while text:
        if len(text) <= max_chars:
            parts.append(text)
            break
        split_at = text.rfind("\n", 0, max_chars)
        if split_at == -1:
            split_at = max_chars
        parts.append(text[:split_at].strip())
        text = text[split_at:].strip()
    return [p for p in parts if p]


# ── Request / Response Models ─────────────────────────────────────────────────

class IngestRequest(BaseModel):
    path: str
    collection: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    collection: Optional[str] = None


class WikiSearchRequest(BaseModel):
    query: str
    limit: int = 5
    category: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    qdrant_status = "unknown"
    try:
        qc = get_qdrant()
        qc.get_collections()
        qdrant_status = "ok"
    except Exception:
        qdrant_status = "unavailable"
    return {
        "status": "ok",
        "service": "rag-api",
        "version": "0.2.0",
        "qdrant": qdrant_status,
        "embedding_model": EMBEDDING_MODEL,
        "wiki_collection": WIKI_COLLECTION,
        "wiki_dir": str(WIKI_DIR),
    }


@app.get("/collections")
async def list_collections():
    qc = get_qdrant()
    cols = qc.get_collections().collections
    result = []
    for c in cols:
        try:
            info = qc.get_collection(c.name)
            result.append({
                "name": c.name,
                "vectors_count": info.vectors_count or 0,
                "points_count": info.points_count or 0,
            })
        except Exception:
            result.append({"name": c.name, "vectors_count": 0, "points_count": 0})
    return {"collections": result, "count": len(result)}


@app.post("/ingest")
async def ingest(req: IngestRequest):
    """Generic ingest — any directory."""
    collection = req.collection or COLLECTION
    ingest_path = Path(req.path)

    if not ingest_path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {req.path}")

    files = []
    if ingest_path.is_dir():
        files = list(ingest_path.glob("**/*.md")) + list(ingest_path.glob("**/*.txt"))
    elif ingest_path.is_file():
        files = [ingest_path]

    if not files:
        return {"ingested": 0, "chunks": 0, "message": "No .md or .txt files found"}

    embedder = get_embedder()
    qc = get_qdrant()
    _ensure_collection(qc, collection)

    from qdrant_client.models import PointStruct

    total_chunks = 0
    ingested_files = []

    for file_path in files:
        content = _read_file(str(file_path))
        if not content:
            continue
        chunks = _chunk_text(content, str(file_path.name))
        points = []
        for chunk in chunks:
            embedding = embedder.encode(chunk["text"]).tolist()
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={"text": chunk["text"], "source": chunk["source"], "chunk_num": chunk["chunk_num"]},
            ))
        if points:
            qc.upsert(collection_name=collection, points=points)
            total_chunks += len(points)
            ingested_files.append(str(file_path.name))
        logger.info("Ingested %s: %d chunks", file_path.name, len(points))

    return {
        "ingested": len(ingested_files),
        "chunks": total_chunks,
        "files": ingested_files,
        "collection": collection,
    }


@app.post("/ingest/wiki")
async def ingest_wiki():
    """
    Ingest docs/wiki/**/*.md into aicc_wiki collection.
    - Heading-based chunking with frontmatter metadata
    - Idempotent via content_hash as point ID
    - Safety: only reads from WIKI_DIR, skips blocked patterns
    """
    started_at = datetime.now(timezone.utc).isoformat()

    if not WIKI_DIR.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Wiki directory not found: {WIKI_DIR}. Check volume mount in docker-compose.",
        )

    md_files = [p for p in WIKI_DIR.rglob("*.md") if _is_safe_wiki_path(p)]
    if not md_files:
        return {"ingested": 0, "chunks": 0, "message": "No safe .md files found in wiki dir"}

    embedder = get_embedder()
    qc = get_qdrant()
    _ensure_collection(qc, WIKI_COLLECTION)

    from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

    total_chunks  = 0
    skipped       = 0
    file_reports  = []
    errors        = []

    for file_path in sorted(md_files):
        try:
            content = file_path.read_text(encoding="utf-8")
            meta, body = _parse_frontmatter(content)
            chunks = _chunk_markdown_wiki(body, file_path, meta)

            if not chunks:
                skipped += 1
                continue

            # Check which IDs already exist (idempotent — skip unchanged)
            candidate_ids = [c["id"] for c in chunks]
            try:
                existing = qc.retrieve(
                    collection_name=WIKI_COLLECTION,
                    ids=candidate_ids,
                    with_payload=False,
                )
                existing_ids = {str(p.id) for p in existing}
            except Exception:
                existing_ids = set()

            new_chunks = [c for c in chunks if c["id"] not in existing_ids]

            if new_chunks:
                texts = [c["text"] for c in new_chunks]
                embeddings = embedder.encode(texts).tolist()
                points = [
                    PointStruct(
                        id=c["id"],
                        vector=emb,
                        payload={k: v for k, v in c.items() if k != "id"},
                    )
                    for c, emb in zip(new_chunks, embeddings)
                ]
                qc.upsert(collection_name=WIKI_COLLECTION, points=points)
                total_chunks += len(points)

            rel = str(file_path.relative_to(WIKI_DIR.parent.parent))
            file_reports.append({
                "path": rel,
                "category": meta.get("category", "wiki"),
                "title": meta.get("title", file_path.stem),
                "total_chunks": len(chunks),
                "new_chunks": len(new_chunks),
                "skipped_chunks": len(chunks) - len(new_chunks),
            })
            logger.info("Wiki ingest %s: %d chunks (%d new)", rel, len(chunks), len(new_chunks))

        except Exception as e:
            logger.error("Failed to ingest %s: %s", file_path, e)
            errors.append({"path": str(file_path), "error": str(e)})

    completed_at = datetime.now(timezone.utc).isoformat()
    report = {
        "status": "completed",
        "started_at": started_at,
        "completed_at": completed_at,
        "collection": WIKI_COLLECTION,
        "wiki_dir": str(WIKI_DIR),
        "files_found": len(md_files),
        "files_ingested": len(file_reports),
        "files_skipped": skipped,
        "total_new_chunks": total_chunks,
        "errors": errors,
        "files": file_reports,
    }
    global _latest_report
    _latest_report = report

    # Persist report
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        (REPORTS_DIR / "wiki_ingest_latest.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        logger.warning("Could not persist report: %s", e)

    return report


@app.post("/search/wiki")
async def search_wiki(req: WikiSearchRequest):
    """
    Semantic search in aicc_wiki collection.
    Returns: score, title, path, category, snippet, heading_path
    """
    embedder = get_embedder()
    qc = get_qdrant()
    _ensure_collection(qc, WIKI_COLLECTION)

    query_vector = embedder.encode(req.query).tolist()

    search_kwargs: dict = {
        "collection_name": WIKI_COLLECTION,
        "query_vector": query_vector,
        "limit": req.limit,
        "with_payload": True,
        "score_threshold": 0.35,
    }

    # Optional category filter
    if req.category:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        search_kwargs["query_filter"] = Filter(
            must=[FieldCondition(key="category", match=MatchValue(value=req.category))]
        )

    results = qc.search(**search_kwargs)

    hits = []
    for r in results:
        p = r.payload or {}
        text = p.get("text", "")
        snippet = text[:300].replace("\n", " ").strip()
        if len(text) > 300:
            snippet += "..."
        hits.append({
            "score":        round(r.score, 4),
            "title":        p.get("title", ""),
            "path":         p.get("path", ""),
            "category":     p.get("category", ""),
            "heading_path": p.get("heading_path", ""),
            "tags":         p.get("tags", []),
            "snippet":      snippet,
            "updated_at":   p.get("updated_at", ""),
        })

    return {
        "query":      req.query,
        "results":    hits,
        "count":      len(hits),
        "collection": WIKI_COLLECTION,
    }


@app.post("/search")
async def search(req: SearchRequest):
    """Generic search."""
    collection = req.collection or COLLECTION
    embedder = get_embedder()
    qc = get_qdrant()

    query_vector = embedder.encode(req.query).tolist()
    results = qc.search(
        collection_name=collection,
        query_vector=query_vector,
        limit=req.limit,
    )

    hits = [
        {
            "score":     round(r.score, 4),
            "text":      r.payload.get("text", ""),
            "source":    r.payload.get("source", ""),
            "chunk_num": r.payload.get("chunk_num", 0),
        }
        for r in results
    ]
    return {"query": req.query, "results": hits, "count": len(hits), "collection": collection}


@app.get("/ingest/reports/latest")
async def get_latest_report():
    """Return latest wiki ingest report."""
    global _latest_report
    if not _latest_report:
        # Try to load from disk
        report_file = REPORTS_DIR / "wiki_ingest_latest.json"
        if report_file.exists():
            try:
                _latest_report = json.loads(report_file.read_text(encoding="utf-8"))
            except Exception:
                pass
    if not _latest_report:
        return {
            "status": "no_report",
            "message": "No ingest report found. Run POST /ingest/wiki first.",
        }
    return _latest_report


@app.delete("/collections/{name}")
async def delete_collection(name: str, confirm: Optional[str] = None):
    if confirm != "CONFIRM DANGEROUS":
        raise HTTPException(
            status_code=403,
            detail="Deleting a collection requires confirm=CONFIRM DANGEROUS query param",
        )
    qc = get_qdrant()
    qc.delete_collection(name)
    logger.warning("Collection deleted: %s", name)
    return {"deleted": name, "message": "Collection removed from Qdrant"}
